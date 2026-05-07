from __future__ import annotations

import os
import pprint
from pathlib import Path

import pytest
import yaml

from cli import compile_source
from isa import Instruction, write_debug
from machine import ControlUnit
from simulator import format_state
from translator.parser import Parser
from translator.tokenizer import tokenize


class LiteralStr(str):
    """str subclass that yaml.safe_dump emits as a `|` block scalar."""


def _literal_repr(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', str(data), style='|')


yaml.add_representer(LiteralStr, _literal_repr, Dumper=yaml.SafeDumper)

GOLDEN_DIR = Path(__file__).resolve().parent / 'golden'
CASES = sorted(p.stem for p in GOLDEN_DIR.glob('*.yaml'))
REGEN = os.environ.get('REGEN') == '1'

SLOW_CASES = {'prob1'}

EOF_WORD = 0xFFFFFFFF
TRACE_HEAD_TICKS = 200


def _format_ast(src: str) -> str:
    program = Parser(tokenize(src)).parse()
    return pprint.pformat(program, width=80, indent=2, sort_dicts=False)


def _format_code(words: list[int]) -> str:
    out: list[str] = []
    for w in words:
        for shift in (24, 16, 8, 0):
            out.append(f'{(w >> shift) & 0xFF:02X}')
    return ' '.join(out)


def _disasm(instructions: list[Instruction], data: list[int]) -> str:
    tmp = GOLDEN_DIR / '__tmp.txt'
    write_debug(str(tmp), instructions, data)
    text = tmp.read_text(encoding='utf-8')
    tmp.unlink()
    return text


def _output_words(buf: list[int]) -> list[int]:
    """Trim the trailing EOF sentinel (-1) some programs echo on exhaustion."""
    out: list[int] = []
    for word in buf:
        if word == EOF_WORD:
            break
        out.append(word)
    return out


def _format_stdout(cu: ControlUnit) -> str:
    words = _output_words(cu.dp.output_buffer)
    # Text view: only words that fit in a byte. A numeric print like 906609
    # is reflected in output_hex/output_num and skipped here.
    text_bytes = bytes(w for w in words if 0 <= w <= 0xFF)
    try:
        rendered = text_bytes.decode('utf-8')
    except UnicodeDecodeError:
        rendered = '<non-utf8>'
    return (
        f'ticks: {cu.tick}\n'
        f'output_words: {len(words)}\n'
        f'output_hex: {[hex(w) for w in words]}\n'
        f'output_num: {words}\n'
        f'output_text: {rendered!r}\n'
    )


def _make_cu(code_words: list[int], stdin: str | None) -> ControlUnit:
    input_buf = list(stdin.encode('utf-8')) + [0] if stdin else None
    cu = ControlUnit(input_buf)
    for i, w in enumerate(code_words):
        cu.dp.data_mem[i] = w
    return cu


def _trace_head(code_words: list[int], stdin: str | None, limit: int) -> str:
    cu = _make_cu(code_words, stdin)
    lines: list[str] = []
    while not cu.halted and cu.tick < limit and len(lines) < TRACE_HEAD_TICKS:
        cu.step()
        lines.append(format_state(cu.snapshot()).rstrip('\n'))
    return '\n'.join(lines)


def _params() -> list:
    out = []
    for case in CASES:
        if case in SLOW_CASES:
            out.append(pytest.param(case, marks=pytest.mark.slow))
        else:
            out.append(case)
    return out


@pytest.mark.parametrize('case', _params())
def test_golden(case: str) -> None:
    path = GOLDEN_DIR / f'{case}.yaml'
    spec = yaml.safe_load(path.read_text(encoding='utf-8')) or {}

    src = spec['in_source']
    stdin = spec.get('in_stdin') or ''
    limit = int(spec.get('in_limit', 100_000))

    out_ast = _format_ast(src)

    instructions, data = compile_source(src)
    code_words = [ins.encode() for ins in instructions] + list(data)

    out_code = _format_code(code_words)
    out_code_hex = _disasm(instructions, data)

    cu = _make_cu(code_words, stdin)
    while not cu.halted and cu.tick < limit:
        cu.step()
    if not cu.halted:
        raise AssertionError(f'{case}: did not halt within {limit} ticks (last={cu.tick})')

    out_stdout = _format_stdout(cu)
    out_log = _trace_head(code_words, stdin, limit)

    if REGEN:
        new_spec = {
            'in_source': LiteralStr(src.rstrip('\n')),
            'in_stdin': stdin,
            'in_limit': limit,
            'out_ast': LiteralStr(out_ast.rstrip('\n')),
            'out_code': out_code,
            'out_code_hex': LiteralStr(out_code_hex.rstrip('\n')),
            'out_stdout': LiteralStr(out_stdout),
            'out_log': LiteralStr(out_log.rstrip('\n')),
        }
        with path.open('w', encoding='utf-8') as f:
            yaml.safe_dump(new_spec, f, sort_keys=False, allow_unicode=True, width=78)
        return

    def _norm(s: str | None) -> str:
        return (s or '').rstrip('\n')

    assert _norm(spec.get('out_ast')) == _norm(out_ast), f'{case}: out_ast mismatch'
    assert _norm(spec.get('out_code')) == _norm(out_code), f'{case}: out_code mismatch'
    assert _norm(spec.get('out_code_hex')) == _norm(out_code_hex), f'{case}: out_code_hex mismatch'
    assert _norm(spec.get('out_stdout')) == _norm(out_stdout), f'{case}: out_stdout mismatch'
    assert _norm(spec.get('out_log')) == _norm(out_log), f'{case}: out_log mismatch'
