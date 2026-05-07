import struct
from dataclasses import dataclass
from enum import IntEnum, unique


@unique
class Opcode(IntEnum):
    LD = 0x01
    LDR = 0x02
    LDI = 0x03
    ST = 0x04
    STR = 0x05

    ADD = 0x10
    SUB = 0x11
    MUL = 0x12
    DIV = 0x13
    REM = 0x14

    CMP = 0x20
    NOT = 0x21
    NEG = 0x22

    JMP = 0x30  # unconditional jump
    BEQ = 0x31  # branch if equal (Z = 1)
    BNE = 0x32  # branch if not equal (Z = 0)
    BGE = 0x33  # branch if greater or equal (N = 0)
    BGT = 0x34  # branch if greater (N = 0 && Z = 0)
    BLE = 0x35  # branch if less or equal (N = 1 || Z = 1)
    BLT = 0x36  # branch if less (N = 1)

    PUSH = 0x40
    POP = 0x41

    CALL = 0x50
    RET = 0x51

    HALT = 0xFF


@dataclass
class Instruction:
    opcode: Opcode
    operand: int = 0

    def to_bytes(self) -> bytes:
        return struct.pack(">I", self.encode())

    @staticmethod
    def from_bytes(data) -> 'Instruction':
        (word,) = struct.unpack('>I', data)
        return Instruction.decode(word)

    def encode(self):
        mask = (1 << 24) - 1
        op = self.operand & mask
        return (self.opcode.value << 24) | op

    @staticmethod
    def decode(word: int) -> 'Instruction':
        opcode_value = (word >> 24) & 0xFF
        operand = word & ((1 << 24) - 1)
        if operand & (1 << 23):  # sign-extend negative values
            operand -= (1 << 24)
        opcode = Opcode(opcode_value)
        return Instruction(opcode, operand)

    def __str__(self):
        return f"{self.opcode.name} {self.operand:#04x}"


def write_file(path: str, instructions: list[Instruction], data: list[int]) -> None:
    with open(path, 'wb') as f:
        for instr in instructions:
            f.write(instr.to_bytes())
        for cell in data:
            f.write(struct.pack('>I', cell))


def write_debug(path: str, instructions: list[Instruction], data: list[int]) -> None:
    base = len(instructions)
    with open(path, 'w', encoding='utf-8') as f:
        for addr, instr in enumerate(instructions):
            f.write(f'{addr:04x} - {instr.encode():08x} - {instr}\n')
        for offset, cell in enumerate(data):
            addr = base + offset
            f.write(f'{addr:04x} - {cell & 0xFFFFFFFF:08x} - .word {cell:#x}\n')


def read_file(path: str) -> list[int]:
    with open(path, 'rb') as f:
        blob = f.read()
    n = len(blob) // 4
    return list(struct.unpack(f'>{n}I', blob))
