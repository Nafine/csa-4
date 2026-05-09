from machine import ControlUnit, CpuState

TRACE_BATCH = 4096


def format_state(state: CpuState) -> str:
    return (
        f'Tick: [{state.tick}] uPC={state.mp:02} CR={state.cr:08x}\n'
        f'ACC={state.acc:11} IP={state.ip:08x} SP={state.sp:08x}\n'
        f'AR={state.ar:08x} DR={state.dr:08x} Z={state.Z} N={state.N}\n'
        '-----------------------------\n'
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
