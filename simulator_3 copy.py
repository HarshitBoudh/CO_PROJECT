import sys
import os

S_b = 0x00000100
data = 0x00010000
v_halt = "00000000000000000000000001100011"  
prog_mem_len = 64  
# Global state
p_c = 0
is_halted = False
reg = [0] * 32  # x0 to x31 
reg[2] = S_b + 128  # sp top stak
prog_mem = ["0" * 32 for _ in range(prog_mem_len)]  
data_mem = [0] * 32  
stack_mem = [0] * 32  

def increase():
    global p_c
    p_c += 4

def dec_to_bin(num, bits):
    if num < 0:
        num = (1 << bits) + num  #2's com
    return format(num & ((1 << bits) - 1), f"0{bits}b")

def bin_to_dec(bin_str):
    if bin_str[0] == '1':  
        return int(bin_str, 2) - (1 << len(bin_str))
    return int(bin_str, 2)

def add(ins):
    rd, rs1, rs2 = map(bin_to_dec, [ins[20:25], ins[12:17], ins[7:12]])
    reg[rd] = reg[rs1] + reg[rs2]
    reg[0] = 0
    increase()

def sub(ins):
    rd, rs1, rs2 = map(bin_to_dec, [ins[20:25], ins[12:17], ins[7:12]])
    reg[rd] = reg[rs1] - reg[rs2]
    reg[0] = 0
    increase()

def slt(ins):
    rd, rs1, rs2 = map(bin_to_dec, [ins[20:25], ins[12:17], ins[7:12]])
    reg[rd] = 1 if reg[rs1] < reg[rs2] else 0
    reg[0] = 0
    increase()

def srl(ins):
    rd, rs1, rs2 = map(bin_to_dec, [ins[20:25], ins[12:17], ins[7:12]])
    reg[rd] = reg[rs1] >> (reg[rs2] & 0x1F)
    reg[0] = 0
    increase()

def or_inst(ins):
    rd, rs1, rs2 = map(bin_to_dec, [ins[20:25], ins[12:17], ins[7:12]])
    reg[rd] = reg[rs1] | reg[rs2]
    reg[0] = 0
    increase()

def and_inst(ins):
    rd, rs1, rs2 = map(bin_to_dec, [ins[20:25], ins[12:17], ins[7:12]])
    reg[rd] = reg[rs1] & reg[rs2]
    reg[0] = 0
    increase()

