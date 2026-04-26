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
        self.halted = 0


class ControlUnit:
    def __init__(self, data_path):
        self.data_path = data_path
        self.tick = 0

    def tick(self):
        self.tick += 1

    def current_tick(self):
        return self.tick

    def process_next_tick(self):
        pass