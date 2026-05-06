from dataclasses import dataclass

from microcode import DECODER, MROM, Alu, AluLeft, AluRight, ArSel, Cond, MemSrc


def to_signed32(val):
    if val & (1 << 31):
        return val - (1 << 32)
    return val


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


class DataPath:
    MEM_SIZE = 2 ** 12
    OUTPUT_ADDR = MEM_SIZE - 1
    INPUT_ADDR = MEM_SIZE - 2

    def __init__(self, input_buffer):
        self.data_mem = [0] * self.MEM_SIZE

        self.input_buffer = input_buffer
        self.output_buffer = []

        self.MASK_32 = (1 << 32) - 1
        self.MASK_24 = (1 << 24) - 1
        self.BIT_31 = (1 << 31)

        self.acc = 0
        self.dr = 0
        self.ip = 0
        self.sp = (self.INPUT_ADDR - 1) & self.MASK_32
        self.ar = 0
        self.cr = 0

        self.Z = 0
        self.N = 0

    def read_memory(self):
        if self.ar == self.INPUT_ADDR:
            if self.input_buffer:
                return self.input_buffer.pop(0)
            else:
                raise Exception("Input buffer is empty")
        return self.data_mem[self.ar]

    def write_memory(self, value):
        if self.ar == self.OUTPUT_ADDR:
            self.output_buffer.append(value)
        else:
            self.data_mem[self.ar] = value


class ControlUnit:
    def __init__(self, input_buffer: list[int] | None =None):
        if input_buffer is None:
            input_buffer = []
        self.dp = DataPath(input_buffer)

        self.MROM = MROM
        self.mp = 0

        self.tick = 0
        self.halted = 0

    def snapshot(self) -> CpuState:
        return CpuState(
            tick=self.tick,
            mp=self.mp,
            cr=self.dp.cr,
            acc=self.dp.acc,
            ip=self.dp.ip,
            sp=self.dp.sp,
            ar=self.dp.ar,
            dr=self.dp.dr,
            Z=self.dp.Z,
            N=self.dp.N,
        )

    def step(self) -> None:
        self.tick += 1
        mc = self.MROM[self.mp]

        signals = self._decode_mc(mc)
        alu = self._execute_alu(signals)
        self._latch_registers(signals, alu)
        self._update_flags_and_branch(signals)

    def _decode_mc(self, mc):
        return {
            'halted': (mc >> 27) & 1,
            'flag_l': (mc >> 26) & 1,
            'acc_l': (mc >> 25) & 1,
            'dr_l': (mc >> 24) & 1,
            'sp_l': (mc >> 23) & 1,
            'ip_l': (mc >> 22) & 1,
            'cr_l': (mc >> 21) & 1,
            'ar_l': (mc >> 20) & 1,
            'mem_src': (mc >> 19) & 1,
            'mem_w': (mc >> 18) & 1,
            'ar_sel': (mc >> 16) & 0b11,
            'alu_left': (mc >> 14) & 0b11,
            'alu_right': (mc >> 12) & 0b11,
            'alu': (mc >> 9) & 0b111,
            'cond': (mc >> 6) & 0b111,
            'next_addr': mc & 0b111111
        }

    def _execute_alu(self, signals):
        dp = self.dp

        left = {AluLeft.ZERO: 0, AluLeft.ACC: dp.acc, AluLeft.SP: dp.sp}[signals['alu_left']]
        right = {AluRight.ZERO: 0, AluRight.CR_ARG: dp.cr & dp.MASK_24, AluRight.IP: dp.ip, AluRight.DR: dp.dr}[
            signals['alu_right']]

        alu_ops = {
            Alu.ADD: to_signed32(left + right) & dp.MASK_32,
            Alu.SUB: to_signed32(left - right) & dp.MASK_32,
            Alu.MUL: to_signed32(left * right) & dp.MASK_32,
            Alu.DIV: to_signed32(left // right) if right != 0 else 0 & dp.MASK_32,
            Alu.REM: to_signed32(left % right) if right != 0 else 0 & dp.MASK_32,
            Alu.INC: to_signed32(left + right + 1) & dp.MASK_32,
            Alu.DEC: to_signed32(left + right - 1) & dp.MASK_32,
            Alu.NOT: to_signed32(~(left + right)) & dp.MASK_32
        }

        result = alu_ops[signals['alu']]

        if signals['flag_l']:
            self.dp.N = 1 if (result & self.dp.BIT_31) else 0
            self.dp.Z = 1 if result == 0 else 0

        return result

    def _latch_registers(self, signals, alu_result):
        if signals['mem_w']:
            value = self.dp.ip if signals['mem_src'] == MemSrc.IP else self.dp.acc
            self.dp.write_memory(value)
        self._latch_ip(signals, alu_result)
        self._latch_dr(signals)
        self._latch_sp(signals, alu_result)
        self._latch_cr(signals, alu_result)
        self._latch_ar(signals)
        self._latch_acc(signals, alu_result)

    def _latch_acc(self, signals, alu_result):
        if not signals['acc_l']:
            return
        self.dp.acc = alu_result

    def _latch_dr(self, signals, ):
        if not signals['dr_l']:
            return
        self.dp.dr = self.dp.read_memory()

    def _latch_ip(self, signals, alu_result):
        if not signals['ip_l']:
            return
        self.dp.ip = alu_result

    def _latch_sp(self, signals, alu_result):
        if not signals['sp_l']:
            return
        self.dp.sp = alu_result

    def _latch_cr(self, signals, alu_result):
        if not signals['cr_l']:
            return
        self.dp.cr = alu_result

    def _latch_ar(self, signals):
        if not signals['ar_l']:
            return
        sources = {
            ArSel.IP: self.dp.ip,
            ArSel.CR_ARG: self.dp.cr & 0xFFFFFF,
            ArSel.SP: self.dp.sp,
            ArSel.DR: self.dp.dr,
        }
        self.dp.ar = sources[signals['ar_sel']]

    def _update_flags_and_branch(self, signals):
        cond = signals['cond']
        cond_true = (
                (cond == Cond.ALWAYS) or
                (cond == Cond.EQ and self.dp.Z == 1) or
                (cond == Cond.GE and self.dp.N == 0) or
                (cond == Cond.NE and self.dp.Z == 0) or
                (cond == Cond.LT and self.dp.N == 1)
        )

        if cond == Cond.DECODE:
            opcode = (self.dp.cr >> 24) & 0xFF
            self.mp = DECODER[opcode]
        else:
            self.mp = signals['next_addr'] if cond_true else (self.mp + 1) & 0x3F

        if signals['halted']:
            self.halted = True
