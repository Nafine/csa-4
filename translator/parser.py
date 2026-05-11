from dataclasses import dataclass

from .tokenizer import Token


@dataclass
class ASTNode:
    pass


@dataclass
class Program(ASTNode):
    top_levels: list[ASTNode]


@dataclass
class Identifier(ASTNode):
    name: str


@dataclass
class Param(ASTNode):
    name: str
    param_type: str


@dataclass
class Block(ASTNode):
    stmts: list[ASTNode]


@dataclass
class FuncDecl(ASTNode):
    name: str
    params: list[Param]
    return_type: str
    body: Block


@dataclass
class VarDecl(ASTNode):
    name: str
    var_type: str
    expr: ASTNode | None = None


@dataclass
class AssignStmt(ASTNode):
    name: str
    expr: ASTNode


@dataclass
class IndexExpr(ASTNode):
    target: ASTNode
    index: ASTNode


@dataclass
class IndexAssign(ASTNode):
    name: str
    index: ASTNode
    expr: ASTNode


@dataclass
class ElifBranch(ASTNode):
    condition: ASTNode
    body: Block


@dataclass
class IfStmt(ASTNode):
    condition: ASTNode
    then_block: Block
    elifs: list[ElifBranch]
    else_block: Block | None


@dataclass
class WhileStmt(ASTNode):
    condition: ASTNode
    body: Block


@dataclass
class ReturnStmt(ASTNode):
    expr: ASTNode | None


@dataclass
class ExprStmt(ASTNode):
    expr: ASTNode


