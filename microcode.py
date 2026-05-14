from enum import IntEnum

from isa import Opcode


class ArSel(IntEnum):
    CR_ARG = 0b00
    SP = 0b01
    DR = 0b10


class PcSel(IntEnum):
    NEXT = 0
    ALU = 1


class AluLeft(IntEnum):
    ZERO = 0
    ACC = 1
    SP = 2


class AluRight(IntEnum):
    ZERO = 0
    CR_ARG = 1
    PC = 2
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
    DECODE = 0b111  # MPC <- DECODER[CR.opcode]


class MemSrc(IntEnum):
    ACC = 0
    PC = 1


class MemInAddress(IntEnum):
    PC = 0
    AR = 1


def encode_signals(
        halted: int = 0,
        flag_l: int = 0, acc_l: int = 0, dr_l: int = 0, sp_l: int = 0,
        pc_l: int = 0, cr_l: int = 0, ar_l: int = 0, mem_w: int = 0,
        mem_src: MemSrc = MemSrc.ACC, mem_in_addr: MemInAddress = MemInAddress.PC,
        ar_sel: ArSel = ArSel.CR_ARG, pc_sel: PcSel = PcSel.NEXT,
        alu_left: AluLeft = AluLeft.ZERO, alu_right: AluRight = AluRight.ZERO,
        alu: Alu = Alu.ADD, cond: Cond = Cond.NONE, next_addr: int = 0,
) -> int:
    return (
            (halted & 1) << 29 |
            (flag_l & 1) << 28 |
            (acc_l & 1) << 27 |
            (dr_l & 1) << 26 |
            (sp_l & 1) << 25 |
            (pc_l & 1) << 24 |
            (cr_l & 1) << 23 |
            (ar_l & 1) << 22 |
            (mem_src & 1) << 21 |
            (mem_in_addr & 1) << 20 |
            (mem_w & 1) << 19 |
            (int(ar_sel) & 0b11) << 17 |
            (pc_sel & 1) << 16 |
            (int(alu_left) & 0b11) << 14 |
            (int(alu_right) & 0b11) << 12 |
            (int(alu) & 0b111) << 9 |
            (int(cond) & 0b111) << 6 |
            (next_addr & 0b111111)
    )


MROM = [0] * 128
MROM_DESC: list[str] = [''] * 128

MROM[0] = encode_signals(dr_l=1, pc_l=1)
MROM_DESC[0] = 'DR <- Mem[PC]; PC <- PC + 1'

# FETCH
MROM[1] = encode_signals(cr_l=1, alu_right=AluRight.DR, cond=Cond.DECODE)
MROM_DESC[1] = 'CR <- DR; -> DECODER[opcode]'

# LOAD: ACC <- Mem[arg]
MROM[2] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[2] = 'AR <- CR.arg'
MROM[3] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[3] = 'DR <- Mem[AR]'
MROM[4] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS,
                         next_addr=1)
MROM_DESC[4] = 'DR <- Mem[PC]; PC <- PC + 1; ACC <- DR; -> FETCH'

# LDR: ACC <- Mem[Mem[arg]]
MROM[5] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[5] = 'AR <- CR.arg'
MROM[6] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[6] = 'DR <- Mem[AR]'
MROM[7] = encode_signals(ar_l=1, ar_sel=ArSel.DR)
MROM_DESC[7] = 'AR <- DR'
MROM[8] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[8] = 'DR <- Mem[AR]'
MROM[9] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS,
                         next_addr=1)
MROM_DESC[9] = 'DR <- Mem[PC]; PC <- PC + 1; ACC <- DR; -> FETCH'

# LOAD IMM: ACC <- CR.arg
MROM[10] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_right=AluRight.CR_ARG, cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[10] = 'DR <- Mem[PC]; PC <- PC + 1; ACC <- CR.arg; -> FETCH'

