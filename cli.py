import pprint
import sys

from translator.parser import Parser
from translator.tokenizer import tokenize

if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        try:
            tokens = tokenize(f.read())
            parser = Parser(tokens)
            ast_tree = parser.parse()

            print("--- AST Tree ---")
            pprint.pprint(ast_tree)
        except Exception as e:
            print(f"Error: {e}")
