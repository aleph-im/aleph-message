# -*- coding: utf-8 -*-
"""Aleph Message - Python library for the Aleph.im message specification
(c) 2022 OKESO for Aleph.im
"""

import os

from setuptools import setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

with open('README.md') as file:
    long_description = file.read()

setup(name='aleph-message',
      version='0.3.0',
      description='Aleph.im message specification ',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Hugo Herter',
      author_email='git@hugoherter.com',
      url='https://github.com/aleph-im/aleph-message',
      packages=['aleph_message', 'aleph_message.models'],
      package_data={"aleph_message": ["py.typed"],
                    "aleph_message.models": ["py.typed"]},
      data_files=[],
      install_requires=[
          'pydantic~=1.9.2',
          'typing_extensions~=4.3.0',
      ],
      license='MIT',
      platform='any',
      keywords="aleph.im message validation specification",
      classifiers=['Development Status :: 4 - Beta',
                   'Programming Language :: Python :: 3',
                   'Intended Audience :: Developers',
                   'Topic :: System :: Distributed Computing',
                   ],
      )
