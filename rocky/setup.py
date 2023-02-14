from setuptools import setup, find_packages
from rocky.version import __version__


setup(
    name="rocky",
    version=__version__,
    url="https://openkat.nl/",
    packages=find_packages(exclude="tests"),
    scripts=["manage.py"],
    include_package_data=True,
)
