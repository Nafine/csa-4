from enum import IntEnum

from isa import Opcode


class ArSel(IntEnum):
    IP = 0b0
    CR_ARG = 0b1


class AluLeft(IntEnum):
    ZERO = 0
    ACC = 1
    SP = 2


class AluRight(IntEnum):
    ZERO = 0
    CR = 1
    IP = 2
    MEM = 3  # Mem[AR]


class Alu(IntEnum):
    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    INC = 4  # left + right + 1
    DEC = 5  # left + right - 1


class Cond(IntEnum):
    NONE = 0
    ALWAYS = 0b001
    EQ = 0b010  # Z == 1
    GE = 0b011  # N == 0
    NE = 0b100  # Z == 0
    LT = 0b101  # N == 1
    DECODE = 0b111  # MP <- DECODER[CR.opcode]


def encode_signals(halted=0,
                   acc_l=0, sp_l=0, ip_l=0, cr_l=0, ar_l=0, mem_w=0,
                   ar_sel=ArSel.IP,
                   alu_left=AluLeft.ZERO, alu_right=AluRight.ZERO,
                   alu=Alu.ADD, cond=Cond.NONE, next_addr=0):
    return (
            (halted & 1) << 23 |
            (acc_l & 1) << 22 |
            (sp_l & 1) << 21 |
            (ip_l & 1) << 20 |
            (cr_l & 1) << 19 |
            (ar_l & 1) << 18 |
            (mem_w & 1) << 17 |
            (int(ar_sel) & 1) << 16 |
            (int(alu_left) & 0b11) << 14 |
            (int(alu_right) & 0b11) << 12 |
            (int(alu) & 0b111) << 9 |
            (int(cond) & 0b111) << 6 |
            (next_addr & 0b111111)
    )


MROM = [0] * 64

# FETCH
MROM[0] = encode_signals(ar_l=1, ar_sel=ArSel.IP)  # AR <- IP
MROM[1] = encode_signals(alu_right=AluRight.MEM, cr_l=1)  # CR <- Mem[AR]
MROM[2] = encode_signals(alu_right=AluRight.IP, alu=Alu.INC, ip_l=1,
                         cond=Cond.DECODE)  # IP <- IP + 1; -> DECODER[opcode]

# LOAD: ACC <- Mem[arg]
MROM[3] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[4] = encode_signals(alu_right=AluRight.MEM, acc_l=1, cond=Cond.ALWAYS, next_addr=0)  # ACC <- Mem[AR]; -> FETCH

# STORE: Mem[arg] <- ACC
MROM[5] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[6] = encode_signals(mem_w=1, cond=Cond.ALWAYS, next_addr=0)  # Mem[AR] <- ACC; -> FETCH

# DECODER[opcode] = адрес первого uop команды.
# Неизвестный опкод ведёт на 0 (FETCH) -- по сути пропуск.

DECODER = [0] * 256
DECODER[Opcode.LD] = 3
DECODER[Opcode.ST] = 5
