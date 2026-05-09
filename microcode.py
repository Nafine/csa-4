from enum import IntEnum

from isa import Opcode


class ArSel(IntEnum):
    IP = 0b00
    CR_ARG = 0b01
    SP = 0b10
    DR = 0b11


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
    NOT = 7


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


def encode_signals(
        halted: int = 0,
        flag_l: int = 0, acc_l: int = 0, dr_l: int = 0, sp_l: int = 0,
        ip_l: int = 0, cr_l: int = 0, ar_l: int = 0, mem_w: int = 0,
        mem_src: MemSrc = MemSrc.ACC,
        ar_sel: ArSel = ArSel.IP,
        alu_left: AluLeft = AluLeft.ZERO, alu_right: AluRight = AluRight.ZERO,
        alu: Alu = Alu.ADD, cond: Cond = Cond.NONE, next_addr: int = 0,
) -> int:
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


MROM = [0] * 128

# FETCH
MROM[0] = encode_signals(ar_l=1, ar_sel=ArSel.IP)  # AR <- IP
MROM[1] = encode_signals(dr_l=1, ip_l=1, alu_right=AluRight.IP, alu=Alu.INC)  # DR <- Mem[AR]; IP <- IP + 1
MROM[2] = encode_signals(cr_l=1, alu_right=AluRight.DR, cond=Cond.DECODE)  # CR <- DR; -> DECODER[opcode]

# LOAD: ACC <- Mem[arg]
MROM[3] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[4] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[5] = encode_signals(flag_l=1, acc_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS, next_addr=0)  # ACC <- DR; -> FETCH

# LDR: ACC <- Mem[Mem[arg]]
MROM[6] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[7] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[8] = encode_signals(ar_l=1, ar_sel=ArSel.DR)  # AR <- DR
MROM[9] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[10] = encode_signals(flag_l=1, acc_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS,
                          next_addr=0)  # ACC <- DR; -> FETCH

# LOAD IMM: ACC <- CR.arg
MROM[11] = encode_signals(flag_l=1, acc_l=1, alu_right=AluRight.CR_ARG, cond=Cond.ALWAYS,
                          next_addr=0)  # ACC <- CR.arg; -> FETCH

# STORE: Mem[arg] <- ACC
MROM[12] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[13] = encode_signals(mem_w=1, cond=Cond.ALWAYS, next_addr=0)  # Mem[AR] <- ACC; -> FETCH

# STR: Mem[Mem[arg]] <- ACC
MROM[14] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[15] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[16] = encode_signals(ar_l=1, ar_sel=ArSel.DR)  # AR <- DR
MROM[17] = encode_signals(mem_w=1, cond=Cond.ALWAYS, next_addr=0)  # Mem[AR] <- ACC; -> FETCH

# ADD: ACC <- ACC + Mem[arg]
MROM[18] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[19] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[20] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, cond=Cond.ALWAYS,
                          next_addr=0)  # ADD: N, Z, ACC <- ACC + DR; -> FETCH

# ADDI: ACC <- ACC + arg
MROM[21] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.CR_ARG, cond=Cond.ALWAYS,
                          next_addr=0)  # ADDI: N, Z, ACC <- ACC + arg; -> FETCH

# SUB: ACC <- ACC - Mem[arg]
MROM[22] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[23] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[24] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.SUB, cond=Cond.ALWAYS,
                          next_addr=0)  # SUB: N, Z, ACC <- ACC - DR; -> FETCH

# SUBI: ACC <- ACC - arg
MROM[25] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.CR_ARG, alu=Alu.SUB,
                          cond=Cond.ALWAYS, next_addr=0)  # SUB: N, Z, ACC <- ACC - arg; -> FETCH

# MUL: ACC <- ACC * Mem[arg]
MROM[26] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[27] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[28] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.MUL, cond=Cond.ALWAYS,
                          next_addr=0)  # MUL: N, Z, ACC <- ACC * DR; -> FETCH

# DIV: ACC <- ACC / Mem[arg]
MROM[29] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[30] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[31] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.DIV, cond=Cond.ALWAYS,
                          next_addr=0)  # DIV: N, Z, ACC <- ACC // DR; -> FETCH

# REM: ACC <- ACC % Mem[arg]
MROM[32] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[33] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[34] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.REM, cond=Cond.ALWAYS,
                          next_addr=0)  # REM: N, Z, ACC <- ACC * DR; -> FETCH

# CMP: N,Z <- ACC - Mem[arg]
MROM[35] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)  # AR <- CR.arg
MROM[36] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[37] = encode_signals(flag_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.SUB, cond=Cond.ALWAYS,
                          next_addr=0)  # CMP: N,Z <- ACC - DR; -> FETCH

# NOT: ACC <- ~ACC
MROM[38] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu=Alu.NOT, cond=Cond.ALWAYS,
                          next_addr=0)  # ACC <- ~ACC; -> FETCH

# NEG: ACC <- -ACC
MROM[39] = encode_signals(acc_l=1, alu_left=AluLeft.ACC, alu=Alu.NOT)  # ACC <- ~ACC;
MROM[40] = encode_signals(flag_l=1, acc_l=1, alu_left=AluLeft.ACC, alu=Alu.INC, cond=Cond.ALWAYS,
                          next_addr=0)  # AC; -> FETCH

