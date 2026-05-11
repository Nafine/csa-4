from __future__ import annotations

import dataclasses as _dc

from translator.parser import ASTNode


def format_ast(node: ASTNode) -> str:
    lines: list[str] = []
    _ast_collect(node, "", "", lines)
    return "\n".join(lines)


def _is_ast_node(value: ASTNode) -> bool:
    return _dc.is_dataclass(value) and not isinstance(value, type)


def _ast_collect(node: ASTNode, prefix: str, child_prefix: str, lines: list[str]) -> None:
    if not _is_ast_node(node):
        lines.append(prefix + repr(node))
        return

    scalars: list[tuple[str, ASTNode]] = []
    children: list[tuple[str, ASTNode]] = []
    for f in _dc.fields(node):
        v = getattr(node, f.name)
        if v is None:
            continue
        if _is_ast_node(v):
            children.append((f.name, v))
        elif isinstance(v, list):
            for j, item in enumerate(v):
                children.append((f"{f.name}[{j}]", item))
        else:
            scalars.append((f.name, v))

    scalar_str = " ".join(f"{k}={v!r}" for k, v in scalars)
    header = type(node).__name__ + ("  " + scalar_str if scalar_str else "")
    lines.append(prefix + header)

    for i, (label, child) in enumerate(children):
        last = i == len(children) - 1
        conn = "└─ " if last else "├─ "
        next_cp = child_prefix + ("   " if last else "│  ")
        _ast_collect(child, child_prefix + conn + label + ": ", next_cp, lines)
