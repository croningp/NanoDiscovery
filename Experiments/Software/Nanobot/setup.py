from distutils.core import setup
from setuptools import find_packages

setup(
    name="nanobot",
    version="2.1.0",
    description="Core of the Nanobot platform",
    author="Graham Keenan",
    author_email="graham.keenan@glasgow.ac.uk",
    packages=find_packages(),
    install_requires=[
        "pyserial>=3.4"
    ]
)
