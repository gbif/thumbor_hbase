#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license: 
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2013 Damien Hardy dhardy@viadeoteam.com


from setuptools import setup

__version__ = None
execfile('thumbor_hbase/_version.py')

setup(
    name = "thumbor_hbase",
    packages = ["thumbor_hbase"],
    version = __version__,
    description = "HBase image storage for Thumbor",
    author = "Damien Hardy",
    author_email = "dhardy@viadeoteam.com",
    keywords = ["thumbor", "hbase", "hadoop", "images"],
    license = 'MIT',
    url = 'https://github.com/dhardy92/thumbor_hbase',
    classifiers = ['Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: MIT License',
                   'Natural Language :: English',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python :: 2.6',
                   'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
                   'Topic :: Multimedia :: Graphics :: Presentation'
    ],
    package_dir = {"thumbor_hbase": "thumbor_hbase"},
    install_requires=["thumbor>=5.0.3","hbase_thrift"],
    long_description = """\
Thumbor is a smart imaging service. It enables on-demand crop, resizing and flipping of images.
This module provide support for hbase as large auto replicant key/value backend storage for images.
"""
)
