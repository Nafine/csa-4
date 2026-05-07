import pytest

from translator.parser import (
    AssignStmt,
    BinaryExpr,
    Block,
    ElifBranch,
    ExprStmt,
    FuncCall,
    FuncDecl,
    Identifier,
    IfStmt,
    Literal,
    Parser,
    ParserError,
    Program,
    ReturnStmt,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)
from translator.tokenizer import tokenize


def _parse(src):
    return Parser(tokenize(src)).parse()


def test_empty_main():
    prog = _parse('def main() void {}')
    assert isinstance(prog, Program)
    assert len(prog.top_levels) == 1
    fn = prog.top_levels[0]
    assert isinstance(fn, FuncDecl)
    assert fn.name == 'main'
    assert fn.params == []
    assert fn.return_type == 'void'
    assert fn.body.stmts == []


def test_missing_main_raises():
    with pytest.raises(ParserError, match='main'):
        _parse('var x int = 1;')


def test_top_level_var_decl():
    prog = _parse('var x int = 42; def main() void {}')
    assert isinstance(prog.top_levels[0], VarDecl)
    assert prog.top_levels[0].name == 'x'
    assert prog.top_levels[0].var_type == 'int'
    assert isinstance(prog.top_levels[0].expr, Literal)
    assert prog.top_levels[0].expr.value == 42


def test_top_level_short_var_decl():
    prog = _parse('num := 3; def main() void {}')
    decl = prog.top_levels[0]
    assert isinstance(decl, VarDecl)
    assert decl.name == 'num'
    assert decl.var_type == 'int'  # инференс по литералу
    assert decl.expr.value == 3


def test_func_with_params_and_return():
    prog = _parse('def add(a int, b int) int { return a + b; } def main() void {}')
    add = prog.top_levels[0]
    assert isinstance(add, FuncDecl)
    assert add.name == 'add'
    assert [(p.name, p.param_type) for p in add.params] == [('a', 'int'), ('b', 'int')]
    assert add.return_type == 'int'

    ret = add.body.stmts[0]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.expr, BinaryExpr) and ret.expr.op == '+'


def test_arith_precedence():
    """a + b * c должен парситься как a + (b * c)."""
    prog = _parse('def main() void { x := a + b * c; }')
    decl = prog.top_levels[0].body.stmts[0]
    assert isinstance(decl, VarDecl)
    expr = decl.expr
    assert isinstance(expr, BinaryExpr) and expr.op == '+'
    assert isinstance(expr.left, Identifier) and expr.left.name == 'a'
    assert isinstance(expr.right, BinaryExpr) and expr.right.op == '*'


def test_paren_overrides_precedence():
    """(a + b) * c должен парситься как (a + b) * c."""
    prog = _parse('def main() void { x := (a + b) * c; }')
    expr = prog.top_levels[0].body.stmts[0].expr
    assert isinstance(expr, BinaryExpr) and expr.op == '*'
    assert isinstance(expr.left, BinaryExpr) and expr.left.op == '+'
    assert isinstance(expr.right, Identifier) and expr.right.name == 'c'


def test_unary_minus_and_not():
    prog = _parse('def main() void { a := -x; b := !flag; }')
    [a, b] = prog.top_levels[0].body.stmts
    assert isinstance(a.expr, UnaryExpr) and a.expr.op == '-'
    assert isinstance(b.expr, UnaryExpr) and b.expr.op == '!'


def test_logical_chain():
    """a && b || c => (a && b) || c"""
    prog = _parse('def main() void { x := a && b || c; }')
    expr = prog.top_levels[0].body.stmts[0].expr
    assert isinstance(expr, BinaryExpr) and expr.op == '||'
    assert isinstance(expr.left, BinaryExpr) and expr.left.op == '&&'


def test_if_else():
    prog = _parse('def main() void { if (a > 0) { b = 1; } else { b = 2; } }')
    if_stmt = prog.top_levels[0].body.stmts[0]
    assert isinstance(if_stmt, IfStmt)
    assert isinstance(if_stmt.condition, BinaryExpr) and if_stmt.condition.op == '>'
    assert if_stmt.elifs == []
    assert isinstance(if_stmt.else_block, Block)
    assert len(if_stmt.then_block.stmts) == 1
    assert len(if_stmt.else_block.stmts) == 1


def test_if_elif_else():
    prog = _parse('def main() void { if (a) { x = 1; } else if (b) { x = 2; } else { x = 3; } }')
    if_stmt = prog.top_levels[0].body.stmts[0]
    assert len(if_stmt.elifs) == 1
    assert isinstance(if_stmt.elifs[0], ElifBranch)
    assert if_stmt.else_block is not None


def test_while():
    prog = _parse('def main() void { while (x > 0) { x = x - 1; } }')
    w = prog.top_levels[0].body.stmts[0]
    assert isinstance(w, WhileStmt)
    assert isinstance(w.condition, BinaryExpr)
    assert isinstance(w.body.stmts[0], AssignStmt)


def test_return_with_and_without_expr():
    prog = _parse('def f() int { return 42; } def main() void { return; }')
    f_ret = prog.top_levels[0].body.stmts[0]
    main_ret = prog.top_levels[1].body.stmts[0]
    assert isinstance(f_ret, ReturnStmt) and isinstance(f_ret.expr, Literal)
    assert f_ret.expr.value == 42
    assert isinstance(main_ret, ReturnStmt) and main_ret.expr is None


def test_func_call_with_args():
    prog = _parse('def main() void { print("hi", 42); }')
    stmt = prog.top_levels[0].body.stmts[0]
    assert isinstance(stmt, ExprStmt)
    call = stmt.expr
    assert isinstance(call, FuncCall)
    assert call.name == 'print'
    assert len(call.args) == 2
    assert isinstance(call.args[0], Literal) and call.args[0].value == 'hi'
    assert isinstance(call.args[1], Literal) and call.args[1].value == 42


def test_builtin_must_be_called():
    with pytest.raises(ParserError):
        _parse('def main() void { x := print; }')
