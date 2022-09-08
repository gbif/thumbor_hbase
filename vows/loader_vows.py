#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport
from thrift.protocol import TBinaryProtocol
from thumbor_hbase.hbase import Hbase, ttypes

import asyncio
from pyvows import Vows, expect
from thumbor_hbase.storage import Storage
import thumbor_hbase.loader as loader
from thumbor.context import Context
from thumbor.config import Config
from thumbor.loaders import LoaderResult
from vows.fixtures.storage_fixture import IMAGE_URL, IMAGE_BYTES, get_server

class HbaseDBContext(Vows.Context):
    def setup(self):
        transport = TBufferedTransport(TSocket(host='localhost', port=9090))
        transport.open()
        protocol = TBinaryProtocol.TBinaryProtocol(transport)
        self.connection = Hbase.Client(protocol)
        self.table=b'thumbor-test'
        self.family=b'images:'

        columns = []
        col = ttypes.ColumnDescriptor()
        col.name = self.family
        col.maxVersions = 1
        columns.append(col)
        try:
            self.connection.disableTable(self.table)
            self.connection.deleteTable(self.table)
        except ttypes.IOError:
            pass
        self.connection.createTable(self.table, columns)


@Vows.batch
class HbaseLoaderVows(HbaseDBContext):
    class CanLoadImage(Vows.Context):
        def topic(self,callback ):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table,HBASE_STORAGE_SERVER_PORT=9090)
            context = Context(config=config, server=get_server('ACME-SEC'))
            storage = Storage(context)

            asyncio.run(storage.put(IMAGE_URL % '1', IMAGE_BYTES))
            return asyncio.run(loader.load(context, IMAGE_URL % '1'))

        def should_have_proper_bytes(self, topic):
            expect(topic.successful).to_be_true()
            expect(topic.buffer).to_equal(IMAGE_BYTES)

    class LoadNonExistantImage(Vows.Context):
        @Vows.capture_error
        def topic(self, callback):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table,HBASE_STORAGE_SERVER_PORT=9090)
            context = Context(config=config, server=get_server('ACME-SEC'))
            storage = Storage(context)

            return asyncio.run(loader.load(context, IMAGE_URL % '9998'))

        def should_have_proper_bytes(self, topic):
            expect(topic.successful).to_be_false()
            expect(topic.error).to_equal(LoaderResult.ERROR_NOT_FOUND)
