from setuptools import setup, find_packages

from bytes.version import __version__

setup(
    name="bytes",
    version=__version__,
    author="MinVWS",
    packages=find_packages(exclude="tests"),
    include_package_data=True,
)
