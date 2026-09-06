# setup.py — atc-atclang
# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.

from setuptools import setup, find_packages

setup(
    name="atc-atclang",
    version="0.1.0",
    description="ATCLang mirror — proprietary language for A-TownChain OS",
    author="Michael Wroblewski / ShivaCore / A-TownChain-Okosystems",
    license="All Rights Reserved",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        # See requirements.txt for full dependency list
    ],
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "License :: Other/Proprietary License",
    ],
)
