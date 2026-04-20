import re
import sys
from typing import NamedTuple


class Token(NamedTuple):
    type: str
    value: str


def tokenize(code: str) -> list[Token]:
    token_specification = [
        ('FLOAT_LIT', r'\d+\.\d+'),
        ('INT_LIT', r'\d+'),
        ('STRING_LIT', r'"(?:\\.|[^"\\])*"'),
        ('BOOL_LIT', r'\b(?:true|false)\b'),
        ('KEYWORD', r'\b(?:def|var|if|else|while|return|print|read|int|float|bool|string|void)\b'),
        ('ID', r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('OP', r':=|\|\||&&|==|!=|<=|>=|[+\-*/%<>=!]'),
        ('PUNCT', r'[(){},;]'),
        ('WS', r'\s+'),
        ('MISMATCH', r'.'),
    ]

    tok_regex = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in token_specification)
    get_token = re.compile(tok_regex).finditer

    tokens = []
    line_num = 1

    for mo in get_token(code):
        kind = mo.lastgroup
        value = mo.group()

        if kind == 'WS':
            if '\n' in value:
                line_num += value.count('\n')
            continue

        elif kind == 'MISMATCH':
            raise RuntimeError(f'Unexpected symbol {value!r} at line {line_num}')

        tokens.append(Token(kind, value))

    return tokens

if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        raw_text = f.read()
        tokenized_text = tokenize(raw_text)
        print("\n".join(str(token) for token in tokenize(tokenized_text)))