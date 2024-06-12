#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

from json import loads, dumps
from hashlib import md5

from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport, TTransportException
from thrift.protocol import TBinaryProtocol
from thumbor_hbase.hbase import Hbase
from thumbor_hbase.hbase.ttypes import Mutation

from thumbor import storages
from thumbor.utils import logger

class Storage(storages.BaseStorage):
    crypto_col = b'crypto'
    detector_col = b'detector'
    image_col = b'raw'
    hbase_server_offset = 0
    storage = None

    def __init__(self,context):
        self.context=context
        assert(isinstance(self.context.config.HBASE_STORAGE_TABLE, bytes))
        assert(isinstance(self.context.config.HBASE_STORAGE_FAMILY, bytes))
        self.table = self.context.config.HBASE_STORAGE_TABLE
        self.data_fam = self.context.config.HBASE_STORAGE_FAMILY
        try:
            self._connect()
        except TTransportException:
            None

    # put image content
    async def put(self, path, bytes):
        self._put(path, self.image_col, bytes )

        return path

    # put crypto key for signature
    async def put_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            return

        if not self.context.config.SECURITY_KEY:
            raise RuntimeError("STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified")

        self._put(path, self.crypto_col, self.context.config.SECURITY_KEY.encode('utf-8'))

    # put detector JSON
    async def put_detector_data(self, path, data):
        self._put(path, self.detector_col, dumps(data).encode('utf-8'))

    # get signature key
    async def get_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            None
        else:
            r = self._get(path, self.crypto_col)
            if not r:
                return None
            else:
                return r.value

    # get detector Json
    async def get_detector_data(self, path):
        r = self._get(path, self.detector_col)

        if r is not None:
            return loads(r.value)
        else:
            return None

    # get image content
    async def get(self, path):
        r = self._get(path, self.image_col)

        if r is not None:
            return r.value
        else:
            return None

    # test image exists
    async def exists(self, path):
        r = self._get(path, self.image_col)

        if r is not None:
            return len(r.value) != 0
        else:
            return False

    def makeKey(self,key):
        return (md5(key.encode('utf-8', 'backslashreplace')).hexdigest() + '-' + key).encode('utf-8')

    # remove image entries
    async def remove(self,key):
        key = self.makeKey(key)

        if self.storage is None:
            self._connect()
        self.storage.deleteAllRow(self.table, key, {})

    # GET a Cell value in HBase
    def _get(self, key, col):
        key = self.makeKey(key)
        logger.debug("_get column %s of row %s", col, key)

        if self.storage is None:
            self._connect()

        try:
            r = self.storage.get(self.table, key, (self.data_fam + b':' + col), {})[0]
        except IndexError:
            r = None
        except:
            r = None
            logger.error("Error retrieving image from HBase; key %s column %s", key, col)
            self.hbase_server_offset = self.hbase_server_offset+1

        return r

    # PUT value in a Cell of HBase
    def _put(self, key, col, value):
        key = self.makeKey(key)
        logger.debug("_put %d bytes into column %s for row %s", len(value), col, key)

        r = [Mutation(column=(self.data_fam + b':' + col), value=value)]

        if self.storage is None:
            self._connect()

        try:
            self.storage.mutateRow(self.table, key, r, {})
        except:
            # Try once more, seems to happen if downloading takes too long.
            logger.warning("repeating _put %d bytes into column %s for row %s", len(value), col, key)
            self._connect()
            self.storage.mutateRow(self.table, key, r, {})

    def _connect(self):
        if hasattr(self.context.config, 'HBASE_STORAGE_SERVER_HOSTS') and self.context.config.HBASE_STORAGE_SERVER_HOSTS is not None:
            host = self.context.config.HBASE_STORAGE_SERVER_HOSTS[(self.context.server.port + self.hbase_server_offset) % len(self.context.config.HBASE_STORAGE_SERVER_HOSTS)]
        else:
            host = self.context.config.HBASE_STORAGE_SERVER_HOST

        # Timeout is sum of HTTP timeouts, plus a bit.
        try:
            socket = TSocket(host=host, port=self.context.config.HBASE_STORAGE_SERVER_PORT)
            timeout = 5
            socket.setTimeout(timeout * 1000)
        except:
            pass

        try:
            transport = TBufferedTransport(socket)
            transport.open()
            protocol = TBinaryProtocol.TBinaryProtocol(transport)
            self.storage = Hbase.Client(protocol)
            logger.info("Connected to HBase server "+host+":"+str(self.context.config.HBASE_STORAGE_SERVER_PORT))
        except:
            logger.error("Error connecting to HBase server "+host+":"+str(self.context.config.HBASE_STORAGE_SERVER_PORT))
            self.hbase_server_offset = self.hbase_server_offset+1
