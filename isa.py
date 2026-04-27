from dataclasses import dataclass
from enum import unique, IntEnum


@unique
class Opcode(IntEnum):
    LD = 0x01
    LDI = 0x02
    ST = 0x03

    ADD = 0x10
    SUB = 0x11
    MUL = 0x12
    DIV = 0x13
    REM = 0x14

    CMP = 0x20
    NOT = 0x21
    NEG = 0x22

    JMP = 0x30  # unconditional jump
    BEQ = 0x31  # branch if equal (Z=1)
    BNE = 0x32  # branch if not equal (Z=0)
    BGE = 0x33  # branch if greater or equal (N=0)
    BLT = 0x34  # branch if less (N=1)

    CALL = 0x40
    RET = 0x41
    PUSH = 0x42
    POP = 0x43

    HALT = 0xFF


@dataclass
class Instruction:
    opcode: Opcode
    operand: int = 0

    def to_binary(self):
        mask = (1 << 24) - 1
        op = self.operand & mask
        return (self.opcode.value << 24) | op

    @staticmethod
    def from_binary(word: int) -> 'Instruction':
        opcode_value = (word >> 24) & 0xFF
        operand = word & ((1 << 24) - 1)
        if operand & (1 << 23):  # sign-extend negative values
            operand -= (1 << 24)
        opcode = Opcode(opcode_value)
        return Instruction(opcode, operand)

    def __str__(self):
        return f"{self.opcode.name} {self.operand:#04x}"
