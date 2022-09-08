#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Thumbor imaging service — HBase module
# https://github.com/thumbor-community/hbase_storage/

# Licensed under the MIT license:
# https://opensource.org/license/mit/

from setuptools import setup

__version__ = None
exec(open('thumbor_hbase/_version.py').read())

setup(
    name = "thumbor_hbase",
    packages = ["thumbor_hbase", "thumbor_hbase.hbase"],
    version = __version__,
    description = "HBase image storage for Thumbor",
    author = "Damien Hardy",
    author_email = "dhardy@viadeoteam.com",
    keywords = ["thumbor", "hbase", "hadoop", "images"],
    license = 'MIT',
    url = 'https://github.com/thumbor-community/hbase_storage/',
    classifiers = ['Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: MIT License',
                   'Natural Language :: English',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python :: 3.10',
                   'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
                   'Topic :: Multimedia :: Graphics :: Presentation'
    ],
    package_dir = {"thumbor_hbase": "thumbor_hbase"},
    install_requires=["thumbor>=7.3.0","thrift"],
    long_description = """\
Thumbor is a smart imaging service. It enables on-demand crop, resizing and flipping of images.
This module provide support for HBase as large, auto-replicating key/value backend storage for images.
"""
)
