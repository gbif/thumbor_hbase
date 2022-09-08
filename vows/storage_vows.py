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

from pyvows import Vows, expect
from hashlib import md5

from thumbor.app import ThumborServiceApp
from thumbor_hbase.storage import Storage
from thumbor.importer import Importer
from thumbor.context import Context, ServerParameters
from thumbor.config import Config
from vows.fixtures.storage_fixture import IMAGE_URL, IMAGE_BYTES, get_server
import asyncio
import time
import tornado.concurrent

def hbasekey(key):
    return (md5(key.encode('utf-8', 'backslashreplace')).hexdigest() + '-' + key).encode('utf-8')


class HbaseDBContext(Vows.Context):
    connection = None
    table = None
    family = None

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
class HbaseStorageVows(HbaseDBContext):
    class CanStartWithoutThriftServer(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_SERVER_HOST='dummyserver', HBASE_STORAGE_TABLE=self.parent.table, HBASE_STORAGE_SERVER_PORT=9090, SECURITY_KEY='ACME-SEC')
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

        def does_not_raise_exception(self, topic):
            expect(topic).Not.to_be_an_error()

    class CanStoreImage(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table, HBASE_STORAGE_SERVER_PORT=9090, SECURITY_KEY='ACME-SEC')
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

            return (
                asyncio.run(storage.put(IMAGE_URL % '1', IMAGE_BYTES)),
                self.parent.connection.get(self.parent.table, hbasekey(IMAGE_URL % '1'), self.parent.family+b'raw', {})[0].value
            )

        def should_be_in_catalog(self, topic):
            expect(topic[0]).to_equal(IMAGE_URL % '1')
            expect(topic[1]).not_to_be_null()
            expect(topic[1]).not_to_be_an_error()
            expect(topic[1]).to_equal(IMAGE_BYTES)

    class CanStoreUnicodeImage2(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table, HBASE_STORAGE_SERVER_PORT=9090, SECURITY_KEY='ACME-SEC')
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

            return (
                asyncio.run(storage.put(IMAGE_URL % 'àé', IMAGE_BYTES)),
                self.parent.connection.get(self.parent.table, hbasekey(IMAGE_URL % 'àé'), self.parent.family+b'raw' ,{})[0].value
            )

        def should_be_in_catalog(self, topic):
            expect(topic[0]).to_equal(IMAGE_URL % 'àé')
            expect(topic[1]).not_to_be_null()
            expect(topic[1]).not_to_be_an_error()
            expect(topic[1]).to_equal(IMAGE_BYTES)

    class CanStoreUnicodeImage(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table, HBASE_STORAGE_SERVER_PORT=9090, SECURITY_KEY='ACME-SEC')
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

            return (
                asyncio.run(storage.put(IMAGE_URL % 'àé', IMAGE_BYTES)),
                self.parent.connection.get(self.parent.table, hbasekey(IMAGE_URL % 'àé'), self.parent.family+b'raw', {})[0].value
            )

        def should_be_in_catalog(self, topic):
            expect(topic[0]).to_equal(IMAGE_URL % 'àé')
            expect(topic[1]).not_to_be_null()
            expect(topic[1]).not_to_be_an_error()
            expect(topic[1]).to_equal(IMAGE_BYTES)

    class CanStoreAndGetUnicodeURLencodedImage(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table, HBASE_STORAGE_SERVER_PORT=9090, SECURITY_KEY='ACME-SEC')
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

            return (
                asyncio.run(storage.put(IMAGE_URL % '%C3%A0%C3%A9', IMAGE_BYTES)),
                self.parent.connection.get(self.parent.table, hbasekey(IMAGE_URL % '%C3%A0%C3%A9'), self.parent.family+b'raw', {})[0].value
            )

        def should_be_in_catalog(self, topic):
            expect(topic[0]).to_equal(IMAGE_URL % '%C3%A0%C3%A9')
            expect(topic[1]).not_to_be_null()
            expect(topic[1]).not_to_be_an_error()
            expect(topic[1]).to_equal(IMAGE_BYTES)

    class CanGetImage(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table, HBASE_STORAGE_SERVER_PORT=9090)
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

            asyncio.run(storage.put(IMAGE_URL % '2', IMAGE_BYTES))
            return asyncio.run(storage.get(IMAGE_URL % '2'))

        def should_have_proper_bytes(self, topic):
            expect(topic).to_equal(IMAGE_BYTES)

    class CanGetImageExistance(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table,HBASE_STORAGE_SERVER_PORT=9090)
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

            asyncio.run(storage.put(IMAGE_URL % '8', IMAGE_BYTES))
            return asyncio.run(storage.exists(IMAGE_URL % '8'))

        def should_exists(self, topic):
            expect(topic).to_be_true()

    class CanGetImageInexistance(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table,HBASE_STORAGE_SERVER_PORT=9090)
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

            return asyncio.run(storage.exists(IMAGE_URL % '9999'))

        def should_not_exists(self, topic):
            expect(topic).to_be_false()

    class CanRemoveImage(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table,HBASE_STORAGE_SERVER_PORT=9090)
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

            asyncio.run(storage.put(IMAGE_URL % '9', IMAGE_BYTES))
            created = asyncio.run(storage.exists(IMAGE_URL % '9'))
            asyncio.run(storage.remove(IMAGE_URL % '9'))
            return created == True and asyncio.run(storage.exists(IMAGE_URL % '9')) == False

        def should_be_put_and_removed(self, topic):
            expect(topic).to_equal(True)

    class CanRemovethenPutImage(Vows.Context):
        def topic(self):
            config = Config(HBASE_STORAGE_TABLE=self.parent.table,HBASE_STORAGE_SERVER_PORT=9090)
            storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

            asyncio.run(storage.put(IMAGE_URL % '10', IMAGE_BYTES))
            asyncio.run(storage.remove(IMAGE_URL % '10'))
            time.sleep(1)
            created = asyncio.run(storage.exists(IMAGE_URL % '10'))
            time.sleep(1)
            asyncio.run(storage.put(IMAGE_URL % '10', IMAGE_BYTES))
            return asyncio.run(storage.exists(IMAGE_URL % '10')) != created

        def should_be_put_and_removed(self, topic):
            expect(topic).to_equal(True)

    class CryptoVows(Vows.Context):
        class RaisesIfInvalidConfig(Vows.Context):
            @Vows.capture_error
            def topic(self):
                config = Config(HBASE_STORAGE_TABLE=self.parent.parent.table,HBASE_STORAGE_SERVER_PORT=9090, SECURITY_KEY='', STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)
                storage = Storage(Context(config=config, server=get_server('')))

                asyncio.run(storage.put(IMAGE_URL % '3', IMAGE_BYTES))
                asyncio.run(storage.put_crypto(IMAGE_URL % '3'))

            def should_be_an_error(self, topic):
                expect(topic).to_be_an_error_like(RuntimeError)
                expect(topic).to_have_an_error_message_of("STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified")

        class GettingCryptoForANewImageReturnsNone(Vows.Context):
            def topic(self):
                config = Config(HBASE_STORAGE_TABLE=self.parent.parent.table,HBASE_STORAGE_SERVER_PORT=9090, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)
                storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

                return asyncio.run(storage.get_crypto(IMAGE_URL % '9999'))

            def should_be_null(self, topic):
                expect(topic).to_be_null()

        class DoesNotStoreIfConfigSaysNotTo(Vows.Context):
            def topic(self):
                config = Config(HBASE_STORAGE_TABLE=self.parent.parent.table,HBASE_STORAGE_SERVER_PORT=9090)
                storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

                asyncio.run(storage.put(IMAGE_URL % '5', IMAGE_BYTES))
                asyncio.run(storage.put_crypto(IMAGE_URL % '5'))
                return asyncio.run(storage.get_crypto(IMAGE_URL % '5'))

            def should_be_null(self, topic):
                expect(topic).to_be_null()

        class CanStoreCrypto(Vows.Context):
            def topic(self):
                config = Config(HBASE_STORAGE_TABLE=self.parent.parent.table,HBASE_STORAGE_SERVER_PORT=9090, SECURITY_KEY='ACME-SEC', STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)
                storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

                asyncio.run(storage.put(IMAGE_URL % '6', IMAGE_BYTES))
                asyncio.run(storage.put_crypto(IMAGE_URL % '6'))
                return asyncio.run(storage.get_crypto(IMAGE_URL % '6'))

            def should_have_proper_key(self, topic):
                expect(topic).to_equal('ACME-SEC')

    class DetectorVows(Vows.Context):
        class CanStoreDetectorData(Vows.Context):
            def topic(self):
                config = Config(HBASE_STORAGE_TABLE=self.parent.parent.table,HBASE_STORAGE_SERVER_PORT=9090)
                storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

                asyncio.run(storage.put(IMAGE_URL % '7', IMAGE_BYTES))
                asyncio.run(storage.put_detector_data(IMAGE_URL % '7', 'some-data'))
                return asyncio.run(storage.get_detector_data(IMAGE_URL % '7'))

            def should_equal_some_data(self, topic):
                expect(topic).to_equal('some-data')

        class ReturnsNoneIfNoDetectorData(Vows.Context):
            def topic(self):
                config = Config(HBASE_STORAGE_TABLE=self.parent.parent.table,HBASE_STORAGE_SERVER_PORT=9090)
                storage = Storage(Context(config=config, server=get_server('ACME-SEC')))

                return asyncio.run(storage.get_detector_data(IMAGE_URL % '10000'))

            def should_not_be_null(self, topic):
                expect(topic).to_be_null()
