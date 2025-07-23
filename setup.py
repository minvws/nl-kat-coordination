from setuptools import find_packages, setup

from openkat.version import __version__

setup(
    name="openkat",
    version=__version__,
    author="MinVWS",
    url="https://openkat.nl/",
    packages=find_packages(exclude="tests"),
    scripts=["manage.py"],
    include_package_data=True,
)
