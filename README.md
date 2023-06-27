HBase Storage Module for Thumbor
===================================

[![Build Status](https://github.com/gbif/thumbor_hbase/actions/workflows/python.yml/badge.svg?branch=master)](https://github.com/gbif/thumbor_hbase/actions/workflows/python.yml)

Introduction
------------

[Thumbor](https://www.thumbor.org/) is a smart imaging service. It enables on-demand crop, resizing and flipping of images.

[HBase](https://hbase.apache.org) is a column oriented database from the Hadoop ecosystem.

This module provide support for Hadoop HBase as a large auto replicant key/value backend storage for images in Thumbor.


Installation
------------

The current version of the module is **0.20**.

In order to install the HBase Storage Module for Thumbor, you have to install Hadoop / HBase ecosystem first.

## Hadoop / HBase installation

The HBase Storage Module for Thumbor was originally developed and tested on Cloudera CDH3 Hadoop on a Debian system.

The migration to Python 3 and Thumbor 7 was tested on Cloudera CDH5 Hadoop on a CentOS system.

You will need to install HBase and HBase-Thrift.

## Thumbor installation

You have to install [Thumbor](https://www.thumbor.org/) following the [Thumbor Installation Guide](https://thumbor.readthedocs.io/en/latest/installing.html).

## HBase Storage Module installation

Finally, install the HBase Storage Module :

    pip install git+https://github.com/gbif/thumbor_hbase


Usage
-----

Using it is simple, just change your configuration in thumbor.conf:

    HBASE_STORAGE_SERVER_HOST = 'localhost'
    HBASE_STORAGE_SERVER_PORT = 9090
    HBASE_STORAGE_TABLE = b'storage-table'
    HBASE_STORAGE_FAMILY = b'storage-family'

and create a suitable table in HBase:

    create 'thumbor', 'image'

You may well want to investigate [Medium Object Storage](https://hbase.apache.org/book.html#hbase_mob) and adjust this command accordingly:

    create 'thumbor',
      {NAME => 'image', IS_MOB => 'true', MOB_THRESHOLD => '524288', IS_MOB => 'true', 'BLOCKCACHE' => 'false', 'BLOCKSIZE' => '262144'},
      {NUMREGIONS => 128, SPLITALGO => 'HexStringSplit'}

If you want to use thumbor_hbase for loading original images, change your thumbor.conf to read:

    LOADER = "thumbor_hbase.loader"

If you want to use thumbor_hbase for storage of original images, change your thumbor.conf to read:

    STORAGE = "thumbor_hbase.storage"


Testing
-------

In order to execute [pyvows](https://github.com/heynemann/pyvows) tests, you have to install pyvows :

    pip install pyvows

and run tests with :

    pyvows -c -l thumbor_hbase


License
-------

    Licensed under the MIT license:
    https://opensource.org/license/mit/
    Copyright © 2011 globo.com timehome@corp.globo.com