# JMP: IP <- arg
MROM[41] = encode_signals(ip_l=1, alu_right=AluRight.CR_ARG, cond=Cond.ALWAYS, next_addr=0)  # IP <- ARG; -> FETCH

# BEQ: IP <- arg if Z = 1
MROM[42] = encode_signals(cond=Cond.EQ, next_addr=41)
MROM[43] = encode_signals(cond=Cond.ALWAYS, next_addr=0)

# BNE: IP <- arg if Z = 0
MROM[44] = encode_signals(cond=Cond.NE, next_addr=41)
MROM[45] = encode_signals(cond=Cond.ALWAYS, next_addr=0)

# BGE: IP <- arg if N = 0
MROM[46] = encode_signals(cond=Cond.GE, next_addr=41)
MROM[47] = encode_signals(cond=Cond.ALWAYS, next_addr=0)

# BGT: IP <- arg if N = 0 && Z = 0
MROM[48] = encode_signals(cond=Cond.LT, next_addr=0)
MROM[49] = encode_signals(cond=Cond.EQ, next_addr=0)
MROM[50] = encode_signals(cond=Cond.ALWAYS, next_addr=41)

# BLE: IP <- arg if N = 1 || Z = 1
MROM[51] = encode_signals(cond=Cond.LT, next_addr=41)
MROM[52] = encode_signals(cond=Cond.EQ, next_addr=41)
MROM[53] = encode_signals(cond=Cond.ALWAYS, next_addr=0)

# BLT: IP < arg if N = 1
MROM[54] = encode_signals(cond=Cond.LT, next_addr=41)
MROM[55] = encode_signals(cond=Cond.ALWAYS, next_addr=0)

# PUSH: Mem[SP] <- ACC
MROM[56] = encode_signals(ar_l=1, ar_sel=ArSel.SP)  # AR <- SP
MROM[57] = encode_signals(mem_w=1, sp_l=1, alu_left=AluLeft.SP, alu=Alu.DEC, cond=Cond.ALWAYS,
                          next_addr=0)  # Mem[AR] <- ACC; SP <- SP - 1; -> FETCH

# POP: ACC <- Mem[++SP]
MROM[58] = encode_signals(sp_l=1, alu_left=AluLeft.SP, alu=Alu.INC)  # SP++
MROM[59] = encode_signals(ar_l=1, ar_sel=ArSel.SP)  # AR <- SP
MROM[60] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[61] = encode_signals(flag_l=1, acc_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS,
                          next_addr=0)  # ACC <- DR; -> FETCH

# CALL: Mem[SP] <- IP; SP--; IP <- CR.arg
MROM[62] = encode_signals(ar_l=1, ar_sel=ArSel.SP)  # AR <- SP
MROM[63] = encode_signals(mem_w=1, mem_src=MemSrc.IP,
                          sp_l=1, alu_left=AluLeft.SP, alu=Alu.DEC)  # Mem[AR] <- IP; SP--
MROM[64] = encode_signals(ip_l=1, alu_right=AluRight.CR_ARG, cond=Cond.ALWAYS, next_addr=0)  # IP <- CR.arg; -> FETCH

# RET: IP <- Mem[++SP]
MROM[65] = encode_signals(sp_l=1, alu_left=AluLeft.SP, alu=Alu.INC)  # SP++
MROM[66] = encode_signals(ar_l=1, ar_sel=ArSel.SP)  # AR <- SP
MROM[67] = encode_signals(dr_l=1)  # DR <- Mem[AR]
MROM[68] = encode_signals(ip_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS, next_addr=0)  # IP <- DR; -> FETCH

# HALT
MROM[69] = encode_signals(halted=1)

# DECODER[opcode] = адрес первого uop команды.
# Неизвестный опкод ведёт на 0 (FETCH) -- по сути пропуск.

DECODER = [0] * 256
DECODER[Opcode.LD] = 3
DECODER[Opcode.LDR] = 6
DECODER[Opcode.LDI] = 11
DECODER[Opcode.ST] = 12
DECODER[Opcode.STR] = 14
DECODER[Opcode.ADD] = 18
DECODER[Opcode.ADDI] = 21
DECODER[Opcode.SUB] = 22
DECODER[Opcode.SUBI] = 25
DECODER[Opcode.MUL] = 26
DECODER[Opcode.DIV] = 29
DECODER[Opcode.REM] = 32
DECODER[Opcode.CMP] = 35
DECODER[Opcode.NOT] = 38
DECODER[Opcode.NEG] = 39
DECODER[Opcode.JMP] = 41
DECODER[Opcode.BEQ] = 42
DECODER[Opcode.BNE] = 44
DECODER[Opcode.BGE] = 46
DECODER[Opcode.BGT] = 48
DECODER[Opcode.BLE] = 51
DECODER[Opcode.BLT] = 54
DECODER[Opcode.PUSH] = 56
DECODER[Opcode.POP] = 58
DECODER[Opcode.CALL] = 62
DECODER[Opcode.RET] = 65
DECODER[Opcode.HALT] = 69