# STORE: Mem[arg] <- ACC
MROM[11] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[11] = 'AR <- CR.arg'
MROM[12] = encode_signals(mem_w=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[12] = 'Mem[AR] <- ACC'
MROM[13] = encode_signals(dr_l=1, pc_l=1, cond=Cond.ALWAYS, next_addr=1)
MROM_DESC[13] = 'DR <- Mem[PC]; PC <- PC + 1; -> FETCH'

# STR: Mem[Mem[arg]] <- ACC
MROM[14] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[14] = 'AR <- CR.arg'
MROM[15] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[15] = 'DR <- Mem[AR]'
MROM[16] = encode_signals(ar_l=1, ar_sel=ArSel.DR)
MROM_DESC[16] = 'AR <- DR'
MROM[17] = encode_signals(mem_w=1, dr_l=1, pc_l=1, cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[17] = 'DR <- Mem[PC]; PC <- PC + 1; Mem[AR] <- ACC; -> FETCH'

# ADD: ACC <- ACC + Mem[arg]
MROM[18] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[18] = 'AR <- CR.arg'
MROM[19] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[19] = 'DR <- Mem[AR]'
MROM[20] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[20] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC + DR; -> FETCH'

# ADDI: ACC <- ACC + arg
MROM[21] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.CR_ARG,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[21] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC + arg; -> FETCH'

# SUB: ACC <- ACC - Mem[arg]
MROM[22] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[22] = 'AR <- CR.arg'
MROM[23] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[23] = 'DR <- Mem[AR]'
MROM[24] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.SUB,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[24] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC - DR; -> FETCH'

# SUBI: ACC <- ACC - arg
MROM[25] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.CR_ARG,
                          alu=Alu.SUB,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[25] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC - arg; -> FETCH'

# MUL: ACC <- ACC * Mem[arg]
MROM[26] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[26] = 'AR <- CR.arg'
MROM[27] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[27] = 'DR <- Mem[AR]'
MROM[28] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.MUL,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[28] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC * DR; -> FETCH'

# MULI: ACC <- ACC * arg
MROM[29] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.CR_ARG,
                          alu=Alu.MUL,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[29] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC * arg; -> FETCH'

# DIV: ACC <- ACC / Mem[arg]
MROM[30] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[30] = 'AR <- CR.arg'
MROM[31] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[31] = 'DR <- Mem[AR]'
MROM[32] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.DIV,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[32] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC // DR; -> FETCH'

# DIVI: ACC <- ACC / arg
MROM[33] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.CR_ARG,
                          alu=Alu.DIV,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[33] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC // arg; -> FETCH'

# REM: ACC <- ACC % Mem[arg]
MROM[34] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[34] = 'AR <- CR.arg'
MROM[35] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[35] = 'DR <- Mem[AR]'
MROM[36] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.REM,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[36] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC % DR; -> FETCH'

# REMI: ACC <- ACC % arg
MROM[37] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.CR_ARG,
                          alu=Alu.REM,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[37] = 'DR <- Mem[PC]; PC <- PC + 1; N, Z, ACC <- ACC % arg; -> FETCH'

# CMP: N,Z <- ACC - Mem[arg]
MROM[38] = encode_signals(ar_l=1, ar_sel=ArSel.CR_ARG)
MROM_DESC[38] = 'AR <- CR.arg'
MROM[39] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[39] = 'DR <- Mem[AR]'
MROM[40] = encode_signals(flag_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.DR, alu=Alu.SUB,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[40] = 'DR <- Mem[PC]; PC <- PC + 1; N,Z <- ACC - DR; -> FETCH'

# CMPI: N,Z <- ACC - arg
MROM[41] = encode_signals(flag_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu_right=AluRight.CR_ARG, alu=Alu.SUB,
                          cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[41] = 'DR <- Mem[PC]; PC <- PC + 1; N,Z <- ACC - arg; -> FETCH'

# NOT: ACC <- ~ACC
MROM[42] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu=Alu.NOT, cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[42] = 'DR <- Mem[PC]; PC <- PC + 1; ACC <- ~ACC; -> FETCH'

# NEG: ACC <- -ACC
MROM[43] = encode_signals(acc_l=1, alu_left=AluLeft.ACC, alu=Alu.NOT)
MROM_DESC[43] = 'ACC <- ~ACC'
MROM[44] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_left=AluLeft.ACC, alu=Alu.INC, cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[44] = 'DR <- Mem[PC]; PC <- PC + 1; ACC <- ACC + 1; -> FETCH'

# JMP: PC <- arg
MROM[45] = encode_signals(pc_l=1, pc_sel=PcSel.ALU, alu_right=AluRight.CR_ARG, cond=Cond.ALWAYS,
                          next_addr=0)
MROM_DESC[45] = 'PC <- CR.arg; -> FETCH'

# BEQ: PC <- arg if Z = 1
MROM[46] = encode_signals(cond=Cond.EQ, next_addr=45)
MROM_DESC[46] = 'if Z = 1 -> JMP'
MROM[47] = encode_signals(cond=Cond.ALWAYS, next_addr=0)
MROM_DESC[47] = '-> FETCH'

# BNE: PC <- arg if Z = 0
MROM[48] = encode_signals(cond=Cond.NE, next_addr=45)
MROM_DESC[48] = 'if Z = 0 -> JMP'
MROM[49] = encode_signals(cond=Cond.ALWAYS, next_addr=0)
MROM_DESC[49] = '-> FETCH'

# BGE: PC <- arg if N = 0
MROM[50] = encode_signals(cond=Cond.GE, next_addr=45)
MROM_DESC[50] = 'if N = 0 -> JMP'
MROM[51] = encode_signals(cond=Cond.ALWAYS, next_addr=0)
MROM_DESC[51] = '-> FETCH'

# BGT: PC <- arg if N = 0 && Z = 0
MROM[52] = encode_signals(cond=Cond.LT, next_addr=0)
MROM_DESC[52] = 'if N = 1 -> FETCH'
MROM[53] = encode_signals(cond=Cond.EQ, next_addr=0)
MROM_DESC[53] = 'if Z = 1 -> FETCH'
MROM[54] = encode_signals(cond=Cond.ALWAYS, next_addr=45)
MROM_DESC[54] = '-> JMP'

# BLE: PC <- arg if N = 1 || Z = 1
MROM[55] = encode_signals(cond=Cond.LT, next_addr=45)
MROM_DESC[55] = 'if N = 1 -> JMP'
MROM[56] = encode_signals(cond=Cond.EQ, next_addr=45)
MROM_DESC[56] = 'if Z = 1 -> JMP'
MROM[57] = encode_signals(cond=Cond.ALWAYS, next_addr=0)
MROM_DESC[57] = '-> FETCH'

# BLT: PC < arg if N = 1
MROM[58] = encode_signals(cond=Cond.LT, next_addr=45)
MROM_DESC[58] = 'if N = 1 -> JMP'
MROM[59] = encode_signals(cond=Cond.ALWAYS, next_addr=0)
MROM_DESC[59] = '-> FETCH'

# PUSH: Mem[SP] <- ACC
MROM[60] = encode_signals(ar_l=1, ar_sel=ArSel.SP)
MROM_DESC[60] = 'AR <- SP'
MROM[61] = encode_signals(mem_w=1, sp_l=1, mem_in_addr=MemInAddress.AR, alu_left=AluLeft.SP,
                          alu=Alu.DEC)
MROM_DESC[61] = 'Mem[AR] <- ACC; SP <- SP - 1'
MROM[62] = encode_signals(dr_l=1, pc_l=1, cond=Cond.ALWAYS, next_addr=1)
MROM_DESC[62] = 'DR <- Mem[PC]; PC <- PC + 1; -> FETCH'

# POP: ACC <- Mem[++SP]
MROM[63] = encode_signals(sp_l=1, alu_left=AluLeft.SP, alu=Alu.INC)
MROM_DESC[63] = 'SP <- SP + 1'
MROM[64] = encode_signals(ar_l=1, ar_sel=ArSel.SP)
MROM_DESC[64] = 'AR <- SP'
MROM[65] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[65] = 'DR <- Mem[AR]'
MROM[66] = encode_signals(flag_l=1, acc_l=1, dr_l=1, pc_l=1, alu_right=AluRight.DR, cond=Cond.ALWAYS,
                          next_addr=1)
MROM_DESC[66] = 'DR <- Mem[PC]; PC <- PC + 1; ACC <- DR; -> FETCH'

# CALL: Mem[SP] <- PC; SP--; PC <- CR.arg
MROM[67] = encode_signals(ar_l=1, ar_sel=ArSel.SP)
MROM_DESC[67] = 'AR <- SP'
MROM[68] = encode_signals(mem_w=1, mem_src=MemSrc.PC,
                          sp_l=1, alu_left=AluLeft.SP, alu=Alu.DEC)
MROM_DESC[68] = 'Mem[AR] <- PC; SP <- SP - 1'
MROM[69] = encode_signals(pc_l=1, pc_sel=PcSel.ALU, alu_right=AluRight.CR_ARG, cond=Cond.ALWAYS,
                          next_addr=0)
MROM_DESC[69] = 'PC <- CR.arg; -> FETCH'

# RET: PC <- Mem[++SP]
MROM[70] = encode_signals(sp_l=1, alu_left=AluLeft.SP, alu=Alu.INC)
MROM_DESC[70] = 'SP <- SP + 1'
MROM[71] = encode_signals(ar_l=1, ar_sel=ArSel.SP)
MROM_DESC[71] = 'AR <- SP'
MROM[72] = encode_signals(dr_l=1, mem_in_addr=MemInAddress.AR)
MROM_DESC[72] = 'DR <- Mem[AR]'
MROM[73] = encode_signals(pc_l=1, pc_sel=PcSel.ALU, alu_right=AluRight.DR, cond=Cond.ALWAYS,
                          next_addr=0)
MROM_DESC[73] = 'PC <- DR; -> FETCH'

# HALT
MROM[74] = encode_signals(halted=1)
MROM_DESC[74] = 'HALT'

# DECODER[opcode] = адрес первого uop команды.
# Неизвестный опкод ведёт на 0 (FETCH) -- по сути пропуск.

DECODER = [0] * 256
DECODER[Opcode.LD] = 2
DECODER[Opcode.LDR] = 5
DECODER[Opcode.LDI] = 10
DECODER[Opcode.ST] = 11
DECODER[Opcode.STR] = 14
DECODER[Opcode.ADD] = 18
DECODER[Opcode.ADDI] = 21
DECODER[Opcode.SUB] = 22
DECODER[Opcode.SUBI] = 25
DECODER[Opcode.MUL] = 26
DECODER[Opcode.MULI] = 29
DECODER[Opcode.DIV] = 30
DECODER[Opcode.DIVI] = 33
DECODER[Opcode.REM] = 34
DECODER[Opcode.REMI] = 37
DECODER[Opcode.CMP] = 38
DECODER[Opcode.CMPI] = 41
DECODER[Opcode.NOT] = 42
DECODER[Opcode.NEG] = 43
DECODER[Opcode.JMP] = 45
DECODER[Opcode.BEQ] = 46
DECODER[Opcode.BNE] = 48
DECODER[Opcode.BGE] = 50
DECODER[Opcode.BGT] = 52
DECODER[Opcode.BLE] = 55
DECODER[Opcode.BLT] = 58
DECODER[Opcode.PUSH] = 60
DECODER[Opcode.POP] = 63
DECODER[Opcode.CALL] = 67
DECODER[Opcode.RET] = 70
DECODER[Opcode.HALT] = 74

# MROM_LABEL[mpc] = к какой команде относится микрокоманда.
# Адреса 0..1 -- это общий цикл FETCH, не часть конкретной инструкции.
MROM_LABEL: list[str] = ['FETCH'] * 128
_starts = sorted((DECODER[op], op.name) for op in Opcode)
for _idx, (_start, _name) in enumerate(_starts):
    _end = _starts[_idx + 1][0] if _idx + 1 < len(_starts) else 128
    for _addr in range(_start, _end):
        MROM_LABEL[_addr] = _name
