#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Use HBase to track HTTP connections across Thumbor processes.
# Limit by up to four connections to any single domain.

import copy
import random

from struct import pack, unpack
from urllib.parse import urlparse, quote, unquote
from time import sleep

from thumbor_hbase import storage
from thumbor_hbase.hbase import Hbase
from thumbor_hbase.hbase.ttypes import Mutation
from thumbor_hbase.storage import Storage

from . import loader
from thumbor.context import Context
from thumbor.loaders import http_loader
from thumbor.utils import logger
from thumbor.loaders import LoaderResult

async def load(context, path):

    # Storage should be connected, since Thumbor will have checked the HBase cache already
    storage = Storage(context).storage

    # Increment the HBase value for the domain.
    table = context.config.HBASE_POOL_TABLE
    key = urlparse(unquote(path)).hostname.encode('utf-8')

    slots = [b'pool:slot_1', b'pool:slot_2', b'pool:slot_3', b'pool:slot_4', b'pool:slot_5', b'pool:slot_6', b'pool:slot_7', b'pool:slot_8', b'pool:slot_9', b'pool:slot_10', b'pool:slot_11', b'pool:slot_12', b'pool:slot_13', b'pool:slot_14', b'pool:slot_15', b'pool:slot_16', b'pool:slot_17', b'pool:slot_18', b'pool:slot_19', b'pool:slot_20']
    random.shuffle(slots)
    try:
        for n in [1, 2, 3, 4, 5]:
            for slot in slots:
                slot_value = Mutation(column=slot, value=pack("!q", 1))
                slot_result = storage.checkAndPut(table, key, slot, None, slot_value, None)

                if slot_result:
                    logger.debug("Using slot " + slot.decode('utf-8') + " for " + key.decode('utf-8'))
                    r = await http_loader.load(context, path)
                    slot_free = [Mutation(isDelete=True, column=slot)]
                    slot_result = storage.mutateRow(table, key, slot_free, None)
                    return r
            sleep(random.random() / 2)

        logger.warn("Refusing request for image " + unquote(path) + ", too many connections to " + key.decode('utf-8'))
        r = LoaderResult()
        r.successful = False
        r.error = LoaderResult.ERROR_TIMEOUT
        return r
    except IndexError:
        r = None
        logger.error("IndexError finding a connection slot from HBase; key %s path %s", key, path)
    except:
        r = None
        logger.error("Error finding a connection slot from HBase; key %s path %s", key, path)
    return r
