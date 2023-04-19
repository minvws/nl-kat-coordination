from setuptools import find_packages, setup

from octopoes.version import __version__

setup(
    name="octopoes",
    version=__version__,
    description="A Python ORM to persist objects in XTDB",
    author="Jesse Lisser",
    packages=find_packages(exclude="tests"),
    package_data={"octopoes": ["data/logging.yml"]},
    include_package_data=True,
    install_requires=[
        "pydantic~=1.10.2",
        "jsonschema~=4.17.0",
        "dnspython~=2.1.0",
    ],
)
