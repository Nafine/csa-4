from enum import IntEnum

from isa import Opcode


class ArSel(IntEnum):
    IP = 0b00
    CR_ARG = 0b01
    SP = 0b10


class AluLeft(IntEnum):
    ZERO = 0
    ACC = 1
    SP = 2


class AluRight(IntEnum):
    ZERO = 0
    CR_ARG = 1
    IP = 2
    DR = 3


class Alu(IntEnum):
    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    REM = 4
    INC = 5  # left + right + 1
    DEC = 6  # left + right - 1


class Cond(IntEnum):
    NONE = 0
    ALWAYS = 0b001
    EQ = 0b010  # Z == 1
    GE = 0b011  # N == 0
    NE = 0b100  # Z == 0
    LT = 0b101  # N == 1
    DECODE = 0b111  # MP <- DECODER[CR.opcode]


class MemSrc(IntEnum):
    ACC = 0
    IP = 1


def encode_signals(halted=0,
                   flag_l=0, acc_l=0, dr_l=0, sp_l=0, ip_l=0, cr_l=0, ar_l=0, mem_w=0,
                   mem_src=MemSrc.ACC,
                   ar_sel=ArSel.IP,
                   alu_left=AluLeft.ZERO, alu_right=AluRight.ZERO,
                   alu=Alu.ADD, cond=Cond.NONE, next_addr=0):
    return (
            (halted & 1) << 27 |
            (flag_l & 1) << 26 |
            (acc_l & 1) << 25 |
            (dr_l & 1) << 24 |
            (sp_l & 1) << 23 |
            (ip_l & 1) << 22 |
            (cr_l & 1) << 21 |
            (ar_l & 1) << 20 |
            (mem_src & 1) << 19 |
            (mem_w & 1) << 18 |
            (int(ar_sel) & 0b11) << 16 |
            (int(alu_left) & 0b11) << 14 |
            (int(alu_right) & 0b11) << 12 |
            (int(alu) & 0b111) << 9 |
            (int(cond) & 0b111) << 6 |
            (next_addr & 0b111111)
    )


MROM = [0] * 64

# FETCH
MROM[0] = encode_signals(ar_l=1, ar_sel=ArSel.IP)  # AR <- IP
MROM[1] = encode_signals(dr_l=1, ip_l=1, alu_right=AluRight.IP, alu=Alu.INC)  # DR <- Mem[AR]; IP <- IP + 1
MROM[2] = encode_signals(cr_l=1, alu_right=AluRight.DR, cond=Cond.DECODE)  # CR <- DR; -> DECODER[opcode]

# LOAD: ACC <- Mem[arg]
MROM[3] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[4] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[5] = encode_signals(acc_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS, next_addr=0)  # ACC <- DR; -> FETCH

# LOAD IMM: ACC <- CR.arg
MROM[6] = encode_signals(alu_right=AluRight.CR_ARG, acc_l=1, cond=Cond.ALWAYS, next_addr=0)  # ACC <- CR.arg; -> FETCH

# STORE: Mem[arg] <- ACC
MROM[7] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[8] = encode_signals(mem_w=1, cond=Cond.ALWAYS, next_addr=0)  # Mem[AR] <- ACC; -> FETCH

# ADD: ACC <- ACC + Mem[arg]
MROM[9] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[10] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[11] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, cond=Cond.ALWAYS,
                          next_addr=0)  # ADD: N, Z, ACC <- ACC + DR; -> FETCH

# SUB: ACC <- ACC - Mem[arg]
MROM[12] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[13] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[14] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.SUB, cond=Cond.ALWAYS,
                          next_addr=0)  # SUB: N, Z, ACC <- ACC - DR; -> FETCH

# MUL: ACC <- ACC * Mem[arg]
MROM[15] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[16] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[17] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.MUL, cond=Cond.ALWAYS,
                          next_addr=0)  # MUL: N, Z, ACC <- ACC * DR; -> FETCH

# DIV: ACC <- ACC / Mem[arg]
MROM[18] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[19] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[20] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.DIV, cond=Cond.ALWAYS,
                          next_addr=0)  # DIV: N, Z, ACC <- ACC // DR; -> FETCH

