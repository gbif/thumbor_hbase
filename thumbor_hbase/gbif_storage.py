#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

import time
from json import loads, dumps
from hashlib import md5
from struct import pack, unpack

from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport, TTransportException
from thrift.protocol import TBinaryProtocol
from thumbor_hbase import storage
from thumbor_hbase.hbase import Hbase
from thumbor_hbase.hbase.ttypes import Mutation

from thumbor import storages
from thumbor.utils import logger

# Store additional metadata relevant for occurrence images from GBIF.org.
#
class Storage(storage.Storage):

    # GET a Cell value in HBase
    def _get(self, key, col):
        key = self.makeKey(key)
        logger.debug("_get column %s of row %s", col, key)

        if self.storage is None:
            self._connect()

        try:
            r = self.storage.get(self.table, key, (self.data_fam + b':' + col), {})[0]
            try:
                now = int(time.time())
                access = [Mutation(column=b'metadata:accessed', value=pack("!q", now))]
                self.storage.mutateRow(self.table, key, access, {})
                self.storage.atomicIncrement(self.table, key, b'metadata:hits', 1)
            except:
                logger.warning("Failed to increment hit count and access time for row %s", key)
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

        image_size = len(value)
        now = int(time.time())
        r = [
            Mutation(column=(self.data_fam + b':' + col), value=value),
            Mutation(column=b'metadata:image_size', value=pack("!q", image_size)),
            Mutation(column=b'metadata:created', value=pack("!q", now)),
            Mutation(column=b'metadata:accessed', value=pack("!q", now)),
            Mutation(column=b'metadata:hits', value=pack("!q", 1))
        ]
        if 'dataset_key' in self.context.headers:
            dataset_key = self.context.headers['dataset_key']
            occurrence_id = self.context.headers['occurrence_id']
            media_url = self.context.headers['url']
            image_url_hash = self.context.headers['image_url_hash']

            r += [
                Mutation(column=b'metadata:dataset_key', value=dataset_key.encode()),
                Mutation(column=b'metadata:occurrence_id', value=occurrence_id.encode()),
                Mutation(column=b'metadata:identifier', value=media_url.encode()),
                Mutation(column=b'metadata:identifier_hash', value=image_url_hash.encode())
            ]
        elif 'unsafe' in self.context.headers:
            r += [
                Mutation(column=b'metadata:unsafe', value=self.context.headers['unsafe'].encode())
            ]

        if self.storage is None:
            self._connect()

        try:
            self.storage.mutateRow(self.table, key, r, {})
        except:
            # Try once more, seems to happen if downloading takes too long.
            logger.warning("repeating _put %d bytes into column %s for row %s", len(value), col, key)
            self._connect()
            self.storage.mutateRow(self.table, key, r, {})
