#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

from os.path import join, abspath, dirname

from thumbor.context import ServerParameters, Context
from thumbor.config import Config
from thumbor.importer import Importer

IMAGE_URL = 's.glbimg.com/some/image_%s.jpg'
IMAGE_PATH = join(abspath(dirname(__file__)), 'image.jpg')

with open(IMAGE_PATH, 'rb') as img:
    IMAGE_BYTES = img.read()

def get_server(key=None):
    server_params = ServerParameters(8888, 'localhost', 'thumbor.conf', None, 'info', None)
    server_params.security_key = key
    return server_params

def get_context(server=None, config=None, importer=None):
    if not server:
        server = get_server()

    if not config:
        config = Config()

    if not importer:
        importer = Importer(config)

    ctx = Context(server=server, config=config, importer=importer)
    return ctx