# REM: ACC <- ACC % Mem[arg]
MROM[21] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[22] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[23] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.REM, cond=Cond.ALWAYS,
                          next_addr=0)  # REM: N, Z, ACC <- ACC * DR; -> FETCH

# CMP: N,Z <- ACC - Mem[arg]
MROM[24] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[25] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[26] = encode_signals(flag_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.SUB, cond=Cond.ALWAYS,
                          next_addr=0)  # CMP: N,Z <- ACC - DR; -> FETCH

# JMP: IP <- arg
MROM[27] = encode_signals(ip_l=1, alu_right=AluRight.CR_ARG, cond=Cond.ALWAYS, next_addr=0)  # IP <- ARG; -> FETCH

# BEQ: IP <- arg if Z = 1
MROM[28] = encode_signals(cond=Cond.EQ, next_addr=27)
MROM[29] = encode_signals(cond=Cond.ALWAYS, next_addr=0)

# BNE: IP <- arg if Z = 0
MROM[30] = encode_signals(cond=Cond.NE, next_addr=27)
MROM[31] = encode_signals(cond=Cond.ALWAYS, next_addr=0)

# BGE: IP <- arg if N = 0
MROM[32] = encode_signals(cond=Cond.GE, next_addr=27)
MROM[33] = encode_signals(cond=Cond.ALWAYS, next_addr=0)

# BLT: IP < arg if N = 1
MROM[34] = encode_signals(cond=Cond.LT, next_addr=27)
MROM[35] = encode_signals(cond=Cond.ALWAYS, next_addr=0)

# PUSH: Mem[SP] <- ACC
MROM[36] = encode_signals(ar_l=1, ar_sel=ArSel.SP)  # AR <- SP
MROM[37] = encode_signals(mem_w=1, sp_l=1, alu_left=AluLeft.SP, alu=Alu.DEC, cond=Cond.ALWAYS,
                          next_addr=0)  # Mem[AR] <- ACC; SP <- SP - 1; -> FETCH

# POP: ACC <- Mem[++SP]
MROM[38] = encode_signals(sp_l=1, alu_left=AluLeft.SP, alu=Alu.INC)  # SP++
MROM[39] = encode_signals(ar_l=1, ar_sel=ArSel.SP)  # AR <- SP
MROM[40] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[41] = encode_signals(acc_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS, next_addr=0)  # ACC <- DR; -> FETCH

# CALL: Mem[SP] <- IP; SP--; IP <- CR.arg
MROM[42] = encode_signals(ar_l=1, ar_sel=ArSel.SP)  # AR <- SP
MROM[43] = encode_signals(mem_w=1, mem_src=MemSrc.IP,
                          sp_l=1, alu_left=AluLeft.SP, alu=Alu.DEC)  # Mem[AR] <- IP; SP--
MROM[44] = encode_signals(ip_l=1, alu_right=AluRight.CR_ARG, cond=Cond.ALWAYS, next_addr=0)  # IP <- CR.arg; -> FETCH

# RET: IP <- Mem[++SP]
MROM[45] = encode_signals(sp_l=1, alu_left=AluLeft.SP, alu=Alu.INC)  # SP++
MROM[46] = encode_signals(ar_l=1, ar_sel=ArSel.SP)  # AR <- SP
MROM[47] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[48] = encode_signals(ip_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS, next_addr=0)  # IP <- DR; -> FETCH

# DECODER[opcode] = адрес первого uop команды.
# Неизвестный опкод ведёт на 0 (FETCH) -- по сути пропуск.

DECODER = [0] * 256
DECODER[Opcode.LD] = 3
DECODER[Opcode.LDI] = 6
DECODER[Opcode.ST] = 7
DECODER[Opcode.ADD] = 9
DECODER[Opcode.SUB] = 12
DECODER[Opcode.MUL] = 15
DECODER[Opcode.DIV] = 18
DECODER[Opcode.REM] = 21
DECODER[Opcode.CMP] = 24
DECODER[Opcode.JMP] = 27
DECODER[Opcode.BEQ] = 28
DECODER[Opcode.BNE] = 30
DECODER[Opcode.BGE] = 32
DECODER[Opcode.BLT] = 34
DECODER[Opcode.PUSH] = 36
DECODER[Opcode.POP] = 38
DECODER[Opcode.CALL] = 42
DECODER[Opcode.RET] = 45
