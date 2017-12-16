import os
from setuptools import find_packages
from distutils.core import setup

version = "0.0.dev1"

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, "README.md")).read()
except IOError:
    README = ""

install_requires = [
    "numpy",
    "regex",
    "requests"
]

setup(
    name="motu",
    version=version,
    packages=find_packages(),
    include_package_data=False,
    zip_safe=False,
    install_requires=install_requires,
)
