import pytest

from translator.tokenizer import Token, tokenize


def _types(tokens):
    return [t.type for t in tokens]


def _values(tokens):
    return [t.value for t in tokens]


def test_int_literal():
    assert tokenize('42') == [Token('INT_LIT', '42')]


@pytest.mark.xfail(reason="tokenizer has no FLOAT_LIT rule yet")
def test_float_literal():
    assert tokenize('3.14') == [Token('FLOAT_LIT', '3.14')]


def test_string_literal():
    assert tokenize('"hello"') == [Token('STRING_LIT', '"hello"')]


def test_string_with_escape():
    assert tokenize(r'"a\"b"') == [Token('STRING_LIT', r'"a\"b"')]


def test_bool_literals():
    assert tokenize('true false') == [
        Token('BOOL_LIT', 'true'),
        Token('BOOL_LIT', 'false'),
    ]


def test_keywords():
    src = 'def var if else while return print read int float bool string void'
    toks = tokenize(src)
    assert all(t.type == 'KEYWORD' for t in toks), _types(toks)
    assert _values(toks) == src.split()


def test_identifier():
    toks = tokenize('myVar_1 _x x123')
    assert _types(toks) == ['ID', 'ID', 'ID']
    assert _values(toks) == ['myVar_1', '_x', 'x123']


def test_operators():
    src = ':= || && == != <= >= + - * / % < > = !'
    toks = tokenize(src)
    assert all(t.type == 'OP' for t in toks), _types(toks)
    assert _values(toks) == src.split()


def test_punctuation():
    toks = tokenize('(){},;')
    assert _types(toks) == ['PUNCT'] * 6
    assert _values(toks) == ['(', ')', '{', '}', ',', ';']


def test_whitespace_skipped():
    toks = tokenize('  a   \n\t b  ')
    assert _values(toks) == ['a', 'b']


def test_mismatch_raises():
    with pytest.raises(RuntimeError, match='@'):
        tokenize('a @ b')


def test_short_var_decl():
    toks = tokenize('x := 42;')
    assert _types(toks) == ['ID', 'OP', 'INT_LIT', 'PUNCT']
    assert _values(toks) == ['x', ':=', '42', ';']


@pytest.mark.xfail(reason="tokenizer has no FLOAT_LIT rule yet")
def test_full_var_decl():
    toks = tokenize('var pi float = 3.14;')
    assert _types(toks) == ['KEYWORD', 'ID', 'KEYWORD', 'OP', 'FLOAT_LIT', 'PUNCT']
    assert _values(toks) == ['var', 'pi', 'float', '=', '3.14', ';']


def test_keyword_vs_identifier():
    toks = tokenize('if iffy')
    assert _types(toks) == ['KEYWORD', 'ID']
    assert _values(toks) == ['if', 'iffy']


def test_function_signature():
    toks = tokenize('def add(a int, b int) int {}')
    assert _values(toks) == [
        'def', 'add', '(', 'a', 'int', ',', 'b', 'int', ')', 'int', '{', '}',
    ]


