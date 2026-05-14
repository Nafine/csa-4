from collections import deque
from dataclasses import dataclass

from microcode import DECODER, MROM, ArSel, Cond, MemInAddress, PcSel

MASK_32 = (1 << 32) - 1
MASK_24 = (1 << 24) - 1
BIT_31 = 1 << 31


def to_signed32(val: int) -> int:
    if val & BIT_31:
        return val - (1 << 32)
    return val


def _predecode(mc: int) -> tuple[int, ...]:
    return (
        (mc >> 29) & 1,  # 0  halted
        (mc >> 28) & 1,  # 1  flag_l
        (mc >> 27) & 1,  # 2  acc_l
        (mc >> 26) & 1,  # 3  dr_l
        (mc >> 25) & 1,  # 4  sp_l
        (mc >> 24) & 1,  # 5  pc_l
        (mc >> 23) & 1,  # 6  cr_l
        (mc >> 22) & 1,  # 7  ar_l
        (mc >> 21) & 1,  # 8  mem_src (0 = ACC, 1 = PC)
        (mc >> 20) & 1,  # 9  mem_in_addr (0 = PC, 1 = AR)
        (mc >> 19) & 1,  # 10  mem_w
        (mc >> 17) & 0b11,  # 11 ar_sel
        (mc >> 16) & 1,  # 12 pc_sel
        (mc >> 14) & 0b11,  # 13 alu_left
        (mc >> 12) & 0b11,  # 14 alu_right
        (mc >> 9) & 0b111,  # 15 alu
        (mc >> 6) & 0b111,  # 16 cond
        mc & 0b111111,  # 17 next_addr
    )


# optimization costil' in order to finish prob1 not in 5 hours 😢
DECODED_MROM = tuple(_predecode(word) for word in MROM)


@dataclass(frozen=True)
class CpuState:
    tick: int
    mpc: int
    executed_mpc: int
    cr: int
    acc: int
    pc: int
    sp: int
    ar: int
    dr: int
    Z: int
    N: int


class DataPathException(Exception):
    pass


class DataPath:
    # another optimization costil' 🙏
    __slots__ = (
        'data_mem', 'input_buffer', 'output_buffer',
        'acc', 'dr', 'pc', 'sp', 'ar', 'cr', 'Z', 'N',
    )

    MEM_SIZE = 2 ** 24
    OUTPUT_ADDR = MEM_SIZE - 1
    INPUT_ADDR = MEM_SIZE - 2
    MASK_32 = MASK_32
    MASK_24 = MASK_24
    BIT_31 = BIT_31

    def __init__(self, input_buffer: list[int] | deque[int] | None) -> None:
        self.data_mem: list[int] = [0] * self.MEM_SIZE

        # and another one (pop in deque is o(1))
        if input_buffer is None:
            self.input_buffer: deque[int] = deque()
        elif isinstance(input_buffer, deque):
            self.input_buffer = input_buffer
        else:
            self.input_buffer = deque(input_buffer)
        self.output_buffer: list[int] = []

        self.acc = 0
        self.dr = 0
        self.pc = 0
        self.sp = (self.INPUT_ADDR - 1) & MASK_24
        self.ar = 0
        self.cr = 0

        self.Z = 0
        self.N = 0


class ControlUnit:
    # 🙏🙏🙏
    __slots__ = ('dp', 'mpc', 'executed_mpc', 'tick', 'halted')

    def __init__(self, input_buffer: list[int] | None = None):
        self.dp = DataPath(input_buffer)
        self.mpc = 0
        self.executed_mpc = 0
        self.tick = 0
        self.halted = False

    def snapshot(self) -> CpuState:
        dp = self.dp
        return CpuState(
            tick=self.tick,
            mpc=self.mpc,
            executed_mpc=self.executed_mpc,
            cr=dp.cr,
            acc=dp.acc,
            pc=dp.pc,
            sp=dp.sp,
            ar=dp.ar,
            dr=dp.dr,
            Z=dp.Z,
            N=dp.N,
        )

    def step(self) -> None:
        dp = self.dp
        mpc = self.mpc
        self.executed_mpc = mpc
        (halted, flag_l, acc_l, dr_l, sp_l, pc_l, cr_l, ar_l,
         mem_src, mem_in_addr, mem_w, ar_sel, pc_sel, alu_left, alu_right, alu, cond,
         next_addr) = DECODED_MROM[mpc]
        self.tick += 1

        decode_input = dp.dr
        z_old = dp.Z
        n_old = dp.N

        if alu_left == 0:
            left = 0
        elif alu_left == 1:
            left = dp.acc
        else:
            left = dp.sp

        if alu_right == 0:
            right = 0
        elif alu_right == 1:
            right = dp.cr & MASK_24
        elif alu_right == 2:
            right = dp.pc
        else:
            right = dp.dr

        if alu == 0:
            result = (left + right) & MASK_32
        elif alu == 1:
            result = (left - right) & MASK_32
        elif alu == 2:
            result = (left * right) & MASK_32
        elif alu == 3:
            result = ((left // right) & MASK_32) if right != 0 else 0
        elif alu == 4:
            result = ((left % right) & MASK_32) if right != 0 else 0
        elif alu == 5:
            result = (left + right + 1) & MASK_32
        elif alu == 6:
            result = (left + right - 1) & MASK_32
        else:
            result = (~(left + right)) & MASK_32

        if flag_l:
            dp.N = 1 if (result & BIT_31) else 0
            dp.Z = 1 if result == 0 else 0

        if mem_w:
            value = dp.pc if mem_src == 1 else dp.acc
            ar = dp.ar
            if ar == DataPath.OUTPUT_ADDR:
                dp.output_buffer.append(value)
            else:
                dp.data_mem[ar] = value

        if dr_l:
            ar = dp.ar
            if mem_in_addr == MemInAddress.AR and ar == DataPath.INPUT_ADDR:
                if dp.input_buffer:
                    dp.dr = dp.input_buffer.popleft() & MASK_32
                else:
                    raise DataPathException('input_buffer is empty')
            else:
                dp.dr = dp.data_mem[ar if mem_in_addr == MemInAddress.AR else dp.pc]
        if pc_l:
            dp.pc = result if pc_sel == PcSel.ALU & MASK_24 else dp.pc + 1
        if sp_l:
            dp.sp = result & MASK_24
        if cr_l:
            dp.cr = result
        if ar_l:
            if ar_sel == ArSel.CR_ARG:
                dp.ar = dp.cr & MASK_24
            elif ar_sel == ArSel.SP:
                dp.ar = dp.sp
            else:
                dp.ar = dp.dr & MASK_24
        if acc_l:
            dp.acc = result

        if cond == Cond.NONE:
            self.mpc = (mpc + 1) & 0x7F
        elif cond == Cond.ALWAYS:
            self.mpc = next_addr
        elif cond == Cond.EQ:
            self.mpc = next_addr if z_old == 1 else (mpc + 1) & 0x7F
        elif cond == Cond.GE:
            self.mpc = next_addr if n_old == 0 else (mpc + 1) & 0x7F
        elif cond == Cond.NE:
            self.mpc = next_addr if z_old == 0 else (mpc + 1) & 0x7F
        elif cond == Cond.LT:
            self.mpc = next_addr if n_old == 1 else (mpc + 1) & 0x7F
        elif cond == Cond.DECODE:
            self.mpc = DECODER[(decode_input >> 24) & 0xFF]

        if halted:
            self.halted = True
