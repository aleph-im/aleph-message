# -*- coding: utf-8 -*-
"""Aleph Message - Python library for the Aleph.im message specification
(c) 2022 OKESO for Aleph.im
"""

import os
import re


def get_version():
    version_file = os.path.join("aleph_message", "__init__.py")
    initfile_lines = open(version_file, "rt").readlines()
    version = r"^__version__ = ['\"]([^'\"]*)['\"]"

    for line in initfile_lines:
        mo = re.search(version, line, re.M)
        if mo:
            return mo.group(1)
    raise RuntimeError(f"Unable to find version string in {version_file}.")


from setuptools import setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

with open("README.md") as file:
    long_description = file.read()

setup(
    name="aleph-message",
    version=get_version(),
    description="Aleph.im message specification ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Hugo Herter",
    author_email="git@hugoherter.com",
    url="https://github.com/aleph-im/aleph-message",
    packages=[
        "aleph_message",
        "aleph_message.models",
        "aleph_message.models.execution",
    ],
    package_data={
        "aleph_message": ["py.typed"],
        "aleph_message.models": ["py.typed"],
        "aleph_message.models.execution": ["py.typed"],
    },
    data_files=[],
    install_requires=[
        "pydantic~=1.10.5",
        "typing_extensions~=4.5.0",
    ],
    license="MIT",
    platform="any",
    keywords="aleph.im message validation specification",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Topic :: System :: Distributed Computing",
    ],
)