def lw(ins):
    rd, rs1, imm = map(bin_to_dec, [ins[20:25], ins[12:17], ins[0:12]])
    addr = reg[rs1] + imm
    if data <= addr < data + 128 and addr % 4 == 0:
        reg[rd] = data_mem[(addr - data) // 4]
    else:
        print(f"Error: Invalid memory access (lw) at p_c {p_c}", file=sys.stderr)
        sys.exit(1)
    reg[0] = 0
    increase()

def addi(ins):
    rd, rs1, imm = map(bin_to_dec, [ins[20:25], ins[12:17], ins[0:12]])
    reg[rd] = reg[rs1] + imm
    reg[0] = 0
    increase()

def jalr(ins):
    global p_c
    rd, rs1, imm = map(bin_to_dec, [ins[20:25], ins[12:17], ins[0:12]])
    reg[rd] = p_c + 4
    p_c = (reg[rs1] + imm) & ~1
    reg[0] = 0

def sw(ins):
    rs1, rs2, imm = map(bin_to_dec, [ins[12:17], ins[7:12], ins[0:7] + ins[20:25]])
    addr = reg[rs1] + imm
    if data <= addr < data + 128 and addr % 4 == 0:
        data_mem[(addr - data) // 4] = reg[rs2]
    elif S_b <= addr < S_b + 128 and addr % 4 == 0:
        stack_mem[(addr - S_b) // 4] = reg[rs2]
    else:
        print(f"Invalid memory access {p_c}", file=sys.stderr)
        sys.exit(1)
    reg[0] = 0
    increase()

def beq(ins):
    global p_c
    rs1, rs2, imm = map(bin_to_dec, [ins[12:17], ins[7:12], ins[0:1] + ins[24:25] + ins[1:7] + ins[20:24] + "0"])
    if reg[rs1] == reg[rs2]:
        p_c += imm - 4
    else:
        increase()
    reg[0] = 0

def bne(ins):
    global p_c
    rs1, rs2, imm = map(bin_to_dec, [ins[12:17], ins[7:12], ins[0:1] + ins[24:25] + ins[1:7] + ins[20:24] + "0"])
    if reg[rs1] != reg[rs2]:
        p_c += imm - 4
    else:
        increase()
    reg[0] = 0

def blt(ins):
    global p_c
    rs1, rs2, imm = map(bin_to_dec, [ins[12:17], ins[7:12], ins[0:1] + ins[24:25] + ins[1:7] + ins[20:24] + "0"])
    if reg[rs1] < reg[rs2]:
        p_c += imm - 4
    else:
        increase()
    reg[0] = 0

def jal(ins):
    global p_c
    rd, imm = map(bin_to_dec, [ins[20:25], ins[0:1] + ins[12:20] + ins[11:12] + ins[1:11] + "0"])
    reg[rd] = p_c + 4
    p_c += imm - 4
    reg[0] = 0

def mul(ins):
    rd, rs1, rs2 = map(bin_to_dec, [ins[20:25], ins[12:17], ins[7:12]])
    reg[rd] = reg[rs1] * reg[rs2]
    reg[0] = 0
    increase()

def rst(ins):
    reg[1:] = [0] * 31  # Reset all except x0
    increase()

def halt(ins):
    global is_halted
    is_halted = True

def rvrs(ins):
    rd, rs1 = map(bin_to_dec, [ins[20:25], ins[12:17]])
    reg[rd] = int(dec_to_bin(reg[rs1], 32)[::-1], 2)
    reg[0] = 0
    increase()

# ins dictionary
dict_ins = {
    "0110011_000_0000000": add,    # R : add
    "0110011_000_0100000": sub,    # R : sub
    "0110011_010_0000000": slt,    # R : slt
    "0110011_101_0000000": srl,    # R : srl
    "0110011_110_0000000": or_inst,# R : or
    "0110011_111_0000000": and_inst,# R : and
    "0000011_010": lw,             # I : lw
    "0010011_000": addi,           # I : addi
    "1100111_000": jalr,           # I : jalr
    "0100011_010": sw,             # S : sw
    "1100011_000": beq,            # B : beq
    "1100011_001": bne,            # B : bne
    "1100011_100": blt,            # B : blt
    "1101111": jal,                # J: jal
    #bonus
    "1000001": mul,                #  mul
    "1000010": rst,                #  rst
    "1000011": halt,               #  halt
    "1000100": rvrs                #  rvrs
}

def main():
    global prog_mem, is_halted, p_c

    if len(sys.argv) != 3:
        print("Usage: python3 Simulator.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.", file=sys.stderr)
        sys.exit(1)

    p_c = 0
    is_halted = False
    reg[0] = 0
    reg[2] = S_b + 128
    prog_mem = ["0" * 32 for _ in range(prog_mem_len)]  

    with open(input_file, "r") as fobj:
        commands = [line.strip() for line in fobj.readlines() if line.strip()]
        for i, line in enumerate(commands[:prog_mem_len]):
            if len(line) != 32 or not all(c in "01" for c in line):
                print(f"Error: Invalid ins at line {i+1}", file=sys.stderr)
                sys.exit(1)
            prog_mem[i] = line
        if not commands or commands[-1] != v_halt:
            print("Error: Missing or misplaced Virtual Halt", file=sys.stderr)
            sys.exit(1)

    with open(output_file, "w") as fobj2:
        while not is_halted and 0 <= p_c // 4 < prog_mem_len:
            ins = prog_mem[p_c // 4]
            if ins == v_halt:
                is_halted = True
            else:
                op_code = ins[25:32]
                funct3 = ins[17:20] if op_code in ["0110011", "0000011", "0010011", "1100111", "0100011", "1100011"] else ""
                funct7 = ins[0:7] if op_code == "0110011" else ""
                key = f"{op_code}_{funct3}_{funct7}" if op_code == "0110011" else f"{op_code}_{funct3}" if funct3 else op_code
                if key in dict_ins:
                    dict_ins[key](ins)
                else:
                    print(f"Error: Unknown ins '{ins}' at p_c {p_c}", file=sys.stderr)
                    sys.exit(1)

            trace = f"{dec_to_bin(p_c, 32)} " + " ".join(dec_to_bin(reg, 32) for reg in reg)
            fobj2.write(trace + "\n")

        for val in data_mem:
            fobj2.write(f"{dec_to_bin(val, 32)}\n")

    print(f"Simulation complete. Output written to '{output_file}'")


main()
