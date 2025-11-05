#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

import os
import time
from hashlib import md5
from json import loads, dumps
from os.path import dirname, exists, getmtime, splitext
from shutil import move
from struct import pack, unpack
from uuid import uuid4

from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport, TTransportException
from thrift.protocol import TBinaryProtocol

from thumbor import storages
from thumbor.storages import file_storage
from thumbor.utils import logger

from thumbor_hbase import storage
from thumbor_hbase.hbase import Hbase
from thumbor_hbase.hbase.ttypes import Mutation

from thumbor.importer import Importer
from thumbor.transformer import Transformer
from thumbor.storages.no_storage import Storage as NoStorage
from thumbor.config import Config
from thumbor.context import Context
from thumbor.context import RequestParameters

# Store additional metadata relevant for occurrence images from GBIF.org.
#
# Store some images in file storage, and others in HBase.
#
# HBase table creation:
#   create 'thumbor',
#     {NAME => 'image', IS_MOB => 'true', MOB_THRESHOLD => '524288', IS_MOB => 'true', 'BLOCKCACHE' => 'false', 'BLOCKSIZE' => '262144'},
#     {NAME => 'metadata'},
#     {NUMREGIONS => 128, SPLITALGO => 'HexStringSplit'}
#
# HBase table scan:
#   scan 'thumbor',
#     {COLUMNS => ['metadata:image_size:toLong', 'metadata:created:toLong', 'metadata:accessed:toLong', 'metadata:hits:toLong', 'metadata']}
#
class Storage(storage.Storage):
    local_file_storage = None

    # Get from a local file if it exists, otherwise HBase
    def _get(self, key, col):
        logger.debug("_get column (or file) %s with key (or for path) %s", col, key)

        # Check local filesystem cache
        if self.local_file_storage is None:
            self._file_connect()
        local_file_available = self.local_file_exists(key)
        if local_file_available:
            logger.debug("Using local file %s", key)
            r = lambda: None
            r.value = self.local_file_get(key)
            return r

        # Check HBase
        key = self.makeKey(key)
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

    # Store to a local file in special cases, otherwise to HBase
    def _put(self, key, col, value):
        path = key
        key = self.makeKey(key)
        original_image_size = len(value)

        use_file_storage = False
        now = int(time.time())
        r = [
            Mutation(column=b'metadata:original_image_size', value=pack("!q", original_image_size)),
            Mutation(column=b'metadata:created', value=pack("!q", now)),
            Mutation(column=b'metadata:accessed', value=pack("!q", now)),
            Mutation(column=b'metadata:hits', value=pack("!q", 1))
        ]

        if 'hostname' in self.context.headers:
            hostname = self.context.headers['hostname']
            logger.debug("hostname %s %s", self.context.headers['hostname'], hostname)
            r += [
                Mutation(column=b'metadata:hostname', value=hostname.encode())
            ]
            use_file_storage |= hostname in self.context.config.LOCAL_FILE_STORAGE_HOSTNAMES
            if not use_file_storage:
                # NB only handles second level domains as that's all we need.
                domain = '.'.join(hostname.split('.')[-2:])
                use_file_storage |= domain in self.context.config.LOCAL_FILE_STORAGE_DOMAINS

        if 'start_time' in self.context.headers:
            retrieval_time_ms = int((time.time_ns()-self.context.headers['start_time'])/1000)
            r += [
                Mutation(column=b'metadata:retrieval_time_ms', value=pack("!q", retrieval_time_ms))
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

            use_file_storage |= dataset_key in self.context.config.LOCAL_FILE_STORAGE_DATASET_KEYS

        if 'unsafe' in self.context.headers:
            r += [
                Mutation(column=b'metadata:unsafe', value=self.context.headers['unsafe'].encode())
            ]

        # For particular hosts/datasets use file storage instead.  This is to avoid us filling up HBase
        # with huge amount of easily-accessed data (iNaturalist, Contentful etc).
        if use_file_storage:
            logger.debug("_put %d bytes into local file with path %s", original_image_size, path)
            if self.local_file_storage is None:
                self._file_connect()
            self.local_file_put(path, value)
        # Otherwise put in HBase
        else:
            # Further reduce storage use by limiting images to 1200x1200px
            source_width, source_height = self.context.request.engine.size
            if (source_width > 1200 or source_height > 1200 or original_image_size > 300000):
                logger.debug("Resizing large image (%dx%d, %dB) to max 1200x1200", source_width, source_height, original_image_size)
                # Temporary context for transformation
                importer = Importer(None)
                importer.detectors = []
                importer.storage = NoStorage
                config = Config()
                config.IGNORE_SMART_ERRORS = True
                ctx = Context(server=None, config=config, importer=importer)
                ctx.modules.engine = self.context.modules.engine
                ctx.request = RequestParameters(
                    fit_in=True,
                    width=1200,
                    height=1200,
                    extension="JPEG",
                    quality=85,
                    image="some.jpeg",
                    auto_png_to_jpg=True
                )
                ctx.request.engine = self.context.modules.engine
                ctx.request.engine.extension = ".jpeg"
                trans = Transformer(ctx)
                trans.img_operation_worker()
                results = ctx.request.engine.read(".jpeg", 85)
                value = results

            image_size = len(value)
            logger.debug("_put %d (orig %d) bytes into column %s for row %s", image_size, original_image_size, col, key)

            r += [
                Mutation(column=(self.data_fam + b':' + col), value=value),
                Mutation(column=b'metadata:image_size', value=pack("!q", image_size)),
            ]

            if self.storage is None:
                self._connect()

            try:
                self.storage.mutateRow(self.table, key, r, {})
            except:
                # Try once more, seems to happen if downloading takes too long.
                logger.warning("repeating _put %d bytes into column %s for row %s", image_size, col, key)
                self._connect()
                self.storage.mutateRow(self.table, key, r, {})

    def _file_connect(self):
        self.local_file_storage = file_storage.Storage(self.context)

    # sync version of method, copied from file_storage.py
    def local_file_put(self, path, file_bytes):
        file_abspath = self.local_file_storage.path_on_filesystem(path)
        temp_abspath = f"{file_abspath}.{str(uuid4()).replace('-', '')}"
        file_dir_abspath = dirname(file_abspath)

        logger.debug("creating tempfile for %s in %s...", path, temp_abspath)

        self.local_file_storage.ensure_dir(file_dir_abspath)

        with open(temp_abspath, "wb") as _file:
            _file.write(file_bytes)

        logger.debug("moving tempfile %s to %s...", temp_abspath, file_abspath)
        move(temp_abspath, file_abspath)

        return path

    # sync version of method, copied from file_storage.py
    def local_file_get(self, path):
        abs_path = self.local_file_storage.path_on_filesystem(path)

        resource_available = self.local_file_exists(path, path_on_filesystem=abs_path)
        if not resource_available:
            return None

        with open(abs_path, "rb") as source_file:
            return source_file.read()

    # sync version of method, copied from file_storage.py
    def local_file_exists(self, path, path_on_filesystem=None):
        if path_on_filesystem is None:
            path_on_filesystem = self.local_file_storage.path_on_filesystem(path)
        return os.path.exists(path_on_filesystem) and not self.local_file_storage.__is_expired(path_on_filesystem)
