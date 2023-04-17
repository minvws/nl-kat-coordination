"""Packaging script for keiko."""
from setuptools import find_packages, setup

setup(name="keiko", author="MinVWS", packages=find_packages(exclude="tests"), include_package_data=True)
