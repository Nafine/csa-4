import pytest

from translator.parser import Parser, VarDecl
from translator.semantic import SemanticAnalyzer, SemanticError
from translator.tokenizer import tokenize


def _analyze(src: str):
    program = Parser(tokenize(src)).parse()
    SemanticAnalyzer().analyze(program)
    return program


def test_resolves_short_var_decl_with_read():
    program = _analyze('def main() void { c := read(); }')
    decl = program.top_levels[0].body.stmts[0]
    assert isinstance(decl, VarDecl)
    assert decl.var_type == 'int'


def test_resolves_short_var_decl_with_func_call():
    src = """
        def f() bool { return true; }
        def main() void { x := f(); }
    """
    program = _analyze(src)
    decl = program.top_levels[1].body.stmts[0]
    assert decl.var_type == 'bool'


def test_main_signature_required():
    with pytest.raises(SemanticError, match='main'):
        _analyze('def main() int { return 0; }')


def test_main_must_take_no_params():
    with pytest.raises(SemanticError, match='main'):
        _analyze('def main(x int) void {}')


def test_undeclared_variable():
    with pytest.raises(SemanticError, match='undeclared'):
        _analyze('def main() void { x = 1; }')


def test_use_before_declaration():
    with pytest.raises(SemanticError, match='undeclared'):
        _analyze('def main() void { y := x; var x int = 1; }')


def test_unknown_function():
    with pytest.raises(SemanticError, match='unknown function'):
        _analyze('def main() void { foo(1); }')


def test_arity_mismatch():
    src = """
        def add(a int, b int) int { return a + b; }
        def main() void { x := add(1); }
    """
    with pytest.raises(SemanticError, match='expected 2 args'):
        _analyze(src)


def test_param_type_mismatch():
    src = """
        def f(x int) int { return x; }
        def main() void { y := f(true); }
    """
    with pytest.raises(SemanticError, match="parameter 'x'"):
        _analyze(src)


def test_assignment_type_mismatch():
    src = "def main() void { var x int = 1; x = true; }"
    with pytest.raises(SemanticError, match='expected int'):
        _analyze(src)


def test_arithmetic_type_check():
    with pytest.raises(SemanticError, match="requires int operands"):
        _analyze('def main() void { var x int = 1 + true; }')


def test_logical_type_check():
    with pytest.raises(SemanticError, match='requires bool operands'):
        _analyze('def main() void { var x bool = 1 && 0; }')


def test_unary_minus_requires_int():
    with pytest.raises(SemanticError, match="unary '-' requires int"):
        _analyze('def main() void { var x int = -true; }')


def test_unary_not_requires_bool():
    with pytest.raises(SemanticError, match="unary '!' requires bool"):
        _analyze('def main() void { var x bool = !1; }')

def test_prefix_inc_requires_int():
    with pytest.raises(SemanticError, match=r'unary "\+\+" requires int'):
        _analyze('def main() void { var x bool = true; a := ++x; }')

def test_prefix_dec_requires_int():
    with pytest.raises(SemanticError, match='unary "--" requires int'):
        _analyze('def main() void { var x bool = true; a := --x; }')

def test_compare_same_type():
    with pytest.raises(SemanticError, match='same-type operands'):
        _analyze('def main() void { var x bool = 1 == true; }')


def test_if_condition_must_be_int_or_bool():
    src = 'def main() void { if ("hi") { } }'
    with pytest.raises(SemanticError, match='condition must be int or bool'):
        _analyze(src)


def test_while_condition_int_allowed():
    _analyze('def main() void { var c int = 1; while (c) { c = 0; } }')


def test_return_type_mismatch():
    src = 'def f() int { return true; } def main() void {}'
    with pytest.raises(SemanticError, match='return type mismatch'):
        _analyze(src)


def test_void_return_with_value_rejected():
    with pytest.raises(SemanticError, match='void function'):
        _analyze('def main() void { return 1; }')


def test_non_void_return_without_value_rejected():
    src = 'def f() int { return; } def main() void {}'
    with pytest.raises(SemanticError, match='must return a value'):
        _analyze(src)


def test_missing_return_in_non_void():
    src = 'def f() int { var x int = 1; } def main() void {}'
    with pytest.raises(SemanticError, match='may exit without returning'):
        _analyze(src)


def test_full_paths_return_through_if_else():
    src = """
        def sign(x int) int {
            if (x < 0) { return 0 - 1; } else { return 1; }
        }
        def main() void {}
    """
    _analyze(src)


def test_print_accepts_int_bool_string():
    _analyze('def main() void { print(1); print(true); print("hi"); }')


def test_redeclaration_in_same_scope_rejected():
    src = 'def main() void { var x int = 1; var x int = 2; }'
    with pytest.raises(SemanticError, match='redeclaration'):
        _analyze(src)


def test_shadowing_in_inner_scope_allowed():
    _analyze("""
        def main() void {
            var x int = 1;
            if (x > 0) { var x int = 2; print(x); }
        }
    """)


def test_array_basic_decl_and_use():
    _analyze("""
        def main() void {
            var arr int[5];
            arr[0] = 42;
            print(arr[0]);
        }
    """)


def test_array_string_element_rejected():
    with pytest.raises(SemanticError, match='must be int or bool'):
        _analyze('def main() void { var s string[3]; }')


def test_array_index_must_be_int():
    with pytest.raises(SemanticError, match='index'):
        _analyze("""
            def main() void {
                var arr int[3];
                arr[true] = 1;
            }
        """)


def test_array_assign_type_mismatch():
    with pytest.raises(SemanticError, match='element type is int'):
        _analyze("""
            def main() void {
                var arr int[3];
                arr[0] = true;
            }
        """)


def test_array_bare_use_rejected():
    with pytest.raises(SemanticError, match='must be indexed'):
        _analyze("""
            def main() void {
                var arr int[3];
                var x int = arr;
            }
        """)


def test_array_assign_undeclared_array():
    with pytest.raises(SemanticError, match='undeclared'):
        _analyze('def main() void { arr[0] = 1; }')


def test_array_index_on_scalar():
    with pytest.raises(SemanticError, match='not an array'):
        _analyze("""
            def main() void {
                var x int = 1;
                var y int = x[0];
            }
        """)


def test_bool_array_assign_bool():
    _analyze("""
        def main() void {
            var flags bool[3];
            flags[0] = true;
            flags[1] = false;
        }
    """)


def test_array_param_rejected():
    with pytest.raises(SemanticError, match='array parameters'):
        _analyze("""
            def f(a int[3]) void { }
            def main() void {}
        """)
