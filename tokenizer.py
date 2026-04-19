import re


def tokenize(code):
    lines = code.splitlines()
    no_comments = [re.sub(r"\\.*$", "", line) for line in lines]
    code_nc = "\n".join(no_comments)

    token_pattern = r""