#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "aiodns",
    "aiohttp",
    "attrs",
    "black",
    # "cchardet",
    "click",
    "logzero",
    "lxml",
    "pyyaml",
    "pytest",
    "requests",
]

setup(
    name="apix",
    version="0.4.0",
    description="API Explorer: Discover, Track, Test.",
    long_description=readme + "\n\n" + history,
    author="Jacob J Callahan",
    author_email="jacob.callahan05@@gmail.com",
    url="https://github.com/JacobCallahan/apix",
    packages=["apix", "apix.libtools", "apix.parsers"],
    entry_points={"console_scripts": ["apix=apix.commands:cli"]},
    include_package_data=True,
    install_requires=requirements,
    license="GNU General Public License v3",
    zip_safe=False,
    keywords="apix",
    classifiers=[
        "Development Status :: 2- Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11"
    ],
)
