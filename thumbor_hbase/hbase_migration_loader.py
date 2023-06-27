#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

import copy
import random

from thumbor_hbase.storage import Storage
from . import loader
from thumbor.context import Context
from thumbor.loaders import http_loader
from thumbor.utils import logger
from thumbor.loaders import LoaderResult

# When migrating between HBase databases, it may be useful to first look on the old system
# before resorting to HTTP.
async def load(context, path):

    # Call the old storage, if it doesn't work fall back to HTTP.
    old_server_config = copy.deepcopy(context.config)
    old_server_config.HBASE_STORAGE_SERVER_HOSTS = ["c5n1.gbif.org", "c5n2.gbif.org", "c5n3.gbif.org", "c5n4.gbif.org", "c5n6.gbif.org", "c5n7.gbif.org", "c5n8.gbif.org", "c5n9.gbif.org", "c5n10.gbif.org"]
    random.shuffle(old_server_config.HBASE_STORAGE_SERVER_HOSTS)
    old_server_config.HBASE_STORAGE_SERVER_PORT = 9090
    old_server_config.HBASE_STORAGE_TABLE = b'thumbor'
    old_server_config.HBASE_STORAGE_FAMILY = b'image'
    old_context = Context(context.server, old_server_config)
    storage = Storage(old_context)
    data = await storage.get(path)

    if data is None:
        logger.info("Image %s NOT found on %s", path, old_context.config.HBASE_STORAGE_SERVER_HOSTS[0])
        return await http_loader.load(context, path)
    else:
        logger.info("Image %s found on %s", path, old_context.config.HBASE_STORAGE_SERVER_HOSTS[0])
        result = LoaderResult()
        result.successful = True
        result.buffer = data

    return result
