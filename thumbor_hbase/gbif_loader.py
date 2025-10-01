#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

import hashlib
import json
import time

from urllib.parse import urlparse, quote, unquote
from thumbor_hbase.storage import Storage
from . import hbase_migration_loader
from thumbor.context import Context
from thumbor.config import Config
from thumbor.loaders import LoaderResult, http_loader
from thumbor.utils import logger

# A loader specific to occurrence images on GBIF.org.
#
# If the path is like /occurrence/1234/media/1234hash5678, query the GBIF occurrence API to find
# the image (on the occurrence) with the matching hash, and retrieve using HTTP.
#
# In such cases, unsafe requests are fine.
#
async def load(context, url_or_gbif_query):

    if (url_or_gbif_query.startswith("occurrence")):
        query = url_or_gbif_query.split('/')
        logger.debug("Loading occurrence image %s", query)
        occurrence_id = query[1]
        image_url_hash = query[3]

        occurrence_req = await http_loader.load(
            context,
            context.config.GBIF_OCCURRENCE_API + occurrence_id
        )

        if not occurrence_req.successful:
            occurrence_req.extras["reason"] = "Occurrence %s not found" % (occurrence_id)
            return occurrence_req

        #logger.debug("Occurrence JSON %s", occurrence_req.buffer)

        occurrence = json.loads(occurrence_req.buffer)

        url = None
        if 'media' in occurrence:
            for m in occurrence['media']:
                if 'identifier' in m:
                    m_hash = hashlib.md5(m['identifier'].encode('utf-8'))
                    logger.debug("On occurrence %s, media %s hashes to %s", occurrence_id, m['identifier'], m_hash.hexdigest())
                    if m_hash.hexdigest() == image_url_hash:
                        url = m['identifier']
                        hostname = urlparse(url).hostname
                        dataset_key = occurrence['datasetKey']
                        logger.debug("On occurrence %s, found media %s to be %s", occurrence_id, image_url_hash, url)

                        context.headers['dataset_key'] = dataset_key
                        context.headers['occurrence_id'] = occurrence_id
                        context.headers['image_url_hash'] = image_url_hash
                        context.headers['url'] = url
                        context.headers['hostname'] = hostname
                        context.headers['start_time'] = time.time_ns()

                        # Proxied URLs that work on HTTP only.
                        #if hostname == 'www.tropicos.org':
                        #    logger.debug("Accessing Tropicos image %s with HTTP instead", url)
                        #    url = url.replace('https:', 'http:')

                        return await http_loader.load(context, quote(url))
                        # During migration, read from the old HBase and fall back to HTTP.
                        #return await hbase_migration_loader.load(context, quote(url))

        if url is None:
            result = LoaderResult()
            result.successful = False
            result.error = LoaderResult.ERROR_NOT_FOUND
            result.extras["reason"] = "Media with hash/url %s not found for occurrence %s" % (image_url_hash, occurrence_id)
            logger.info(result.extras["reason"])
            return result

    else:
        # Normal Thumbor image request.  Expect to have the request hash, otherwise return 403
        hostname = urlparse(unquote(url_or_gbif_query)).hostname
        context.headers['start_time'] = time.time_ns()
        if hostname:
            context.headers['hostname'] = hostname
        if context.request.unsafe:
            result = LoaderResult()
            result.successful = False
            result.error = 403
            result.extras["reason"] = "Images referenced directly must use signed requests"

            # During migration, allow unsigned requests.
            #logger.info("Unsigned request for %s denied", url_or_gbif_query)
            #return result
            logger.warning("Unsigned request for %s ALLOWED ANYWAY", url_or_gbif_query)
            context.headers['unsafe'] = 'unsafe'
            return await http_loader.load(context, url_or_gbif_query)

            # During migration, read from the old HBase and fall back to HTTP.
            #return await hbase_migration_loader.load(context, url_or_gbif_query)
        else:
            logger.debug("Loading non-occurrence image %s", url_or_gbif_query)
            return await http_loader.load(context, url_or_gbif_query)
            # During migration, try the old HBase instead.
            #return await hbase_migration_loader.load(context, url_or_gbif_query)
