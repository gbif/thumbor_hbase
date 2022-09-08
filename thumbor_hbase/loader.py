#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

from thumbor_hbase.storage import Storage
from thumbor.context import Context
from thumbor.config import Config
from thumbor.loaders import LoaderResult

async def load(context, path):
    storage = Storage(context)
    data = await storage.get(path)

    result = LoaderResult()

    if data is None:
        result.successful = False
        result.error = LoaderResult.ERROR_NOT_FOUND
    else:
        result.successful = True
        result.buffer = data

    return result
