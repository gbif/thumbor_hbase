#!/usr/bin/python
# -*- coding: utf-8 -*-

from tornado.concurrent import return_future
from . import loader
from thumbor.loaders import http_loader
from thumbor.utils import logger

@return_future
def load(context, path, callback):

    def callback_wrapper(result):
        if result.successful:
            logger.info("Image "+path+" found on C5")
            callback(result)
        else:
            # If file_loader failed try http_loader
            logger.info("Image "+path+" NOT found on C5")
            http_loader.load(context, path, callback)

    # Call C5 storage, if it doesn't work, go back to HTTP.
    # Provide this config here to override default.
    # (This is ugly, just used for a test.)
    c5 = lambda: None
    c5.config = lambda: None
    c5.config.HBASE_STORAGE_SERVER_HOSTS = ["c5master3-vh.gbif.org", "c5master2-vh.gbif.org", "c5master1-vh.gbif.org"]
    c5.config.HBASE_STORAGE_SERVER_PORT = 9090
    c5.config.HBASE_STORAGE_TABLE = "thumbor"
    c5.config.HBASE_STORAGE_FAMILY = "image"

    loader.load(c5, path, callback_wrapper)
