#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/dhardy92/thumbor_hbase/

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license

from json import loads, dumps
from hashlib import md5
import re

from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport, TTransportException
from thrift.protocol import TBinaryProtocol
from hbase import Hbase
from hbase.ttypes import Mutation

from thumbor.storages import BaseStorage
from tornado.concurrent import return_future
from thumbor.utils import logger

class Storage(BaseStorage):
    crypto_col = 'crypto'
    detector_col = 'detector'
    image_col = 'raw'
    hbase_server_offset = 0
    storage = None

    def __init__(self,context):
        self.context=context
        self.table = self.context.config.HBASE_STORAGE_TABLE
        self.data_fam = self.context.config.HBASE_STORAGE_FAMILY
        try:
            self._connect()
        except TTransportException:
            None

    # put image content
    def put(self, path, bytes):
        self._put(path, self.image_col, bytes )

        return path

    # put crypto key for signature
    def put_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            return

        if not self.context.config.SECURITY_KEY:
            raise RuntimeError("STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified")

        self._put(path, self.crypto_col,self.context.config.SECURITY_KEY)

    # put detector Json
    def put_detector_data(self, path, data):
        self._put(path, self.detector_col, dumps(data))

    # get signature key
    @return_future
    def get_crypto(self, path, callback):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            callback(None)
        else:
            r = self._get(path, self.crypto_col)
            if not r:
                callback(None)
            else:
                callback(r.value)

    # get detector Json
    @return_future
    def get_detector_data(self, path, callback):
        r = self._get(path, self.detector_col)

        if r is not None:
            callback(loads(r.value))
        else:
            callback(None)

    # get image content
    @return_future
    def get(self, path, callback):
        r = self._get(path, self.image_col)

        if r is not None:
             callback(r.value)
        else:
             callback(None)

    # test image exists
    @return_future
    def exists(self, path, callback):
        r = self._get(path, self.image_col)

        if r is not None:
            callback(len(r.value) != 0)
        else:
            callback(False)

    # remove image entries
    def remove(self,key):
        try:
            key = md5(key).hexdigest() + '-' + key
        except UnicodeEncodeError:
            key = md5(key.encode('utf-8')).hexdigest() + '-' + key.encode('utf-8')

        if self.storage is None:
            self._connect()
        self.storage.deleteAllRow(self.table, key)

    def resolve_original_photo_path(self,filename):
        return filename

    # GET a Cell value in HBase
    def _get(self,key,col):

        try:
            key = md5(key).hexdigest() + '-' + key
        except UnicodeEncodeError:
            key = md5(key.encode('utf-8')).hexdigest() + '-' + key.encode('utf-8')

        if self.storage is None:
            self._connect()

        try:
            r = self.storage.get(self.table, key, self.data_fam + ':' + col)[0]
        except IndexError:
            r = None
        except:
            r = None
            logger.error("Error retrieving image from HBase; key "+key)
            self.hbase_server_offset = self.hbase_server_offset+1

        return r

    # PUT value in a Cell of HBase
    def _put(self, key, col, value):

        try:
            key = md5(key).hexdigest() + '-' + key
        except UnicodeEncodeError:
            key = md5(key.encode('utf-8')).hexdigest() + '-' + key.encode('utf-8')

        r = [Mutation(column=self.data_fam + ':' + col, value=value)]

        if self.storage is None:
            self._connect()

        try:
            self.storage.mutateRow(self.table, key, r)
        except:
            # Try once more, seems to happen if downloading takes too long.
            self._connect()
            self.storage.mutateRow(self.table, key, r)


    def _connect(self):
        if hasattr(self.context.config, 'HBASE_STORAGE_SERVER_HOSTS'):
            host = self.context.config.HBASE_STORAGE_SERVER_HOSTS[(self.context.server.port + self.hbase_server_offset) % len(self.context.config.HBASE_STORAGE_SERVER_HOSTS)]
        else:
            host = self.context.config.HBASE_STORAGE_SERVER_HOST

        transport = TBufferedTransport(TSocket(host=host, port=self.context.config.HBASE_STORAGE_SERVER_PORT))

        socket = TSocket(host=host, port=self.context.config.HBASE_STORAGE_SERVER_PORT)
        # Timeout is sum of HTTP timeouts, plus a bit.
        try:
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
