import argparse
import sys
from typing import AnyStr

from isa import Instruction, read_file, write_file
from machine import ControlUnit
from translator.codegen import CodeGenerator
from translator.parser import Parser
from translator.tokenizer import tokenize


def compile_source(source: AnyStr) -> tuple[list[Instruction], list[int]]:
    tokens = tokenize(source)
    ast_tree = Parser(tokens).parse()
    generator = CodeGenerator()
    return generator.generate(ast_tree)


def compile_file(input_file: str, output_file: str) -> None:
    with open(input_file) as f:
        instructions, data = compile_source(f.read())
    write_file(output_file, instructions, data)


def run_file(machine_file: str, trace_file: str) -> None:
    data = read_file(machine_file)

    cu = ControlUnit(log_path=trace_file)
    for index, value in enumerate(data):
        cu.dp.data_mem[index] = value

    cu.run()
    print(cu.dp.output_buffer)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog='csa')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_compile = sub.add_parser('compile', help='compile source into a binary')
    p_compile.add_argument('input_file')
    p_compile.add_argument('output_file')

    p_run = sub.add_parser('run', help='run a compiled binary')
    p_run.add_argument('machine_file')
    p_run.add_argument('trace_file')

    args = parser.parse_args(argv)

    if args.cmd == 'compile':
        compile_file(args.input_file, args.output_file)
    elif args.cmd == 'run':
        run_file(args.machine_file, args.trace_file)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)
