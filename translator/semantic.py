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
    IndexAssign,
    IndexExpr,
    Literal,
    Param,
    Program,
    ReturnStmt,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)


class SemanticError(Exception):
    pass


_ARITH_OPS = {'+', '-', '*', '/', '%'}
_COMPARE_OPS = {'==', '!=', '<', '<=', '>', '>='}
_LOGICAL_OPS = {'&&', '||'}
_ARRAY_ELEMENT_TYPES = {'int', 'bool'}

TypeInfo = str | tuple[str, str, int]


def parse_array_type(t: str) -> tuple[str, int] | None:
    """Return (element_type, size) if t is an array type like 'int[10]', else None."""
    if not t.endswith(']') or '[' not in t:
        return None
    base, _, rest = t.partition('[')
    size_str = rest[:-1]
    try:
        size = int(size_str)
    except ValueError:
        return None
    return base, size


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.functions: dict[str, FuncDecl] = {}
        self.scopes: list[dict[str, TypeInfo]] = []
        self.current_func_return: str | None = None

    def analyze(self, program: Program) -> Program:
        for node in program.top_levels:
            if isinstance(node, FuncDecl):
                if node.name in self.functions:
                    raise SemanticError(f'duplicate function: {node.name}')
                self.functions[node.name] = node

        main = self.functions.get('main')
        if main is None:
            raise SemanticError('missing main() entrypoint')
        if main.params:
            raise SemanticError('main() must take no parameters')
        if main.return_type != 'void':
            raise SemanticError("main() must return 'void'")

        self.scopes.append({})
        for node in program.top_levels:
            if isinstance(node, VarDecl):
                self._check_top_var_decl(node)

        for func in self.functions.values():
            self._check_function(func)

        self.scopes.pop()
        return program

    def _check_top_var_decl(self, decl: VarDecl) -> None:
        array_info = parse_array_type(decl.var_type)
        if array_info is not None:
            elem_type, size = array_info
            if elem_type not in _ARRAY_ELEMENT_TYPES:
                raise SemanticError(
                    f"top-level array '{decl.name}': element type must be int or bool, got {elem_type}"
                )
            if decl.expr is not None:
                raise SemanticError(
                    f"top-level array '{decl.name}' cannot have an initializer"
                )
            self._declare(decl.name, ('array', elem_type, size))
            return

        if decl.var_type not in ('int', 'bool', 'string', 'unknown'):
            raise SemanticError(
                f"top-level var '{decl.name}': unsupported type '{decl.var_type}'"
            )
        if decl.expr is not None and not isinstance(decl.expr, Literal):
            raise SemanticError(
                f"top-level var '{decl.name}' initializer must be a literal"
            )
        if decl.expr is not None:
            init_type = self._infer(decl.expr)
            if decl.var_type == 'unknown':
                decl.var_type = init_type
            elif init_type != decl.var_type:
                raise SemanticError(
                    f"top-level var '{decl.name}': type {decl.var_type} does not match initializer {init_type}"
                )
        elif decl.var_type == 'unknown':
            raise SemanticError(f"cannot infer type for '{decl.name}'")

        self._declare(decl.name, decl.var_type)

    def _check_function(self, func: FuncDecl) -> None:
        self.current_func_return = func.return_type
        self.scopes.append({})
        for param in func.params:
            self._check_param(param)
            self._declare(param.name, param.param_type)

        self._check_block(func.body)
        self.scopes.pop()
        self.current_func_return = None

        if func.return_type != 'void' and not _all_paths_return(func.body):
            raise SemanticError(
                f"function '{func.name}' may exit without returning a value"
            )

    @staticmethod
    def _check_param(param: Param) -> None:
        if parse_array_type(param.param_type) is not None:
            raise SemanticError(
                f"parameter '{param.name}': array parameters are not supported"
            )
        if param.param_type not in ('int', 'bool', 'string'):
            raise SemanticError(
                f"parameter '{param.name}': unsupported type '{param.param_type}'"
            )

    def _check_block(self, block: Block) -> None:
        self.scopes.append({})
        for stmt in block.stmts:
            self._check_stmt(stmt)
        self.scopes.pop()

    def _check_stmt(self, stmt: object) -> None:
        if isinstance(stmt, VarDecl):
            self._check_var_decl(stmt)
            return
        if isinstance(stmt, AssignStmt):
            self._check_assign(stmt)
            return
        if isinstance(stmt, IndexAssign):
            self._check_index_assign(stmt)
            return
        if isinstance(stmt, ExprStmt):
            self._infer(stmt.expr)
            return
        if isinstance(stmt, IfStmt):
            self._check_if(stmt)
            return
        if isinstance(stmt, WhileStmt):
            self._check_while(stmt)
            return
        if isinstance(stmt, ReturnStmt):
            self._check_return(stmt)
            return
        raise SemanticError(f'unsupported statement: {type(stmt).__name__}')

    def _check_index_assign(self, stmt: IndexAssign) -> None:
        info = self._lookup(stmt.name)
        if info is None:
            raise SemanticError(f"assignment to undeclared variable '{stmt.name}'")
        if not (isinstance(info, tuple) and info[0] == 'array'):
            raise SemanticError(f"'{stmt.name}' is not an array; cannot index")
        _, elem_type, _ = info
        index_type = self._infer(stmt.index)
        if index_type != 'int':
            raise SemanticError(
                f"array index for '{stmt.name}' must be int, got {index_type}"
            )
        rhs_type = self._infer(stmt.expr)
        if rhs_type != elem_type:
            raise SemanticError(
                f"array '{stmt.name}' element type is {elem_type}, got {rhs_type}"
            )

    def _check_var_decl(self, decl: VarDecl) -> None:
        array_info = parse_array_type(decl.var_type)
        if array_info is not None:
            elem_type, size = array_info
            if elem_type not in _ARRAY_ELEMENT_TYPES:
                raise SemanticError(
                    f"array '{decl.name}': element type must be int or bool, got {elem_type}"
                )
            if decl.expr is not None:
                raise SemanticError(
                    f"array '{decl.name}' cannot have an initializer"
                )
            self._declare(decl.name, ('array', elem_type, size))
            return

        declared = decl.var_type
        if declared not in ('int', 'bool', 'string', 'unknown'):
            raise SemanticError(
                f"var '{decl.name}': unsupported type '{declared}'"
            )
        if decl.expr is None:
            if declared == 'unknown':
                raise SemanticError(f"cannot infer type for '{decl.name}'")
            self._declare(decl.name, declared)
            return

        init_type = self._infer(decl.expr)
        if declared == 'unknown':
            decl.var_type = init_type
            self._declare(decl.name, init_type)
            return
        if init_type != declared:
            raise SemanticError(
                f"var '{decl.name}': declared type {declared} does not match initializer type {init_type}"
            )
        self._declare(decl.name, declared)

    def _check_assign(self, stmt: AssignStmt) -> None:
        target_type = self._lookup(stmt.name)
        if target_type is None:
            raise SemanticError(f"assignment to undeclared variable '{stmt.name}'")
        if isinstance(target_type, tuple):
            raise SemanticError(
                f"cannot assign to array '{stmt.name}' as a whole; use indexing"
            )
        rhs_type = self._infer(stmt.expr)
        if rhs_type != target_type:
            raise SemanticError(
                f"assignment to '{stmt.name}': expected {target_type}, got {rhs_type}"
            )

    def _check_if(self, stmt: IfStmt) -> None:
        cond_type = self._infer(stmt.condition)
        if cond_type not in ('int', 'bool'):
            raise SemanticError(f"if condition must be int or bool, got {cond_type}")
        self._check_block(stmt.then_block)
        for branch in stmt.elifs:
            assert isinstance(branch, ElifBranch)
            sub_cond = self._infer(branch.condition)
            if sub_cond not in ('int', 'bool'):
                raise SemanticError(
                    f"elif condition must be int or bool, got {sub_cond}"
                )
            self._check_block(branch.body)
        if stmt.else_block is not None:
            self._check_block(stmt.else_block)

    def _check_while(self, stmt: WhileStmt) -> None:
        cond_type = self._infer(stmt.condition)
        if cond_type not in ('int', 'bool'):
            raise SemanticError(
                f"while condition must be int or bool, got {cond_type}"
            )
        self._check_block(stmt.body)

    def _check_return(self, stmt: ReturnStmt) -> None:
        expected = self.current_func_return
        if expected is None:
            raise SemanticError('return outside of function')
        if expected == 'void':
            if stmt.expr is not None:
                raise SemanticError('void function must return without a value')
            return
        if stmt.expr is None:
            raise SemanticError(
                f'non-void function must return a value of type {expected}'
            )
        actual = self._infer(stmt.expr)
        if actual != expected:
            raise SemanticError(
                f'return type mismatch: expected {expected}, got {actual}'
            )

    def _infer(self, expr: object) -> str:
        if isinstance(expr, Literal):
            mapping = {'INT_LIT': 'int', 'BOOL_LIT': 'bool', 'STRING_LIT': 'string'}
            kind = mapping.get(expr.literal_type)
            if kind is None:
                raise SemanticError(f'unsupported literal type: {expr.literal_type}')
            return kind
        if isinstance(expr, Identifier):
            t = self._lookup(expr.name)
            if t is None:
                raise SemanticError(f"undeclared variable '{expr.name}'")
            if isinstance(t, tuple):
                raise SemanticError(
                    f"array '{expr.name}' must be indexed before use"
                )
            return t
        if isinstance(expr, UnaryExpr):
            return self._infer_unary(expr)
        if isinstance(expr, BinaryExpr):
            return self._infer_binary(expr)
        if isinstance(expr, FuncCall):
            return self._infer_call(expr)
        if isinstance(expr, IndexExpr):
            return self._infer_index(expr)
        raise SemanticError(f'unsupported expression: {type(expr).__name__}')

    def _infer_index(self, expr: IndexExpr) -> str:
        if not isinstance(expr.target, Identifier):
            raise SemanticError('only named arrays can be indexed')
        info = self._lookup(expr.target.name)
        if info is None:
            raise SemanticError(f"undeclared variable '{expr.target.name}'")
        if not (isinstance(info, tuple) and info[0] == 'array'):
            raise SemanticError(f"'{expr.target.name}' is not an array")
        _, elem_type, _ = info
        index_type = self._infer(expr.index)
        if index_type != 'int':
            raise SemanticError(
                f"array index for '{expr.target.name}' must be int, got {index_type}"
            )
        return elem_type

    def _infer_unary(self, expr: UnaryExpr) -> str:
        operand = self._infer(expr.expr)
        if expr.op == '-':
            if operand != 'int':
                raise SemanticError(f"unary '-' requires int, got {operand}")
            return 'int'
        if expr.op == '!':
            if operand != 'bool':
                raise SemanticError(f"unary '!' requires bool, got {operand}")
            return 'bool'
        if expr.op == '++':
            if operand != 'int':
                raise SemanticError(f'unary "++" requires int, got {operand}')
            return 'int'
        if expr.op == '--':
            if operand != 'int':
                raise SemanticError(f'unary "--" requires int, got {operand}')
            return 'int'
        raise SemanticError(f'unsupported unary op: {expr.op}')

    def _infer_binary(self, expr: BinaryExpr) -> str:
        left = self._infer(expr.left)
        right = self._infer(expr.right)
        if expr.op in _ARITH_OPS:
            if left != 'int' or right != 'int':
                raise SemanticError(
                    f"operator '{expr.op}' requires int operands, got {left} and {right}"
                )
            return 'int'
        if expr.op in _COMPARE_OPS:
            if left != right:
                raise SemanticError(
                    f"operator '{expr.op}' requires same-type operands, got {left} and {right}"
                )
            if left not in ('int', 'bool'):
                raise SemanticError(
                    f"operator '{expr.op}' supports int or bool, got {left}"
                )
            return 'bool'
        if expr.op in _LOGICAL_OPS:
            if left != 'bool' or right != 'bool':
                raise SemanticError(
                    f"operator '{expr.op}' requires bool operands, got {left} and {right}"
                )
            return 'bool'
        raise SemanticError(f'unsupported binary op: {expr.op}')

    def _infer_call(self, call: FuncCall) -> str:
        if call.name == 'print':
            if len(call.args) != 1:
                raise SemanticError('print() expects exactly one argument')
            arg_type = self._infer(call.args[0])
            if arg_type not in ('int', 'bool', 'string'):
                raise SemanticError(
                    f"print() argument must be int, bool, or string, got {arg_type}"
                )
            return 'void'
        if call.name == 'read':
            if call.args:
                raise SemanticError('read() expects zero arguments')
            return 'int'

        func = self.functions.get(call.name)
        if func is None:
            raise SemanticError(f"unknown function: '{call.name}'")
        if len(call.args) != len(func.params):
            raise SemanticError(
                f"{call.name}: expected {len(func.params)} args, got {len(call.args)}"
            )
        for arg, param in zip(call.args, func.params, strict=True):
            actual = self._infer(arg)
            if actual != param.param_type:
                raise SemanticError(
                    f"{call.name}: parameter '{param.name}' expects {param.param_type}, got {actual}"
                )
        return func.return_type

    def _declare(self, name: str, type_info: TypeInfo) -> None:
        scope = self.scopes[-1]
        if name in scope:
            raise SemanticError(f"redeclaration of '{name}' in the same scope")
        scope[name] = type_info

    def _lookup(self, name: str) -> TypeInfo | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None


def _all_paths_return(block: Block) -> bool:
    if not block.stmts:
        return False
    last = block.stmts[-1]
    if isinstance(last, ReturnStmt):
        return True
    if isinstance(last, IfStmt) and last.else_block is not None:
        if not _all_paths_return(last.then_block):
            return False
        for branch in last.elifs:
            if not _all_paths_return(branch.body):
                return False
        return _all_paths_return(last.else_block)
    return False
