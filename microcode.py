def encode_signals(halted=0,
                   acc_l=0, sp_l=0, ip_l=0, cr_l=0, ar_l=0, mem_w=0,
                   ar_sel=0, ip_sel=0, alu_left=0, alu_right=0,
                   alu=0, cond=0, next_addr=0):
    return (
            (halted & 1) << 24 |
            (acc_l & 1) << 23 |
            (sp_l & 1) << 22 |
            (ip_l & 1) << 21 |
            (cr_l & 1) << 20 |
            (ar_l & 1) << 19 |
            (mem_w & 1) << 18 |
            (ar_sel & 0b11) << 16 |
            (ip_sel & 1) << 15 |
            (alu_left & 1) << 14 |
            (alu_right & 0b11) << 12 |
            (alu & 0b111) << 9 |
            (cond & 0b111) << 6 |
            (next_addr & 0b111111)
    )

UOPS = [0] * 64

# FETCH
UOPS[0] = encode_signals()