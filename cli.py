import sys

from machine import ControlUnit
from translator.codegen import CodeGenerator
from translator.parser import Parser
from translator.tokenizer import tokenize

if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        try:
            tokens = tokenize(f.read())
            ast_tree = Parser(tokens).parse()
            generator = CodeGenerator()
            instructions, data = generator.generate(ast_tree)

            cu = ControlUnit()
            for index, instr in enumerate(instructions):
                cu.dp.data_mem[index] = instr.to_binary()
            data_base = len(instructions)
            for offset, value in enumerate(data):
                cu.dp.data_mem[data_base + offset] = value

            cu.run()
            print(''.join([str(_) for _ in cu.dp.output_buffer]))
            print(f'ticks: {cu.current_tick()}')

            # print("--- AST Tree ---")
            # pprint.pprint(ast_tree)
        except Exception as e:
            print(f"Error: {e}")
