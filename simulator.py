from machine import ControlUnit, CpuState


def format_state(state: CpuState) -> str:
    return (
        f'Tick: [{state.tick}] uPC={state.mp:02} CR={state.cr:08x}\n'
        f'ACC={state.acc:11} IP={state.ip:08x} SP={state.sp:08x}\n'
        f'AR={state.ar:08x} Z={state.Z} N={state.N}\n'
        '-----------------------------\n'
    )


class Simulator:
    def __init__(self, cu: ControlUnit, trace_path: str | None = None):
        self.cu = cu
        self.trace_path = trace_path

    def run(self) -> None:
        if self.trace_path is None:
            while not self.cu.halted:
                self.cu.step()
            return
        with open(self.trace_path, 'w', encoding='utf-8') as trace:
            while not self.cu.halted:
                self.cu.step()
                trace.write(format_state(self.cu.snapshot()))
