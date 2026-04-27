from microcode import UOPS


def to_signed32(val):
    if val & (1 << 31):
        return val - (1 << 32)
    return val


class DataPath:
    def __init__(self, mem_size: int, input_buffer):
        self.data_mem = [0] * mem_size

        self.input_buffer = input_buffer
        self.output_buffer = []

        self.acc = 0
        self.ip = 0
        self.sp = mem_size - 1
        self.ar = 0
        self.cr = 0

        self.MASK_32 = (1 << 32) - 1
        self.BIT_31 = (1 << 31)

        self.Z = 0
        self.N = 0

    def read_memory(self):
        if self.ar == 0x80:
            if self.input_buffer:
                return self.input_buffer.pop(0)
            else:
                raise Exception("Input buffer is empty")
        return self.data_mem[self.ar]

    def write_memory(self):
        if self.ar == 0x84:
            self.output_buffer.append(self.acc)
        else:
            self.data_mem[self.ar] = self.acc


class ControlUnit:
    def __init__(self, log_path="trace.log", input_buffer=None):
        if input_buffer is None:
            input_buffer = []
        self.dp = DataPath(2048, input_buffer)

        self.UOPS = UOPS
        self.uPC = 0
        self.last_uPC = 0

        self.tick = 0
        self.halted = 0

        self.log = open(log_path, 'w', encoding='utf-8')

    def tick(self):
        self.tick += 1

    def current_tick(self):
        return self.tick

    def step(self):
        mc = self.UOPS[self.uPC]

        signals = self._decode_mc(mc)
        #print(signals)
        alu = self._execute_alu(signals)
        self._latch_registers(signals, alu)
        self._update_flags_and_branch(signals)

    def _decode_mc(self, mc):
        return {
            'halted': (mc >> 25) & 1,
            'acc_l': (mc >> 24) & 1,
            'sp_l': (mc >> 23) & 1,
            'ip_l': (mc >> 22) & 1,
            'cr_l': (mc >> 21) & 1,
            'ar_l': (mc >> 20) & 1,
            'mem_w': (mc >> 19) & 1,
            'ar_sel': (mc >> 17) & 0b11,
            'ip_sel': (mc >> 16) & 1,
            'alu_left': (mc >> 14) & 0b11,
            'alu_right': (mc >> 12) & 0b11,
            'alu': (mc >> 9) & 0b111,
            'cond': (mc >> 6) & 0b111,
            'next_addr': mc & 0b111111
        }

    def _execute_alu(self, signals):
        dp = self.dp

        left = {0: 0, 1: dp.acc, 2: dp.sp}[signals['alu_left']]
        right = {0: 0, 1: dp.cr, 2: dp.ip, 3: dp.read_memory()}[signals['alu_right']]

        alu_ops = {
            0: to_signed32(left + right) & dp.MASK_32,
            1: to_signed32(left - right) & dp.MASK_32,
            2: to_signed32(left * right) & dp.MASK_32,
            3: to_signed32(left // right) if right != 0 else 0 & dp.MASK_32,
            4: to_signed32(left + right + 1) & dp.MASK_32,
            5: to_signed32(left + right - 1) & dp.MASK_32,
        }

        return alu_ops[signals['alu']]

    def _latch_registers(self, signals, alu_result):
        if signals['mem_w']:
            self.dp.write_memory()
        self._latch_acc(signals, alu_result)
        self._latch_ip(signals, alu_result)
        self._latch_sp(signals, alu_result)
        self._latch_cr(signals, alu_result)
        self._latch_ar(signals, alu_result)

    def _latch_acc(self, signals, alu_result):
        if not signals['acc_l']:
            return
        self.dp.acc = alu_result
        self.dp.N = 1 if (alu_result & self.dp.BIT_31) else 0
        self.dp.Z = 1 if alu_result == 0 else 0

    def _latch_ip(self, signals, alu_result):
        if not signals['ip_l']:
            return
        self.dp.ip = alu_result if signals['ip_sel'] == 0 else 0

    def _latch_sp(self, signals, alu_result):
        if not signals['sp_l']:
            return
        self.dp.sp = alu_result

    def _latch_cr(self, signals, alu_result):
        if not signals['cr_l']:
            return
        self.dp.cr = alu_result

    def _latch_ar(self, signals, alu_result):
        if not signals['ar_l']:
            return
        sources = {
            0b00: self.dp.ip,
            0b01: self.dp.cr & 0xFFFFFF,
            0b10: self.dp.acc & 0xFFFFFF,
        }
        self.dp.ar = sources[signals['ar_sel']]

    def _update_flags_and_branch(self, signals):
        cond = signals['cond']
        cond_true = (
                (cond == 0b001) or
                (cond == 0b010 and self.dp.Z == 1) or
                (cond == 0b011 and self.dp.N == 0 and self.dp.Z != 0) or
                (cond == 0b100 and self.dp.Z == 0) or
                (cond == 0b101 and self.dp.N == 0 and self.dp.Z != 0)
        )

        self.tick += 1
        self.print_state()

        self.last_uPC = self.uPC
        self.uPC = signals['next_addr'] if cond_true else (self.uPC + 1) & 0x3F

        if signals['halted']:
            self.halted = True

        if self.uPC == 0 and not self.halted and self.last_uPC != 0:
            self.step()

    def print_state(self):
        self.log.write(f'Tick: [{self.tick}] uPC={self.uPC:02} CR={self.dp.cr:08x}\n')
        self.log.write(f'ACC={self.dp.acc:11} IP={self.dp.ip:08x} SP={self.dp.sp:08x}\n')
        self.log.write(f'AR={self.dp.ar:08x} Z={self.dp.Z} N={self.dp.N}\n')
        self.log.write('-----------------------------\n')


def _dump(label, cu):
    print(f'[{label}] tick={cu.tick} uPC={cu.uPC} '
          f'IP={cu.dp.ip:#x} AR={cu.dp.ar:#x} '
          f'CR={cu.dp.cr:#010x} ACC={cu.dp.acc} '
          f'Z={cu.dp.Z} N={cu.dp.N}')


def _run_checks(label, checks):
    print(f'-- {label} --')
    ok = True
    for name, got, want in checks:
        status = 'OK' if got == want else 'FAIL'
        if got != want:
            ok = False
        print(f'  {status}: {name}={got:#x}, ожидалось {want:#x}')
    return ok


if __name__ == '__main__':
    # === FETCH ===
    cu = ControlUnit()
    cu.dp.data_mem[0] = 0xDEADBEEF
    cu.dp.ip = 0
    cu.dp.ar = 0  # FETCH в текущей реализации не грузит AR - выставляем вручную

    _dump('init', cu)
    cu.step()
    _dump('after fetch', cu)
    cu.step()
    _dump('after inc', cu)

    _run_checks('FETCH', [
        ('CR', cu.dp.cr, 0xDEADBEEF),
        ('IP', cu.dp.ip, 1),
        ('AR', cu.dp.ar, 0),
    ])
    cu.log.close()

    # === LOAD: LD 0x10 ===
    cu = ControlUnit(log_path='trace_load.log')
    cu.dp.data_mem[0] = 0x01000010   # opcode LD (0x01), operand 0x10
    cu.dp.data_mem[0x10] = 0xCAFE
    cu.dp.ip = 0
    cu.dp.ar = 0

    _dump('LOAD init', cu)
    for _ in range(4):  # FETCH x2 + LOAD x2
        cu.step()
    _dump('LOAD done', cu)

    _run_checks('LOAD', [
        ('ACC', cu.dp.acc, 0xCAFE),
        ('AR',  cu.dp.ar,  0x10),
        ('uPC', cu.uPC,    0),     # вернулись к FETCH
    ])
    cu.log.close()

    # === STORE: ST 0x20 ===
    cu = ControlUnit(log_path='trace_store.log')
    cu.dp.data_mem[0] = 0x03000020   # opcode ST (0x03), operand 0x20
    cu.dp.acc = 0xBEEF
    cu.dp.ip = 0
    cu.dp.ar = 0

    _dump('STORE init', cu)
    cu.step(); cu.step()             # FETCH
    cu.uPC = 4                       # декодера опкодов нет - прыгаем в STORE вручную
    cu.step(); cu.step()             # STORE
    _dump('STORE done', cu)

    _run_checks('STORE', [
        ('Mem[0x20]', cu.dp.data_mem[0x20], 0xBEEF),
        ('AR',        cu.dp.ar,             0x20),
        ('uPC',       cu.uPC,               0),
    ])
    cu.log.close()
