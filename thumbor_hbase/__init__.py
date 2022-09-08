#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

from ._version import __version__

# HBASE STORAGE OPTIONS
from thumbor.config import Config
Config.define('HBASE_STORAGE_SERVER_HOST', 'localhost', 'Thrift HBase interface host for storage', 'HBase Storage')
Config.define('HBASE_STORAGE_SERVER_HOSTS', None, 'Thrift HBase interface sosts for storage', 'HBase Storage')
Config.define('HBASE_STORAGE_SERVER_PORT', 9090, 'Thrift HBase interface port for storage', 'HBase Storage')
Config.define('HBASE_STORAGE_TABLE', b'thumbor', 'Thrift HBase table for storage', 'HBase Storage')
Config.define('HBASE_STORAGE_FAMILY', b'images', 'Thrift HBase column family for storage', 'HBase Storage')
