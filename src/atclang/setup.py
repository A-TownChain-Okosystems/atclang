# setup.py — atclang
# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.

from setuptools import setup, find_packages

setup(
    name="atclang",
    version="0.1.0",
    description="ATCLang — language and compiler toolchain",
    author="Michael Wroblewski / ShivaCore / A-TownChain-Okosystems",
    license="Apache-2.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: Apache Software License",
    ],
)
