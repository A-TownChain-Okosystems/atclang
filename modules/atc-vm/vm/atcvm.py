# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""ATC Virtual Machine — Stack-based bytecode execution engine."""
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class VMState:
    """VM execution state."""
    stack: List = field(default_factory=list)
    pc: int = 0
    halted: bool = False
    gas: int = 1000000
    memory: Dict[int, int] = field(default_factory=dict)


class ATCVM:
    """ATC Virtual Machine — executes ATCLang bytecode."""

    def __init__(self):
        self.state = VMState()
        self.ops = {
            0x00: self._op_nop,
            0x01: self._op_push,
            0x02: self._op_pop,
            0x03: self._op_add,
            0x04: self._op_sub,
            0x05: self._op_mul,
            0x06: self._op_div,
            0x07: self._op_dup,
            0x08: self._op_swap,
            0x09: self._op_store,
            0x0a: self._op_load,
            0x0b: self._op_jump,
            0x0c: self._op_jz,
            0x0d: self._op_eq,
            0x0e: self._op_lt,
            0x0f: self._op_gt,
            0x10: self._op_halt,
            0x11: self._op_print,
        }

    def execute(self, bytecode: bytes) -> List:
        """Execute bytecode and return output."""
        output = []
        self.state = VMState()
        while not self.state.halted and self.state.pc < len(bytecode):
            if self.state.gas <= 0:
                raise RuntimeError("Out of gas")
            opcode = bytecode[self.state.pc]
            self.state.pc += 1
            self.state.gas -= 1
            handler = self.ops.get(opcode, self._op_unknown)
            result = handler(bytecode)
            if result is not None:
                output.append(result)
        return output

    def _op_nop(self, bc): pass
    def _op_push(self, bc):
        val = int.from_bytes(bc[self.state.pc:self.state.pc+8], 'little')
        self.state.pc += 8
        self.state.stack.append(val)
    def _op_pop(self, bc): self.state.stack.pop()
    def _op_add(self, bc):
        b, a = self.state.stack.pop(), self.state.stack.pop()
        self.state.stack.append(a + b)
    def _op_sub(self, bc):
        b, a = self.state.stack.pop(), self.state.stack.pop()
        self.state.stack.append(a - b)
    def _op_mul(self, bc):
        b, a = self.state.stack.pop(), self.state.stack.pop()
        self.state.stack.append(a * b)
    def _op_div(self, bc):
        b, a = self.state.stack.pop(), self.state.stack.pop()
        if b == 0: raise ZeroDivisionError
        self.state.stack.append(a // b)
    def _op_dup(self, bc):
        self.state.stack.append(self.state.stack[-1])
    def _op_swap(self, bc):
        self.state.stack[-1], self.state.stack[-2] = self.state.stack[-2], self.state.stack[-1]
    def _op_store(self, bc):
        addr = self.state.stack.pop()
        val = self.state.stack.pop()
        self.state.memory[addr] = val
    def _op_load(self, bc):
        addr = self.state.stack.pop()
        self.state.stack.append(self.state.memory.get(addr, 0))
    def _op_jump(self, bc):
        self.state.pc = self.state.stack.pop()
    def _op_jz(self, bc):
        addr = self.state.stack.pop()
        val = self.state.stack.pop()
        if val == 0: self.state.pc = addr
    def _op_eq(self, bc):
        b, a = self.state.stack.pop(), self.state.stack.pop()
        self.state.stack.append(1 if a == b else 0)
    def _op_lt(self, bc):
        b, a = self.state.stack.pop(), self.state.stack.pop()
        self.state.stack.append(1 if a < b else 0)
    def _op_gt(self, bc):
        b, a = self.state.stack.pop(), self.state.stack.pop()
        self.state.stack.append(1 if a > b else 0)
    def _op_halt(self, bc): self.state.halted = True
    def _op_print(self, bc):
        val = self.state.stack.pop()
        return val
    def _op_unknown(self, bc):
        raise RuntimeError(f"Unknown opcode at pc={self.state.pc-1}")


if __name__ == "__main__":
    vm = ATCVM()
    # PUSH 5, PUSH 3, ADD, PRINT, HALT
    bc = bytes([0x01, 5,0,0,0,0,0,0,0, 0x01, 3,0,0,0,0,0,0,0, 0x03, 0x11, 0x10])
    print("Output:", vm.execute(bc))  # Should print 8
