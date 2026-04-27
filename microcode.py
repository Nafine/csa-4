def encode_signals(halted=0,
                   acc_l=0, sp_l=0, ip_l=0, cr_l=0, ar_l=0, mem_w=0,
                   ar_sel=0, ip_sel=0, alu_left=0, alu_right=0,
                   alu=0, cond=0, next_addr=0):
    return (
            (halted & 1) << 25 |
            (acc_l & 1) << 24 |
            (sp_l & 1) << 23 |
            (ip_l & 1) << 22 |
            (cr_l & 1) << 21 |
            (ar_l & 1) << 20 |
            (mem_w & 1) << 19 |
            (ar_sel & 0b11) << 17 |
            (ip_sel & 1) << 16 |
            (alu_left & 0b11) << 14 |
            (alu_right & 0b11) << 12 |
            (alu & 0b111) << 9 |
            (cond & 0b111) << 6 |
            (next_addr & 0b111111)
    )


UOPS = [0] * 64

# FETCH
UOPS[0] = encode_signals(alu_right=0b11, cr_l=1) # Mem[AR] -> CR
UOPS[1] = encode_signals(alu=0b100, ip_l=1) # IP++

# LOAD: AC <- Mem[arg]
UOPS[2] = encode_signals(ar_sel=0b01, ar_l=1)                              # AR <- CR.arg
UOPS[3] = encode_signals(alu_right=0b11, acc_l=1, cond=0b001, next_addr=0) # AC <- Mem[AR]; -> FETCH

# STORE: Mem[arg] <- AC
UOPS[4] = encode_signals(ar_sel=0b01, ar_l=1)                              # AR <- CR.arg
UOPS[5] = encode_signals(mem_w=1, cond=0b001, next_addr=0)                 # Mem[AR] <- AC; -> FETCH