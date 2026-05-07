import argparse
import sys
import time

from isa import Instruction, read_file, write_debug, write_file
from machine import ControlUnit, DataPath
from simulator import Simulator
from translator.codegen import CodeGenerator
from translator.parser import Parser
from translator.tokenizer import tokenize


def compile_source(source: str) -> tuple[list[Instruction], list[int]]:
    tokens = tokenize(source)
    ast_tree = Parser(tokens).parse()
    # pprint(ast_tree)
    generator = CodeGenerator()
    return generator.generate(ast_tree)


def compile_file(input_file: str, output_file: str) -> None:
    with open(input_file) as f:
        instructions, data = compile_source(f.read())
    write_file(output_file, instructions, data)
    write_debug(output_file + '.txt', instructions, data)


def file_to_buf(path: str) -> list[int]:
    words: list[int] = []

    with open(path, 'rb') as f:
        while byte_chunk := f.read(1):
            byte_chunk = byte_chunk.ljust(4, b'\x00')

            word = int.from_bytes(byte_chunk, byteorder='little')
            words.append(word)

    return words

def buf_to_str(buf: list[int]) -> str:
    eof = (-1) & DataPath.MASK_32
    out = []
    for char in buf:
        if char == eof:
            break
        out.append(chr(char))
    return ''.join(out)

def run_file(machine_file: str, input_file: str | None = None, trace_file: str | None = None) -> None:
    data = read_file(machine_file)

    input_buffer = file_to_buf(input_file) if input_file else None

    cu = ControlUnit(input_buffer)
    for index, value in enumerate(data):
        cu.dp.data_mem[index] = value

    begin_time = time.time_ns()
    Simulator(cu, trace_file).run()
    end_time = time.time_ns()
    print(f'Time in ms: {(end_time - begin_time) // 1_000_000}')
    print(buf_to_str(cu.dp.output_buffer))


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog='csa')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_compile = sub.add_parser('compile', help='compile source into a binary')
    p_compile.add_argument('input_file')
    p_compile.add_argument('output_file')

    p_run = sub.add_parser('run', help='run a compiled binary')
    p_run.add_argument('machine_file')
    p_run.add_argument('input_file', nargs='?', default=None)
    p_run.add_argument('trace_file', nargs='?', default=None)
    args = parser.parse_args(argv)

    if args.cmd == 'compile':
        compile_file(args.input_file, args.output_file)
    elif args.cmd == 'run':
        run_file(args.machine_file, args.input_file, args.trace_file)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)
