from machine import ControlUnit, to_signed32

MASK_32 = 0xFFFFFFFF


def _exec_branch(word, log_path, *, Z=None, N=None):
    """FETCH branch-инструкции, выставляем флаги после FETCH,
    докручиваем такты до возврата в FETCH (mp == 0)."""
    cu = ControlUnit(log_path=log_path)
    cu.dp.data_mem[0] = word
    for _ in range(3):  # FETCH
        cu.step()
    if Z is not None:
        cu.dp.Z = Z
    if N is not None:
        cu.dp.N = N
    safety = 0
    while cu.mp != 0 and safety < 20:
        cu.step()
        safety += 1
    return cu


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


def test_beq_taken():
    cu = _exec_branch(0x31000010, 'log/trace_beq_taken.log', Z=1)
    assert cu.dp.ip == 0x10, f'IP={cu.dp.ip:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_beq_not_taken():
    cu = _exec_branch(0x31000010, 'log/trace_beq_not_taken.log', Z=0)
    assert cu.dp.ip == 1, f'IP={cu.dp.ip:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_bne_taken():
    cu = _exec_branch(0x32000010, 'log/trace_bne_taken.log', Z=0)
    assert cu.dp.ip == 0x10, f'IP={cu.dp.ip:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_bne_not_taken():
    cu = _exec_branch(0x32000010, 'log/trace_bne_not_taken.log', Z=1)
    assert cu.dp.ip == 1, f'IP={cu.dp.ip:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_bge_taken():
    cu = _exec_branch(0x33000010, 'log/trace_bge_taken.log', N=0)
    assert cu.dp.ip == 0x10, f'IP={cu.dp.ip:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_bge_not_taken():
    cu = _exec_branch(0x33000010, 'log/trace_bge_not_taken.log', N=1)
    assert cu.dp.ip == 1, f'IP={cu.dp.ip:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_blt_taken():
    cu = _exec_branch(0x34000010, 'log/trace_blt_taken.log', N=1)
    assert cu.dp.ip == 0x10, f'IP={cu.dp.ip:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_blt_not_taken():
    cu = _exec_branch(0x34000010, 'log/trace_blt_not_taken.log', N=0)
    assert cu.dp.ip == 1, f'IP={cu.dp.ip:#x}'
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


def test_pop():
    cu = ControlUnit(log_path='log/trace_pop.log')
    cu.dp.data_mem[0] = 0x41000000  # POP
    sp_before = cu.dp.sp  # 2047
    cu.dp.sp = 2046
    cu.dp.data_mem[2047] = 0x111
    for _ in range(7):
        cu.step()
    assert cu.dp.sp == sp_before, f'SP={cu.dp.sp}'
    assert cu.dp.acc == 0x111, f'ACC={cu.dp.acc:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_call():
    cu = ControlUnit(log_path='log/trace_call.log')
    cu.dp.data_mem[0] = 0x50000010  # CALL 0x10
    sp_before = cu.dp.sp  # 2047
    for _ in range(6):  # FETCH 3 + CALL 3
        cu.step()
    assert cu.dp.data_mem[sp_before] == 1, f'mem[{sp_before:#x}]={cu.dp.data_mem[sp_before]:#x}'
    assert cu.dp.sp == sp_before - 1, f'SP={cu.dp.sp}'
    assert cu.dp.ip == 0x10, f'IP={cu.dp.ip:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_ret():
    cu = ControlUnit(log_path='log/trace_ret.log')
    cu.dp.data_mem[0] = 0x51000000  # RET
    acc_before = cu.dp.acc
    sp_before = cu.dp.sp  # 2047
    cu.dp.sp = 2046
    cu.dp.data_mem[2047] = 0x111
    for _ in range(7):  # FETCH 3 + RET 4
        cu.step()
    assert cu.dp.ip == 0x111, f'IP={cu.dp.ip:#x}'
    assert cu.dp.sp == sp_before, f'SP={cu.dp.sp}'
    assert cu.dp.acc == acc_before, f'ACC={cu.dp.acc:#x}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


def test_call_ret():
    """Интеграционный: CALL по адресу 0, RET по адресу 0x10.
    Должны вернуться к IP=1 (адрес после CALL) с восстановленным SP."""
    cu = ControlUnit(log_path='log/trace_call_ret.log')
    cu.dp.data_mem[0] = 0x50000010  # CALL 0x10
    cu.dp.data_mem[0x10] = 0x51000000  # RET
    sp_before = cu.dp.sp  # 2047
    for _ in range(13):  # FETCH 3 + CALL 3 + FETCH 3 + RET 4
        cu.step()
    assert cu.dp.ip == 1, f'IP={cu.dp.ip:#x}'
    assert cu.dp.sp == sp_before, f'SP={cu.dp.sp}'
    assert cu.mp == 0, f'MP={cu.mp}'
    cu.log.close()


if __name__ == '__main__':
    tests = [
        test_fetch, test_load, test_ldi, test_store,
        test_add, test_sub, test_mul,
        test_div, test_rem, test_cmp_eq,
        test_jmp,
        test_beq_taken, test_beq_not_taken,
        test_bne_taken, test_bne_not_taken,
        test_bge_taken, test_bge_not_taken,
        test_blt_taken, test_blt_not_taken,
        test_push, test_pop, test_call, test_ret, test_call_ret,
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
