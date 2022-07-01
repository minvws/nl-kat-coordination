from setuptools import setup, find_packages

from octopoes.version import __version__

setup(
    name="octopoes",
    version=__version__,
    description="A Python ORM to persist objects in XTDB",
    author="Jesse Lisser",
    packages=find_packages(),
    package_data={"octopoes": ["data/logging.yml"]},
    install_requires=[
        "pydantic~=1.8.2",
        "dnspython~=2.1.0",
    ],
)
