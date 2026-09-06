# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang — Die Programmiersprache des A-TownChain Ökosystems
Version: 0.3.0-alpha
"""
ATCLANG_VERSION = "0.3.0"

from atclang.lexer.lexer import ATCLexer, Token, TT, tokenize
from atclang.parser.parser import ATCParser, parse
from atclang.compiler.compiler import ATCCompiler, compile_source, disassemble
from atclang.vm.atcvm import ATCVM, OP, Instruction
