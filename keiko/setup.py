"""Packaging script for keiko."""

from setuptools import find_packages, setup

from keiko.version import __version__

setup(
    name="keiko",
    version=__version__,
    author="MinVWS",
    url="https://openkat.nl/",
    packages=find_packages(exclude="tests"),
    include_package_data=True,
)
