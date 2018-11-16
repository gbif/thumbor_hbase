#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor_hbase.storage import Storage
from thumbor.context import Context
from thumbor.config import Config
from thumbor.loaders import LoaderResult

def load(context, path, callback):

    def callback_wrapper(result):
        r = LoaderResult()
        if result is not None:
            r.successful = True
            r.buffer = result
        else:
            r.error = LoaderResult.ERROR_NOT_FOUND
            r.successful = False

        callback(r)

    storage = Storage(context)
    storage.get(path, callback_wrapper)
