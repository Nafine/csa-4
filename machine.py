from collections import deque
from dataclasses import dataclass

from microcode import DECODER, MROM, Cond, MemInAddress, IpSel, ArSel

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
        (mc >> 24) & 1,  # 5  ip_l
        (mc >> 23) & 1,  # 6  cr_l
        (mc >> 22) & 1,  # 7  ar_l
        (mc >> 21) & 1,  # 8  mem_src (0 = ACC, 1 = IP)
        (mc >> 20) & 1,  # 9  mem_in_addr (0 = IP, 1 = AR)
        (mc >> 19) & 1,  # 10  mem_w
        (mc >> 17) & 0b11,  # 11 ar_sel
        (mc >> 16) & 1,  # 12 ip_sel
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
    mp: int
    cr: int
    acc: int
    ip: int
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
        'acc', 'dr', 'ip', 'sp', 'ar', 'cr', 'Z', 'N',
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
        self.ip = 0
        self.sp = (self.INPUT_ADDR - 1) & MASK_24
        self.ar = 0
        self.cr = 0

        self.Z = 0
        self.N = 0


class ControlUnit:
    # 🙏🙏🙏
    __slots__ = ('dp', 'mp', 'tick', 'halted')

    def __init__(self, input_buffer: list[int] | None = None):
        self.dp = DataPath(input_buffer)
        self.mp = 0
        self.tick = 0
        self.halted = False

    def snapshot(self) -> CpuState:
        dp = self.dp
        return CpuState(
            tick=self.tick,
            mp=self.mp,
            cr=dp.cr,
            acc=dp.acc,
            ip=dp.ip,
            sp=dp.sp,
            ar=dp.ar,
            dr=dp.dr,
            Z=dp.Z,
            N=dp.N,
        )

    def step(self) -> None:
        dp = self.dp
        mp = self.mp
        (halted, flag_l, acc_l, dr_l, sp_l, ip_l, cr_l, ar_l,
         mem_src, mem_in_addr, mem_w, ar_sel, ip_sel, alu_left, alu_right, alu, cond,
         next_addr) = DECODED_MROM[mp]
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
            right = dp.ip
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
            value = dp.ip if mem_src == 1 else dp.acc
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
                dp.dr = dp.data_mem[ar if mem_in_addr == MemInAddress.AR else dp.ip]
        if ip_l:
            dp.ip = result if ip_sel == IpSel.ALU & MASK_24 else dp.ip + 1
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
            self.mp = (mp + 1) & 0x7F
        elif cond == Cond.ALWAYS:
            self.mp = next_addr
        elif cond == Cond.EQ:
            self.mp = next_addr if z_old == 1 else (mp + 1) & 0x7F
        elif cond == Cond.GE:
            self.mp = next_addr if n_old == 0 else (mp + 1) & 0x7F
        elif cond == Cond.NE:
            self.mp = next_addr if z_old == 0 else (mp + 1) & 0x7F
        elif cond == Cond.LT:
            self.mp = next_addr if n_old == 1 else (mp + 1) & 0x7F
        elif cond == Cond.DECODE:
            print(f'decode: {decode_input >> 24}: {DECODER[(decode_input >> 24) & 0xFF]}')
            self.mp = DECODER[(decode_input >> 24) & 0xFF]

        if halted:
            self.halted = True
