from isa import Instruction, Opcode
from machine import ControlUnit


def _load(cu, *instructions, data=None):
    """Кладёт программу с адреса 0 и опциональные значения данных."""
    for i, ins in enumerate(instructions):
        cu.dp.data_mem[i] = ins.to_binary()
    if data:
        for addr, value in data.items():
            cu.dp.data_mem[addr] = value


def test_prog_arith():
    """(5 + 3) - 2 = 6 -> mem[0x12]"""
    cu = ControlUnit(log_path='log/prog_arith.log')
    _load(cu,
          Instruction(Opcode.LDI, 5),  # 0: ACC = 5
          Instruction(Opcode.ADD, 0x10),  # 1: ACC += mem[0x10]
          Instruction(Opcode.SUB, 0x11),  # 2: ACC -= mem[0x11]
          Instruction(Opcode.ST, 0x12),  # 3: mem[0x12] = ACC
          Instruction(Opcode.JMP, 4),  # 4: loop here
          data={0x10: 3, 0x11: 2},
          )
    for _ in range(50):
        cu.step()
    assert cu.dp.data_mem[0x12] == 6, f'mem[0x12]={cu.dp.data_mem[0x12]}'
    cu.log.close()


def test_prog_branch():
    """if ACC == mem[0x10] -> mem[0x12] = 1, иначе 0."""
    cu = ControlUnit(log_path='log/prog_branch.log')
    _load(cu,
          Instruction(Opcode.LDI, 5),  # 0: ACC = 5
          Instruction(Opcode.CMP, 0x10),  # 1: сравнить с mem[0x10]
          Instruction(Opcode.BEQ, 5),  # 2: если equal -> 5
          Instruction(Opcode.LDI, 0),  # 3: not equal
          Instruction(Opcode.JMP, 6),  # 4: пропустить equal-ветку
          Instruction(Opcode.LDI, 1),  # 5: equal
          Instruction(Opcode.ST, 0x12),  # 6
          Instruction(Opcode.JMP, 7),  # 7: loop
          data={0x10: 5},
          )
    for _ in range(60):
        cu.step()
    assert cu.dp.data_mem[0x12] == 1, f'mem[0x12]={cu.dp.data_mem[0x12]}'
    cu.log.close()


def test_prog_call_ret():
    """main: ACC=10, CALL inc, ST mem[0x12].  inc: ACC += mem[0x10]; RET."""
    cu = ControlUnit(log_path='log/prog_call_ret.log')
    _load(cu,
          Instruction(Opcode.LDI, 10),  # 0
          Instruction(Opcode.CALL, 5),  # 1: вызов inc
          Instruction(Opcode.ST, 0x12),  # 2: после возврата
          Instruction(Opcode.JMP, 3),  # 3: loop
          Instruction(Opcode.LDI, 0),  # 4: padding (не выполняется)
          Instruction(Opcode.ADD, 0x10),  # 5: inc: ACC += mem[0x10]
          Instruction(Opcode.RET),  # 6: возврат
          data={0x10: 1},
          )
    for _ in range(60):
        cu.step()
    assert cu.dp.data_mem[0x12] == 11, f'mem[0x12]={cu.dp.data_mem[0x12]}'
    cu.log.close()


def test_prog_stack():
    """PUSH 0xAA; ACC=0x55; ST mem[0x10]; POP; ST mem[0x11]."""
    cu = ControlUnit(log_path='log/prog_stack.log')
    _load(cu,
          Instruction(Opcode.LDI, 0xAA),  # 0
          Instruction(Opcode.PUSH),  # 1
          Instruction(Opcode.LDI, 0x55),  # 2
          Instruction(Opcode.ST, 0x10),  # 3
          Instruction(Opcode.POP),  # 4
          Instruction(Opcode.ST, 0x11),  # 5
          Instruction(Opcode.JMP, 6),  # 6: loop
          )
    for _ in range(60):
        cu.step()
    assert cu.dp.data_mem[0x10] == 0x55, f'mem[0x10]={cu.dp.data_mem[0x10]:#x}'
    assert cu.dp.data_mem[0x11] == 0xAA, f'mem[0x11]={cu.dp.data_mem[0x11]:#x}'
    cu.log.close()


def test_factorial():
    """
    Вычисляет 8! = 40320 рекурсивным способом.
    main:
        CALL fac
        ST mem[0x33]
    fac:
        if n <= 1 return 1
        else return n * fac(n-1)
    """
    cu = ControlUnit(log_path='log/prog_factorial.log')

    _load(cu,
          Instruction(Opcode.LD, 0x32),  # 0: ACC = 5 (загружаем N)
          Instruction(Opcode.CALL, 5),  # 1: вызов функции fac
          Instruction(Opcode.ST, 0x33),  # 2: сохраняем итоговый результат в mem[0x33]
          Instruction(Opcode.JMP, 3),  # 3: бесконечный цикл (остановка программы)
          Instruction(Opcode.HALT),  # 4: padding (выравнивание адресов)

          # ================= fac(n) =================
          # ACC = n
          Instruction(Opcode.CMP, 0x30),  # 5: Сравниваем ACC с 1 (mem[0x30] = 1)
          Instruction(Opcode.BEQ, 15),  # 6: Если n == 1, прыгаем к базовому случаю
          Instruction(Opcode.BLT, 15),  # 7: Если n < 1, прыгаем к базовому случаю

          # Рекурсивный случай: возвращаем n * fac(n-1)
          Instruction(Opcode.PUSH),  # 8: Сохраняем текущее n на стеке
          Instruction(Opcode.SUB, 0x30),  # 9: ACC = n - 1
          Instruction(Opcode.CALL, 5),  # 10: Рекурсивный вызов fac(n-1)
          # После возврата результат fac(n-1) лежит в ACC
          Instruction(Opcode.ST, 0x31),  # 11: Временно сохраняем fac(n-1) в mem[0x31]
          Instruction(Opcode.POP),  # 12: Восстанавливаем сохраненное n обратно в ACC
          Instruction(Opcode.MUL, 0x31),  # 13: ACC = n * fac(n-1)
          Instruction(Opcode.RET),  # 14: Возврат из подпрограммы (ответ в ACC)

          # Базовый случай
          Instruction(Opcode.LDI, 1),  # 15: ACC = 1
          Instruction(Opcode.RET),  # 16: Возврат из подпрограммы

          data={
              0x30: 1,  # Константа 1
              0x31: 0,  # Временная переменная для хранения sub_result
              0x32: 8  # N = 5 (число, факториал которого ищем)
          }
          )

    for _ in range(445):
        cu.step()

    assert cu.dp.data_mem[0x33] == 40320, f'mem[0x33]={cu.dp.data_mem[0x33]}'
    cu.log.close()


if __name__ == '__main__':
    tests = [
        test_prog_arith,
        test_prog_branch,
        test_prog_call_ret,
        test_prog_stack,
        test_factorial
    ]
    failed = []
    for t in tests:
        try:
            t()
            print(f'  OK: {t.__name__}')
        except AssertionError as e:
            print(f'FAIL: {t.__name__}: {e}')
            failed.append(t.__name__)
    print(f'\n{len(tests) - len(failed)}/{len(tests)} passed')
