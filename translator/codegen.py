from dataclasses import dataclass

from isa import Instruction, Opcode
from machine import DataPath
from translator.parser import (
    AssignStmt,
    BinaryExpr,
    ExprStmt,
    FuncCall,
    FuncDecl,
    Identifier,
    IfStmt,
    Literal,
    Program,
    ReturnStmt,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)


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
        self.string_symbols: set[str] = set()
        self.scope_stack: list[str] = []
        self.scope_counter: int = 0
        self.function_decls: dict[str, FuncDecl] = {}

    def generate(self, program: Program) -> tuple[list[Instruction], list[int]]:
        main_decl: FuncDecl | None = None

        for node in program.top_levels:
            if isinstance(node, VarDecl):
                self._compile_top_var_decl(node)
            elif isinstance(node, FuncDecl):
                self.function_decls[node.name] = node
                if node.name == 'main':
                    main_decl = node
            else:
                raise CodegenError(f'unsupported top-level node: {type(node).__name__}')

        if main_decl is None:
            raise CodegenError('missing main() entrypoint')

        jmp_main = self._compile_branch(Opcode.JMP)

        for fname, fdecl in self.function_decls.items():
            for p in fdecl.params:
                self._allocate(f'{fname}.{p.name}')
                if p.param_type == 'string':
                    self.string_symbols.add(f'{fname}.{p.name}')

        for fname, fdecl in self.function_decls.items():
            if fname == 'main':
                continue
            self.symbols[fname] = _Symbol('function', self._ip())
            self._enter_scope(fname)
            self._compile_block(fdecl.body)
            self._exit_scope()
            self._compile_primary(Instruction(Opcode.RET))

        main_addr = self._ip()
        self.symbols[main_decl.name] = _Symbol('function', main_addr)
        self._patch_branch(jmp_main, main_addr)

        self._enter_scope('main')
        self._compile_block(main_decl.body)
        self._exit_scope()
        self._compile_primary(Instruction(Opcode.HALT))

        self._resolve_symbols()

        return list(self.instructions), list(self.data)

    def _ip(self) -> int:
        return len(self.instructions)

    def _emit_symbol_ref(self, opcode: Opcode, name: str) -> int:
        index = self._compile_primary(Instruction(opcode, 0))
        self.symbol_patches.append(_Patch(index, name))
        return index

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

    def _qualify(self, name: str) -> str:
        if not self.scope_stack:
            return name
        return '.'.join(self.scope_stack) + '.' + name

    def _resolve(self, name: str) -> str:
        for i in range(len(self.scope_stack), 0, -1):
            prefix = '.'.join(self.scope_stack[:i])
            candidate = f'{prefix}.{name}'
            if candidate in self.symbols:
                return candidate
        return name

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

    def _enter_scope(self, name: str | None = None):
        if name is None:
            name = f'scope_{self.scope_counter}'
            self.scope_counter += 1
        self.scope_stack.append(name)

    def _exit_scope(self) -> None:
        self.scope_stack.pop()

    def _compile_block(self, block):
        self._enter_scope()
        for stmt in block.stmts:
            self._compile_stmt(stmt)
        self._exit_scope()

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
        resolved = self._resolve(assign.name)
        if resolved not in self.symbols:
            raise CodegenError(f'assignment to undeclared variable: {assign.name}')
        self._compile_expression(assign.expr)
        self._emit_symbol_ref(Opcode.ST, resolved)

    def _compile_top_var_decl(self, decl: VarDecl) -> None:
        if decl.expr is None:
            self._allocate(decl.name)
            self._tag_if_string(decl)
            return
        if isinstance(decl.expr, Literal) and decl.expr.literal_type in ('INT_LIT', 'BOOL_LIT'):
            self._allocate(decl.name, self._literal_to_int(decl.expr))
            return
        self._compile_var_decl(decl)

    def _compile_var_decl(self, decl: VarDecl) -> None:
        qualified = self._qualify(decl.name)
        self._allocate(qualified)
        self._tag_if_string(decl)
        if decl.expr is None:
            return
        self._compile_expression(decl.expr)
        self._emit_symbol_ref(Opcode.ST, qualified)

    def _tag_if_string(self, decl: VarDecl) -> None:
        is_string = decl.var_type == 'string'
        if not is_string and isinstance(decl.expr, Identifier):
            is_string = self._resolve(decl.expr.name) in self.string_symbols
        if is_string:
            self.string_symbols.add(self._qualify(decl.name))

    @staticmethod
    def _literal_to_int(lit: Literal) -> int:
        if lit.literal_type == 'INT_LIT':
            return int(lit.value)
        if lit.literal_type == 'FLOAT_LIT':
            return int(lit.value)
        if lit.literal_type == 'BOOL_LIT':
            return 1 if lit.value else 0
        raise CodegenError(f'cannot statically materialize literal type: {lit.literal_type}')

    def _tmp_name(self) -> str:
        name = '$tmp'
        if name not in self.symbols:
            self._allocate(name)
        return name

    def _print_ptr_name(self) -> str:
        name = '$print_ptr'
        if name not in self.symbols:
            self._allocate(name)
        return name

    def _one_name(self) -> str:
        name = '$one'
        if name not in self.symbols:
            self._allocate(name, value=1)
        return name

    def _peek_tmp_name(self) -> str:
        name = '$peek_tmp'
        if name not in self.symbols:
            self._allocate(name)
        return name

    def _poke_val_name(self) -> str:
        name = '$poke_val'
        if name not in self.symbols:
            self._allocate(name)
        return name

    def _poke_addr_name(self) -> str:
        name = '$poke_addr'
        if name not in self.symbols:
            self._allocate(name)
        return name

    def _emit_print_string_loop(self) -> None:
        ptr = self._print_ptr_name()
        one = self._one_name()
        self._emit_symbol_ref(Opcode.ST, ptr)
        loop_start = self._ip()
        self._emit_symbol_ref(Opcode.LDR, ptr)
        jz_end = self._compile_branch(Opcode.BEQ)
        self._compile_primary(Instruction(Opcode.ST, DataPath.OUTPUT_ADDR))
        self._emit_symbol_ref(Opcode.LD, ptr)
        self._emit_symbol_ref(Opcode.ADD, one)
        self._emit_symbol_ref(Opcode.ST, ptr)
        back = self._compile_branch(Opcode.JMP)
        self._patch_branch(back, loop_start)
        self._patch_branch(jz_end, self._ip())

    def _compile_expression(self, expr) -> None:
        if isinstance(expr, Literal):
            self._compile_lit(expr)
            return
        if isinstance(expr, Identifier):
            self._emit_symbol_ref(Opcode.LD, self._resolve(expr.name))
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
                self._emit_symbol_ref(Opcode.LDI, name)
                self._emit_print_string_loop()
                return
            if isinstance(arg, Identifier) and self._resolve(arg.name) in self.string_symbols:
                self._emit_symbol_ref(Opcode.LD, self._resolve(arg.name))
                self._emit_print_string_loop()
                return
            self._compile_expression(arg)
            self._compile_primary(Instruction(Opcode.ST, DataPath.OUTPUT_ADDR))
            return
        elif call.name == 'read':
            if call.args:
                raise CodegenError('read() expects zero arguments')
            self._compile_primary(Instruction(Opcode.LD, DataPath.INPUT_ADDR))
            return
        elif call.name == 'peek':
            if len(call.args) != 1:
                raise CodegenError('peek() expects exactly one argument')
            tmp = self._peek_tmp_name()
            self._compile_expression(call.args[0])
            self._emit_symbol_ref(Opcode.ST, tmp)
            self._emit_symbol_ref(Opcode.LDR, tmp)
            return
        elif call.name == 'poke':
            if len(call.args) != 2:
                raise CodegenError('poke() expects exactly two arguments')
            val_slot = self._poke_val_name()
            addr_slot = self._poke_addr_name()
            self._compile_expression(call.args[1])
            self._emit_symbol_ref(Opcode.ST, val_slot)
            self._compile_expression(call.args[0])
            self._emit_symbol_ref(Opcode.ST, addr_slot)
            self._emit_symbol_ref(Opcode.LD, val_slot)
            self._emit_symbol_ref(Opcode.STR, addr_slot)
            return

        func = self.function_decls.get(call.name)
        if func is None:
            raise CodegenError(f'unknown function: {call.name}')
        if len(call.args) != len(func.params):
            raise CodegenError(
                f'{call.name}: expected {len(func.params)} args, got {len(call.args)}'
            )

        for arg, param in zip(call.args, func.params, strict=True):
            self._compile_expression(arg)
            self._emit_symbol_ref(Opcode.ST, f'{call.name}.{param.name}')

        self._emit_symbol_ref(Opcode.CALL, call.name)

    def _compile_binary(self, expr: BinaryExpr) -> None:
        if expr.op == '&&':
            self._compile_logical_and(expr)
            return
        if expr.op == '||':
            self._compile_logical_or(expr)
            return

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

    def _compile_logical_and(self, expr: BinaryExpr) -> None:
        self._compile_expression(expr.left)
        sc_false_left = self._compile_branch(Opcode.BEQ)
        self._compile_expression(expr.right)
        sc_false_right = self._compile_branch(Opcode.BEQ)
        self._compile_primary(Instruction(Opcode.LDI, 1))
        end = self._compile_branch(Opcode.JMP)
        false_label = self._ip()
        self._compile_primary(Instruction(Opcode.LDI, 0))
        self._patch_branch(sc_false_left, false_label)
        self._patch_branch(sc_false_right, false_label)
        self._patch_branch(end, self._ip())

    def _compile_logical_or(self, expr: BinaryExpr) -> None:
        self._compile_expression(expr.left)
        sc_true_left = self._compile_branch(Opcode.BNE)
        self._compile_expression(expr.right)
        sc_true_right = self._compile_branch(Opcode.BNE)
        self._compile_primary(Instruction(Opcode.LDI, 0))
        end = self._compile_branch(Opcode.JMP)
        true_label = self._ip()
        self._compile_primary(Instruction(Opcode.LDI, 1))
        self._patch_branch(sc_true_left, true_label)
        self._patch_branch(sc_true_right, true_label)
        self._patch_branch(end, self._ip())

    def _patch_branch(self, index: int, target: int):
        self.instructions[index].operand = target

    def _compile_branch(self, branch) -> int:
        return self._compile_primary(Instruction(branch, 0))

    def _compile_unary(self, expr: UnaryExpr):
        if expr.op in ('++', '--'):
            if not isinstance(expr.expr, Identifier):
                raise CodegenError('increment/decrement supports only variables')
            name = self._resolve(expr.expr.name)
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
                self._compile_int(int(lit.value))
            case 'BOOL_LIT':
                self._compile_primary(Instruction(Opcode.LDI, 1 if lit.value else 0))
            case 'STRING_LIT':
                name = self._allocate_cstr(lit.value)
                self._emit_symbol_ref(Opcode.LDI, name)

    def _compile_int(self, value: int) -> None:
        if 0 <= value < (1 << 24):
            self._compile_primary(Instruction(Opcode.LDI, value))
            return
        name = self._intern_const(value)
        self._emit_symbol_ref(Opcode.LD, name)

    def _intern_const(self, value: int) -> str:
        name = f'$const:{value & 0xFFFFFFFF}'
        if name not in self.symbols:
            self._allocate(name, value & 0xFFFFFFFF)
        return name

    def _compile_primary(self, instruction) -> int:
        self.instructions.append(instruction)
        return len(self.instructions) - 1
