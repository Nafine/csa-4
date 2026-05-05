from dataclasses import dataclass

from isa import Instruction, Opcode
from machine import DataPath
from translator.parser import Program, FuncDecl, VarDecl, Literal, Identifier, UnaryExpr, BinaryExpr, FuncCall, \
    AssignStmt, ExprStmt, IfStmt, ReturnStmt, WhileStmt


class CodegenError(Exception):
    pass


@dataclass
class _Patch:
    index: int
    name: str


@dataclass
class _Symbol:
    kind: str
    offset: int


class CodeGenerator:
    def __init__(self):
        self.instructions: list[Instruction] = []
        self.data: list[int] = []
        self.symbols: dict[str, _Symbol] = {}
        self.symbol_patches: list[_Patch] = []

    def generate(self, program: Program) -> tuple[list[Instruction], list[int]]:
        self.instructions = []
        self.data = []
        self.symbols = {}
        self.symbol_patches = []

        main_decl: FuncDecl | None = None
        function_decls: list[FuncDecl] = []

        for node in program.top_levels:
            if isinstance(node, VarDecl):
                self._compile_top_var_decl(node)
            elif isinstance(node, FuncDecl):
                function_decls.append(node)
                if node.name == 'main':
                    main_decl = node
            else:
                raise CodegenError(f'unsupported top-level node: {type(node).__name__}')

        if main_decl is None:
            raise CodegenError('missing main() entrypoint')

        jmp_main = self._compile_branch(Opcode.JMP)

        for func in function_decls:
            if func.name == 'main':
                continue
            self.symbols[func.name] = _Symbol('function', self._ip())
            self._compile_block(func.body)
            self._compile_primary(Instruction(Opcode.RET))

        main_addr = self._ip()
        self.symbols[main_decl.name] = _Symbol('function', main_addr)
        self._patch_branch(jmp_main, main_addr)

        self._compile_block(main_decl.body)
        self._compile_primary(Instruction(Opcode.HALT))

        self._resolve_symbols()

        return list(self.instructions), list(self.data)

    def _resolve_symbols(self) -> None:
        data_base = len(self.instructions)
        for patch in self.symbol_patches:
            sym = self.symbols.get(patch.name)
            if sym is None:
                raise CodegenError(f'unresolved symbol: {patch.name}')
            if sym.kind == 'data':
                self.instructions[patch.index].operand = data_base + sym.offset
            elif sym.kind == 'function':
                self.instructions[patch.index].operand = sym.offset
            else:
                raise CodegenError(f'unknown symbol kind: {sym.kind}')

    def _ip(self) -> int:
        return len(self.instructions)

    def _compile_block(self, block):
        for stmt in block.stmts:
            self._compile_stmt(stmt)

    def _compile_stmt(self, stmt) -> None:
        if isinstance(stmt, VarDecl):
            self._compile_var_decl(stmt)
            return
        if isinstance(stmt, AssignStmt):
            self._compile_assign(stmt)
            return
        if isinstance(stmt, ExprStmt):
            self._compile_expression(stmt.expr)
            return
        if isinstance(stmt, IfStmt):
            self._compile_if(stmt)
            return
        if isinstance(stmt, WhileStmt):
            self._compile_while(stmt)
            return
        if isinstance(stmt, ReturnStmt):
            if stmt.expr is not None:
                self._compile_expression(stmt.expr)
            self._compile_primary(Instruction(Opcode.RET))
            return

    def _compile_if(self, stmt: IfStmt):
        self._compile_expression(stmt.condition)
        jz_else = self._compile_branch(Opcode.BEQ)

        self._compile_block(stmt.then_block)

        if stmt.else_block is None:
            self._patch_branch(jz_else, self._ip())
            return

        jmp_end = self._compile_branch(Opcode.JMP)
        self._patch_branch(jz_else, self._ip())
        self._compile_block(stmt.else_block)
        self._patch_branch(jmp_end, self._ip())

    def _compile_while(self, stmt: WhileStmt):
        loop_start = self._ip()
        self._compile_expression(stmt.condition)
        jz_end = self._compile_branch(Opcode.BEQ)

        self._compile_block(stmt.body)
        jz_while = self._compile_branch(Opcode.JMP)
        self._patch_branch(jz_end, self._ip())
        self._patch_branch(jz_while, loop_start)

    def _compile_assign(self, assign: AssignStmt):
        if assign.name not in self.symbols:
            self._allocate(assign.name)
        self._compile_expression(assign.expr)
        self._store(assign.name)

    def _compile_top_var_decl(self, decl: VarDecl) -> None:
        if decl.expr is None:
            self._allocate(decl.name)
            return
        if isinstance(decl.expr, Literal) and decl.expr.literal_type in ('INT_LIT', 'FLOAT_LIT', 'BOOL_LIT'):
            self._allocate(decl.name, self._literal_to_int(decl.expr))
            return
        self._compile_var_decl(decl)

    def _compile_var_decl(self, decl: VarDecl) -> None:
        self._allocate(decl.name)
        if decl.expr is None:
            return
        self._compile_expression(decl.expr)
        self._store(decl.name)

    @staticmethod
    def _literal_to_int(lit: Literal) -> int:
        if lit.literal_type == 'INT_LIT':
            return int(lit.value)
        if lit.literal_type == 'FLOAT_LIT':
            return int(lit.value)
        if lit.literal_type == 'BOOL_LIT':
            return 1 if lit.value else 0
        raise CodegenError(f'cannot statically materialize literal type: {lit.literal_type}')

    def _allocate(self, name: str, value: int = 0) -> int:
        existing = self.symbols.get(name)
        if existing is not None:
            return existing.offset
        offset = len(self.data)
        self.data.append(value)
        self.symbols[name] = _Symbol('data', offset)
        return offset

    def _allocate_cstr(self, value: str) -> str:
        name = f'str:{value}'
        if name in self.symbols:
            return name
        offset = len(self.data)
        for char in value:
            self.data.append(ord(char))
        self.data.append(0)
        self.symbols[name] = _Symbol('data', offset)
        return name

    def _tmp_name(self) -> str:
        name = '$tmp'
        if name not in self.symbols:
            self._allocate(name)
        return name

    def _compile_expression(self, expr) -> None:
        if isinstance(expr, Literal):
            self._compile_lit(expr)
            return
        if isinstance(expr, Identifier):
            self._emit_symbol_ref(Opcode.LD, expr.name)
            return
        if isinstance(expr, UnaryExpr):
            self._compile_unary(expr)
            return
        if isinstance(expr, BinaryExpr):
            self._compile_binary(expr)
            return
        if isinstance(expr, FuncCall):
            self._compile_call(expr)
            return

    def _compile_call(self, call: FuncCall):
        if call.name == 'print':
            if len(call.args) != 1:
                raise CodegenError('print() expects exactly one argument')
            arg = call.args[0]
            if isinstance(arg, Literal) and arg.literal_type == 'STRING_LIT':
                name = self._allocate_cstr(arg.value)
                self._emit_symbol_ref(Opcode.LD, name)
                self._compile_primary(Instruction(Opcode.ST, DataPath.OUTPUT_ADDR))
                return
            self._compile_expression(arg)
            self._compile_primary(Instruction(Opcode.ST, DataPath.OUTPUT_ADDR))
            return
        elif call.name == 'read':
            if call.args:
                raise CodegenError('read() expects zero arguments')
            self._compile_primary(Instruction(Opcode.LD, DataPath.INPUT_ADDR))
            return

        for arg in call.args:
            self._compile_expression(arg)
            self._compile_primary(Instruction(Opcode.PUSH))

        self._emit_symbol_ref(Opcode.CALL, call.name)

    def _compile_binary(self, expr: BinaryExpr) -> None:
        tmp_name = self._tmp_name()
        self._compile_expression(expr.left)
        self._compile_primary(Instruction(Opcode.PUSH))
        self._compile_expression(expr.right)
        self._emit_symbol_ref(Opcode.ST, tmp_name)
        self._compile_primary(Instruction(Opcode.POP))

        operations: dict[str, Opcode] = {
            '+': Opcode.ADD,
            '-': Opcode.SUB,
            '*': Opcode.MUL,
            '/': Opcode.DIV,
            '%': Opcode.REM,
        }

        if expr.op in operations:
            self._emit_symbol_ref(operations[expr.op], tmp_name)
            return

        compares = {'==', '!=', '<', '<=', '>', '>='}

        if expr.op not in compares:
            raise CodegenError(f'unsupported binary op: {expr.op}')

        self._emit_symbol_ref(Opcode.CMP, tmp_name)
        if expr.op == '==':
            branch = Opcode.BEQ
        elif expr.op == '!=':
            branch = Opcode.BNE
        elif expr.op == '<':
            branch = Opcode.BLT
        elif expr.op == '<=':
            branch = Opcode.BLE
        elif expr.op == '>':
            branch = Opcode.BGT
        else:
            branch = Opcode.BGE

        branch_true = self._compile_branch(branch)
        self._compile_primary(Instruction(Opcode.LDI, 0))
        branch_end = self._compile_branch(Opcode.JMP)
        self._patch_branch(branch_true, self._ip())
        self._compile_primary(Instruction(Opcode.LDI, 1))
        self._patch_branch(branch_end, self._ip())

    def _patch_branch(self, index: int, target: int):
        self.instructions[index].operand = target

    def _compile_branch(self, branch) -> int:
        return self._compile_primary(Instruction(branch, 0))

    def _compile_unary(self, expr: UnaryExpr):
        if expr.op in ('++', '--'):
            if not isinstance(expr.expr, Identifier):
                raise CodegenError('increment/decrement supports only variables')
            name = expr.expr.name
            tmp_name = self._tmp_name()
            self._compile_primary(Instruction(Opcode.LDI, 1))
            self._emit_symbol_ref(Opcode.ST, tmp_name)
            self._emit_symbol_ref(Opcode.LD, name)
            opcode = Opcode.ADD if expr.op == '++' else Opcode.SUB
            self._emit_symbol_ref(opcode, tmp_name)
            self._emit_symbol_ref(Opcode.ST, name)
            return

        self._compile_expression(expr.expr)
        if expr.op == '-':
            self._compile_primary(Instruction(Opcode.NEG))
            return
        if expr.op == '!':
            self._compile_primary(Instruction(Opcode.NOT))
            return
        raise CodegenError(f'unsupported unary op: {expr.op}')

    def _compile_lit(self, lit):
        match lit.literal_type:
            case 'INT_LIT':
                self._compile_primary(Instruction(Opcode.LDI, lit.value))
            case 'FLOAT_LIT':
                self._compile_primary(Instruction(Opcode.LDI, int(lit.value)))
            case 'BOOL_LIT':
                self._compile_primary(Instruction(Opcode.LDI, 1 if lit.value else 0))
            case 'STRING_LIT':
                name = self._allocate_cstr(lit.value)
                self._emit_symbol_ref(Opcode.LDI, name)

    def _compile_primary(self, instruction) -> int:
        self.instructions.append(instruction)
        return len(self.instructions) - 1

    def _emit_symbol_ref(self, opcode: Opcode, name: str) -> int:
        index = self._compile_primary(Instruction(opcode, 0))
        self.symbol_patches.append(_Patch(index, name))
        return index

    def _store(self, name: str) -> None:
        if name not in self.symbols:
            self._allocate(name)
        self._emit_symbol_ref(Opcode.ST, name)