@dataclass
class BinaryExpr(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode


@dataclass
class UnaryExpr(ASTNode):
    op: str
    expr: ASTNode


@dataclass
class Literal(ASTNode):
    value: str | int | bool
    literal_type: str


@dataclass
class FuncCall(ASTNode):
    name: str
    args: list[ASTNode]


class ParserError(Exception):
    pass


_ESCAPE = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'", '0': '\0'}


def _decode_escapes(s: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            out.append(_ESCAPE.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek_next(self) -> Token | None:
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return None

    def advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def match(self, expected_type: str, expected_value: str | None = None) -> bool:
        token = self.peek()
        if not token:
            return False
        if token.type != expected_type:
            return False
        if expected_value is not None and token.value != expected_value:
            return False
        return True

    def consume(self, expected_type: str, expected_value: str | None = None) -> Token:
        if self.match(expected_type, expected_value):
            return self.advance()

        token = self.peek()
        expected = expected_value if expected_value else expected_type
        got = f"'{token.value}' ({token.type})" if token else "EOF"
        raise ParserError(f"Expected {expected}, got {got} at token index {self.pos}")

    def parse(self) -> Program:
        top_levels: list[ASTNode] = []
        while self.peek() is not None:
            top_levels.append(self.parse_top_level())

        has_main = any(isinstance(node, FuncDecl) and node.name == 'main' for node in top_levels)
        if not has_main:
            raise ParserError("Expected main function")

        return Program(top_levels)

    def parse_top_level(self) -> ASTNode:
        if self.match('KEYWORD', 'def'):
            return self.parse_func_decl()
        elif self.match('KEYWORD', 'var'):
            return self.parse_var_decl()
        elif self.match('ID') and (nxt := self.peek_next()) is not None and nxt.value == ':=':
            return self.parse_short_var_decl()
        else:
            raise ParserError(f"Expected function or variable declaration at top level, got {self.peek()}")

    def parse_func_decl(self) -> FuncDecl:
        self.consume('KEYWORD', 'def')
        name = self.consume('ID').value
        self.consume('PUNCT', '(')
        params = self.parse_params() if not self.match('PUNCT', ')') else []
        self.consume('PUNCT', ')')
        ret_type = self.parse_type()
        body = self.parse_block()
        return FuncDecl(name, params, ret_type, body)

    def parse_params(self) -> list[Param]:
        params = [self.parse_param()]
        while self.match('PUNCT', ','):
            self.consume('PUNCT', ',')
            params.append(self.parse_param())
        return params

    def parse_param(self) -> Param:
        name = self.consume('ID').value
        p_type = self.parse_type()
        return Param(name, p_type)

    def parse_type(self) -> str:
        token = self.consume('KEYWORD')
        if token.value not in ['int', 'bool', 'string', 'void']:
            raise ParserError(f"Expected type, got {token.value}")
        base = token.value
        if self.match('PUNCT', '['):
            self.consume('PUNCT', '[')
            size_token = self.consume('INT_LIT')
            self.consume('PUNCT', ']')
            size = int(size_token.value)
            if size <= 0:
                raise ParserError(f"array size must be positive, got {size}")
            return f'{base}[{size}]'
        return base

    def parse_block(self) -> Block:
        self.consume('PUNCT', '{')
        stmts = []
        while not self.match('PUNCT', '}'):
            stmts.append(self.parse_stmt())
        self.consume('PUNCT', '}')
        return Block(stmts)

    def parse_stmt(self) -> ASTNode:
        if self.match('KEYWORD', 'var'):
            return self.parse_var_decl()
        elif self.match('KEYWORD', 'if'):
            return self.parse_branch_stmt()
        elif self.match('KEYWORD', 'while'):
            return self.parse_while_stmt()
        elif self.match('KEYWORD', 'return'):
            return self.parse_return_stmt()

        if self.match('ID') and (nxt := self.peek_next()) is not None:
            next_val = nxt.value
            if next_val == '=':
                return self.parse_assign_stmt()
            elif next_val == ':=':
                return self.parse_short_var_decl()
            elif next_val == '[':
                return self.parse_index_or_expr_stmt()

        return self.parse_expr_stmt()

    def parse_index_or_expr_stmt(self) -> ASTNode:
        start = self.pos
        name = self.consume('ID').value
        self.consume('PUNCT', '[')
        index = self.parse_expr()
        self.consume('PUNCT', ']')
        if self.match('OP', '='):
            self.consume('OP', '=')
            rhs = self.parse_expr()
            self.consume('PUNCT', ';')
            return IndexAssign(name, index, rhs)
        # not an assignment - rewind and parse as expression statement
        self.pos = start
        return self.parse_expr_stmt()

    def parse_var_decl(self) -> VarDecl:
        self.consume('KEYWORD', 'var')
        name = self.consume('ID').value
        v_type = self.parse_type()

        expr = None

        if self.match('OP', '='):
            if v_type.endswith(']'):
                raise ParserError(
                    f"array variable '{name}' cannot have an initializer"
                )
            self.consume('OP', '=')
            expr = self.parse_expr()

        self.consume('PUNCT', ';')
        return VarDecl(name, v_type, expr)

    def parse_assign_stmt(self) -> AssignStmt:
        name = self.consume('ID').value
        self.consume('OP', '=')
        expr = self.parse_expr()
        self.consume('PUNCT', ';')
        return AssignStmt(name, expr)

    def parse_short_var_decl(self) -> VarDecl:
        name = self.consume('ID').value
        self.consume('OP', ':=')
        expr = self.parse_expr()
        self.consume('PUNCT', ';')

        inferred_type = self.infer_type(expr)
        return VarDecl(name, inferred_type, expr)

    def infer_type(self, expr: ASTNode) -> str:
        if isinstance(expr, Literal):
            if expr.literal_type == 'INT_LIT':
                return 'int'
            if expr.literal_type == 'BOOL_LIT':
                return 'bool'
            if expr.literal_type == 'STRING_LIT':
                return 'string'

        elif isinstance(expr, BinaryExpr):
            if expr.op in ['&&', '||', '==', '!=', '<', '>', '<=', '>=']:
                return 'bool'

            return self.infer_type(expr.left)

        elif isinstance(expr, UnaryExpr):
            if expr.op == '!':
                return 'bool'
            return self.infer_type(expr.expr)

        return 'unknown'

    def parse_branch_stmt(self) -> IfStmt:
        self.consume('KEYWORD', 'if')
        self.consume('PUNCT', '(')
        condition = self.parse_expr()
        self.consume('PUNCT', ')')
        then_block = self.parse_block()

        elifs = []
        while self.match('KEYWORD', 'else') and (nxt := self.peek_next()) is not None and nxt.value == 'if':
            self.consume('KEYWORD', 'else')
            self.consume('KEYWORD', 'if')
            self.consume('PUNCT', '(')
            elif_cond = self.parse_expr()
            self.consume('PUNCT', ')')
            elif_body = self.parse_block()
            elifs.append(ElifBranch(elif_cond, elif_body))

        else_block = None
        if self.match('KEYWORD', 'else'):
            self.consume('KEYWORD', 'else')
            else_block = self.parse_block()

        return IfStmt(condition, then_block, elifs, else_block)

    def parse_while_stmt(self) -> WhileStmt:
        self.consume('KEYWORD', 'while')
        self.consume('PUNCT', '(')
        condition = self.parse_expr()
        self.consume('PUNCT', ')')
        body = self.parse_block()
        return WhileStmt(condition, body)

    def parse_return_stmt(self) -> ReturnStmt:
        self.consume('KEYWORD', 'return')
        expr = None
        if not self.match('PUNCT', ';'):
            expr = self.parse_expr()
        self.consume('PUNCT', ';')
        return ReturnStmt(expr)

    def parse_expr_stmt(self) -> ExprStmt:
        expr = self.parse_expr()
        self.consume('PUNCT', ';')
        return ExprStmt(expr)

    def parse_expr(self) -> ASTNode:
        return self.parse_logical_or()

    def parse_logical_or(self) -> ASTNode:
        node = self.parse_logical_and()
        while self.match('OP', '||'):
            op = self.advance().value
            right = self.parse_logical_and()
            node = BinaryExpr(node, op, right)
        return node

    def parse_logical_and(self) -> ASTNode:
        node = self.parse_equality()
        while self.match('OP', '&&'):
            op = self.advance().value
            right = self.parse_equality()
            node = BinaryExpr(node, op, right)
        return node

    def parse_equality(self) -> ASTNode:
        node = self.parse_relational()
        while self.match('OP', '==') or self.match('OP', '!='):
            op = self.advance().value
            right = self.parse_relational()
            node = BinaryExpr(node, op, right)
        return node

    def parse_relational(self) -> ASTNode:
        node = self.parse_additive()
        while self.match('OP', '<') or self.match('OP', '>') or \
                self.match('OP', '<=') or self.match('OP', '>='):
            op = self.advance().value
            right = self.parse_additive()
            node = BinaryExpr(node, op, right)
        return node

    def parse_additive(self) -> ASTNode:
        node = self.parse_multiplicative()
        while self.match('OP', '+') or self.match('OP', '-'):
            op = self.advance().value
            right = self.parse_multiplicative()
            node = BinaryExpr(node, op, right)
        return node

    def parse_multiplicative(self) -> ASTNode:
        node = self.parse_unary()
        while self.match('OP', '*') or self.match('OP', '/') or self.match('OP', '%'):
            op = self.advance().value
            right = self.parse_unary()
            node = BinaryExpr(node, op, right)
        return node

    def parse_unary(self) -> ASTNode:
        if self.match('OP', '!') or self.match('OP', '-'):
            op = self.advance().value
            expr = self.parse_unary()
            return UnaryExpr(op, expr)
        elif self.match('OP', '++') or self.match('OP', '--'):
            op = self.advance().value
            idt = self.parse_unary()
            return UnaryExpr(op, idt)
        return self.parse_primary()

    def parse_primary(self) -> ASTNode:
        token = self.peek()

        if self.match('INT_LIT'):
            return Literal(int(self.advance().value), 'INT_LIT')
        elif self.match('BOOL_LIT'):
            bool_val = self.advance().value == 'true'
            return Literal(bool_val, 'BOOL_LIT')
        elif self.match('STRING_LIT'):
            str_val = _decode_escapes(self.advance().value[1:-1])
            return Literal(str_val, 'STRING_LIT')
        elif self.match('PUNCT', '('):
            self.consume('PUNCT', '(')
            expr = self.parse_expr()
            self.consume('PUNCT', ')')
            return expr

        is_builtin = (
                self.match('KEYWORD', 'print')
                or self.match('KEYWORD', 'read')
        )
        is_id = self.match('ID')

        if is_builtin or is_id:
            name_token = self.advance()
            if self.match('PUNCT', '('):
                self.consume('PUNCT', '(')
                args = self.parse_args() if not self.match('PUNCT', ')') else []
                self.consume('PUNCT', ')')
                return FuncCall(name_token.value, args)
            if is_builtin:
                raise ParserError(f"Built-in keyword {name_token.value} must be called as a function")
            node: ASTNode = Identifier(name_token.value)
            while self.match('PUNCT', '['):
                self.consume('PUNCT', '[')
                index = self.parse_expr()
                self.consume('PUNCT', ']')
                node = IndexExpr(node, index)
            return node

        raise ParserError(f"Unexpected token in expression: {token}")

    def parse_args(self) -> list[ASTNode]:
        args = [self.parse_expr()]
        while self.match('PUNCT', ','):
            self.consume('PUNCT', ',')
            args.append(self.parse_expr())
        return args
