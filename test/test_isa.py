"""Тесты микрокоманд CSA-4.

Не покрыты:
- BEQ/BNE/BGE/BLT — next_addr=20 в MROM[28..31] явно неверный (должен быть JMP),
  и при cond=false происходит mp+1 в случайный uop. Сначала надо починить микрокод.
- POP — MROM[35] = encode_signals() пустая, ACC не загружается, нет возврата в FETCH.
"""

from machine import ControlUnit, to_signed32

MASK_32 = 0xFFFFFFFF


def test_fetch():
    cu = ControlUnit(log_path='log/trace_fetch.log')
    cu.dp.data_mem[0] = 0xDEADBEEF
    for _ in range(3):
        cu.step()
    assert cu.dp.cr == 0xDEADBEEF, f'CR={cu.dp.cr:#x}'
    assert cu.dp.ip == 1, f'IP={cu.dp.ip}'
    cu.log.close()


def test_load():
    cu = ControlUnit(log_path='log/trace_load.log')
    cu.dp.data_mem[0] = 0x01000010  # LD 0x10
    cu.dp.data_mem[0x10] = 0xCAFE
    for _ in range(6):  # FETCH 3 + LOAD 3
        cu.step()
    assert cu.dp.acc == 0xCAFE, f'ACC={cu.dp.acc:#x}'
    assert cu.dp.ar == 0x10, f'AR={cu.dp.ar:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_ldi():
    cu = ControlUnit(log_path='log/trace_ldi.log')
    cu.dp.data_mem[0] = 0x02000040  # LDI #0x40
    for _ in range(4):  # FETCH 3 + LDI 1
        cu.step()
    assert cu.dp.acc == 0x40, f'ACC={cu.dp.acc:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_store():
    cu = ControlUnit(log_path='log/trace_store.log')
    cu.dp.data_mem[0] = 0x03000020  # ST 0x20
    cu.dp.acc = 0xBEEF
    for _ in range(5):  # FETCH 3 + STORE 2
        cu.step()
    assert cu.dp.data_mem[0x20] == 0xBEEF, f'mem[0x20]={cu.dp.data_mem[0x20]:#x}'
    assert cu.dp.ar == 0x20, f'AR={cu.dp.ar:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_add():
    cu = ControlUnit(log_path='log/trace_add.log')
    cu.dp.data_mem[0] = 0x10000020  # ADD 0x20
    cu.dp.data_mem[0x20] = 0xBEEF
    cu.dp.acc = 0
    for _ in range(6):  # FETCH 3 + ADD 3
        cu.step()
    assert cu.dp.acc == 0xBEEF, f'ACC={cu.dp.acc:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_sub():
    cu = ControlUnit(log_path='log/trace_sub.log')
    cu.dp.data_mem[0] = 0x11000020  # SUB 0x20
    cu.dp.data_mem[0x20] = 15
    cu.dp.acc = 0
    for _ in range(6):  # FETCH 3 + SUB 3
        cu.step()
    assert cu.dp.acc == to_signed32(-15) & MASK_32, f'ACC={cu.dp.acc:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_mul():
    cu = ControlUnit(log_path='log/trace_mul.log')
    cu.dp.data_mem[0] = 0x12000020  # MUL 0x20
    cu.dp.data_mem[0x20] = 45
    cu.dp.acc = 3
    for _ in range(6):  # FETCH 3 + MUL 3
        cu.step()
    assert cu.dp.acc == 45 * 3, f'ACC={cu.dp.acc}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_div():
    cu = ControlUnit(log_path='log/trace_div.log')
    cu.dp.data_mem[0] = 0x13000020  # DIV 0x20
    cu.dp.data_mem[0x20] = 4
    cu.dp.acc = 20
    for _ in range(6):  # FETCH 3 + DIV 3
        cu.step()
    assert cu.dp.acc == 5, f'ACC={cu.dp.acc}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_rem():
    cu = ControlUnit(log_path='log/trace_rem.log')
    cu.dp.data_mem[0] = 0x14000020  # REM 0x20
    cu.dp.data_mem[0x20] = 3
    cu.dp.acc = 20
    for _ in range(6):  # FETCH 3 + REM 3
        cu.step()
    assert cu.dp.acc == 20 % 3, f'ACC={cu.dp.acc}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_cmp_eq():
    cu = ControlUnit(log_path='log/trace_cmp.log')
    cu.dp.data_mem[0] = 0x20000020  # CMP 0x20: 10 - 10
    cu.dp.data_mem[0x20] = 10
    cu.dp.acc = 10
    for _ in range(6):  # FETCH 3 + CMP 3
        cu.step()
    assert cu.dp.acc == 10, f'ACC={cu.dp.acc}'  # CMP не меняет ACC
    assert cu.dp.Z == 1, f'Z={cu.dp.Z}'
    assert cu.dp.N == 0, f'N={cu.dp.N}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_jmp():
    cu = ControlUnit(log_path='log/trace_jmp.log')
    cu.dp.data_mem[0] = 0x30000010  # JMP 0x10
    for _ in range(4):  # FETCH 3 + JMP 1
        cu.step()
    assert cu.dp.ip == 0x10, f'IP={cu.dp.ip:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()

def test_push():
    cu = ControlUnit(log_path='log/trace_push.log')
    cu.dp.data_mem[0] = 0x40000000  # PUSH
    cu.dp.acc = 0xBEEF
    sp_before = cu.dp.sp
    for _ in range(5):  # FETCH 3 + PUSH 2
        cu.step()
    assert cu.dp.data_mem[sp_before] == 0xBEEF, f'mem[{sp_before:#x}]={cu.dp.data_mem[sp_before]:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


if __name__ == '__main__':
    tests = [
        test_fetch, test_load, test_ldi, test_store,
        test_add, test_sub, test_mul,
        test_div, test_rem, test_cmp_eq,
        test_jmp, test_push,
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
