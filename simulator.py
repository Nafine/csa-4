from machine import ControlUnit, CpuState
from microcode import MROM_DESC, MROM_LABEL

TRACE_BATCH = 4096


def format_state(state: CpuState) -> str:
    return (
        f'Tick: [{state.tick}] mPC={state.mpc:02} CR={state.cr:08x} ACC={state.acc:11} PC={state.pc:08x} SP={state.sp:08x} AR={state.ar:08x} DR={state.dr:08x} Z={state.Z} N={state.N}\n'  # noqa: E501
    )


def format_microcode(state: CpuState) -> str:
    return (
        f'Tick: [{state.tick}] {MROM_LABEL[state.executed_mpc]:<5} '
        f'mPC={state.executed_mpc:02} {MROM_DESC[state.executed_mpc]}\n'
    )


class Simulator:
    def __init__(self, cu: ControlUnit, trace_path: str | None = None):
        self.cu = cu
        self.trace_path = trace_path

    def run(self) -> None:
        cu = self.cu
        step = cu.step

        if self.trace_path is None:
            while not cu.halted:
                step()
            return

        snapshot = cu.snapshot
        with open(self.trace_path, 'w', encoding='utf-8') as trace:
            buf: list[str] = []
            append = buf.append
            while not cu.halted:
                step()
                append(format_state(snapshot()))
                if len(buf) >= TRACE_BATCH:
                    trace.write(''.join(buf))
                    buf.clear()
            if buf:
                trace.write(''.join(buf))
