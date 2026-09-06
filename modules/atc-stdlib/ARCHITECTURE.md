# ARCHITECTURE.md — atc-stdlib

> Copyright © Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.

## File Tree
```tree
atc-stdlib/
├── requirements.txt — Python dependencies (none — pure Python)
├── setup.py — pip installation configuration
├── README.md — Standard Library overview
└── src/
    ├── __init__.py — Package initialization
    └── stdlib/ — ATCLang standard library modules
```

## Module Descriptions
- `stdlib/` — ATCLang Standard Library implementations (collections, math, io, crypto, net)
- Pure Python implementation with no external dependencies

## Build System
- Python 3.11+ with pip
- No external dependencies required

## Dependencies
- atc-vm (ATC Virtual Machine for execution)
- atclang (ATCLang compiler)

## Status (Active/Migrated/Legacy)
Active (Python, Standard Library)
