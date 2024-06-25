#!usr/bin/env python3

# 8 bits = 1 byte
# 16 bits = 2 bytes

import array
import random
import time
import sdl2.ext


# RAM, 4KB (4096 bytes)
ram = array.array('B')

# 16 registers, 8 bits each
v_registers = array.array('B', [0 for i in range(0, 16)])

# i-register, 16 bits
i_register = 0x0000

# sound and time registers
sound_register = 0x00
time_register = 0x00

# program counter, will be used as ram array index
pc = 0x0000

# stack, array of 16 16-bit values
stack = array.array('H', [0 for i in range(0, 16)])
stack_pointer = 0x00


"""===***instruction set functions***==="""


def clear_screen(texture_object):
    """0x00E0"""
    texture_object.clear()


def return_subroutine():
    """0x00EE"""
    global pc
    global stack_pointer
    pc = stack[-1]
    stack_pointer -= 1


def jump(opcode):
    global pc
    """0x1nnn - JP addr"""
    jump_address = opcode & 0x0FFF
    pc = jump_address


def call_subroutine(opcode):
    """0x2nnn - CALL addr"""
    global stack_pointer
    stack_pointer += 1
    stack[-1] = pc
    jump_address = opcode & 0x0FFF
    pc = jump_address


def skip_next_instruction_bytecheck(opcode):
    """0x3xkk - SE Vx, byte"""
    global pc
    index_x = (opcode & 0x0F00) >> 8
    kk = opcode & 0x00FF
    if v_registers[index_x] == kk:
        pc += 2


def skip_next_instruction_unequalbytecheck(opcode):
    """0x4xkk - SNE Vx, byte"""
    global pc
    index_x = (opcode & 0x0F00) >> 8
    kk = opcode & 0x00FF
    if v_registers[index_x] != kk:
        pc += 2


def skip_next_instruction_equalregister(opcode):
    """0x5xy0 - SE Vx, Vy"""
    global pc
    first_index_x = (opcode & 0x0F00) >> 8
    second_index_y = (opcode & 0x00F0) >> 4
    if v_registers[first_index_x] == v_registers[second_index_y]:
        pc += 2


def store_byte(opcode):
    """0x6xkk - LD Vx, byte"""
    index_x = (opcode & 0x0F00) >> 8
    kk = opcode & 0x00FF
    v_registers[index_x] = kk


def add_byte(opcode):
    """0x7xkk - ADD Vx, byte"""
    index_x = (opcode & 0x0F00) >> 8
    kk = opcode & 0x00FF
    v_registers[index_x] = v_registers[index_x] + kk


def store_register(opcode):
    """0x8xy0 - LD Vx, Vy"""
    first_index_x = (opcode & 0x0F00) >> 8
    second_index_y = (opcode & 0x00F0) >> 4
    v_registers[first_index_x] = v_registers[second_index_y]


def bitwise_or(opcode):
    """0x8xy1 - OR Vx, Vy"""
    first_index_x = (opcode & 0x0F00) >> 8
    second_index_y = (opcode & 0x00F0) >> 4
    v_registers[first_index_x] = v_registers[first_index_x] | v_registers[second_index_y] 
    


def bitwise_and(opcode):
    """0x8xy2 - AND Vx, Vy"""
    first_index_x = (opcode & 0x0F00) >> 8
    second_index_y = (opcode & 0x00F0) >> 4
    v_registers[first_index_x] = v_registers[first_index_x] & v_registers[second_index_y] 


def bitwise_xor(opcode):
    """0x8xy3 - XOR Vx, Vy"""
    first_index_x = (opcode & 0x0F00) >> 8
    second_index_y = (opcode & 0x00F0) >> 4
    v_registers[first_index_x] ^ v_registers[first_index_x] & v_registers[second_index_y]


def add_register(opcode):
    """0x8xy4 - ADD Vx, Vy"""
    first_index_x = (opcode & 0x0F00) >> 8
    second_index_y = (opcode & 0x00F0) >> 4
    v_registers[first_index_x] = v_registers[first_index_x] + v_registers[second_index_y]
    if v_registers[first_index_x] > 255:
        v_registers[0xF] = 1
    else:
        v_registers[0xF] = 0


def subtract_register_vxvy(opcode):
    """0x8xy5 - SUB Vx, Vy"""
    first_index_x = (opcode & 0x0F00) >> 8
    second_index_y = (opcode & 0x00F0) >> 4

    if v_registers[first_index_x] > v_registers[second_index_y]:
        v_registers[0xF] = 1
    else:
        v_registers[0xF] = 0
    
    v_registers[first_index_x] = v_registers[first_index_x] - v_registers[second_index_y]


def shift_right(opcode):
    """0x8xy6 - SHR Vx {, Vy}"""
    pass


def subtract_register_vyvx(opcode):
    """0x8xy7 - SUBN Vx, Vy"""
    first_index_x = (opcode & 0x0F00) >> 8
    second_index_y = (opcode & 0x00F0) >> 4

    if v_registers[second_index_y] > v_registers[first_index_x]:
        v_registers[0xF] = 1
    else:
        v_registers[0xF] = 0
    
    v_registers[first_index_x] = v_registers[second_index_y] - v_registers[first_index_x]


def shift_left(opcode):
    """0x8xyE - SHL Vx {, Vy}:"""
    pass


def skip_next_instruction_unequalregister(opcode):
    """0x9xy0 - SNE Vx, Vy"""
    global pc
    first_index_x = (opcode & 0x0F00) >> 8
    second_index_y = (opcode & 0x00F0) >> 4

    if v_registers[first_index_x] != v_registers[second_index_y]:
        pc += 2 # increase by four?


def set_i_register(opcode):
    """0xAnnn - LD I, addr"""
    nnn = (opcode & 0x0FFF)
    i_register = nnn


def jump_v0_plus_value(opcode):
    """0xBnnn - JP V0, addr"""
    global pc
    nnn = (opcode & 0x0FFF)
    pc = nnn + v_registers[0x0]


def random_byte(opcode):
    """0xCxkk - RND Vx, byte"""
    index_x = (opcode & 0x0F00) >> 8
    kk = opcode & 0x00FF
    v_registers[index_x] = random.randint(0, 255) & kk # maybe replace random.randint() for better randomness


def draw(opcode):
    """0xDxyn - DRW Vx, Vy, nibble"""
    pass


def skip_keypressed(opcode):
    """0xEx9E - SKP Vx"""
    pass


def skip_keynotpressed(opcode):
    """0xExA1 - SKNP Vx"""
    pass


def set_register_delaytimervalue(opcode):
    """0xFx07 - LD Vx, DT"""
    pass


def wait_keypress(opcode):
    """0xFx0A - LD Vx, K"""
    pass


def set_delaytimer_registervalue(opcode):
    """0xFx15 - LD DT, Vx"""
    pass


def set_soundtimer_registervalue(opcode):
    """0xFx18 - LD ST, Vx"""
    pass


def add_register_to_i(opcode):
    """0xFx1E - ADD I, Vx"""
    index_x = (opcode & 0x0F00) >> 8
    i_register = i_register + v_registers[index_x]
    pass


def set_i_sprite(opcode):
    """0xFx29 - LD F, Vx"""
    pass


def set_register_bcd(opcode):
    """0xFx33 - LD B, Vx"""
    pass


def store_registers_memory(opcode):
    """0xFx55 - LD [I], Vx"""
    global ram
    index_x = (opcode & 0x0F00) >> 8
    for i in range(0, index_x):
        ram[i_register + i] = v_registers[i]


def read_registers_memory(opcode):
    """0xFx65 - LD Vx, [I]"""
    global ram
    index_x = (opcode & 0x0F00) >> 8
    for i in range(0, index_x):
        v_registers[i] = ram[i_register + i]


"""===***begin CHIP-8 behavior functions***==="""


"""type 8 instructions begin with 0x8, with last digit as lookup code. Middle two digits are arguments, parsed by referenced function."""

unique_instructions = {
    0x1: jump,
    0x2: call_subroutine,
    0x3: skip_next_instruction_bytecheck,
    0x4: skip_next_instruction_unequalbytecheck,
    0x5: skip_next_instruction_equalregister,
    0x6: store_byte,
    0x7: add_byte,
    0x9: skip_next_instruction_unequalregister,
    0xA: set_i_register,
    0xB: jump_v0_plus_value,
    0xC: random_byte,
    0xD: draw
}

type_8_instructions = {
    0x0: store_register,
    0x1: bitwise_or,
    0x2: bitwise_and,
    0x3: bitwise_xor,
    0x4: add_register,
    0x5: subtract_register_vxvy,
    0x6: shift_right,
    0x7: subtract_register_vyvx,
    0xE: shift_left
}

"""type E instructions begin with 0xE, with lookup code as last two digits. Second digit is the argument."""
type_E_instructions = {
    0xA1: skip_keynotpressed,
    0x9E: skip_keypressed
}

"""type F instructions begin with 0xE, with lookup code as last two digits. Second digit is the argument."""
type_f_instructions = {
    0x07: set_register_delaytimervalue,
    0x0A: wait_keypress,
    0x15: set_delaytimer_registervalue,
    0x18: set_soundtimer_registervalue,
    0x1E: add_register_to_i,
    0x29: set_i_sprite,
    0x33: set_register_bcd,
    0x55: store_registers_memory,
    0x65: read_registers_memory
}


clear_return_instructions = {
    0x0: clear_screen,
    0xE: return_subroutine
}


"""===*** Emulation cycle functions ***==="""


def fetch():
    global ram
    opcode = ram[pc] << 8 | ram[pc+1]
    pc += 2 
    return opcode

def decode(opcode):
    # bitshift right to get instruction code
    instruction_code = (opcode & 0xF000) >> 12

    if instruction_code == 0x8:
        end_digit = opcode & 0x000F # bitmask to get final digit for table lookup
        type_8_instructions[end_digit](opcode)

    elif instruction_code == 0xE:
        end_digits = opcode & 0x00FF
        type_E_instructions[end_digits](opcode)
    
    elif instruction_code == 0xF:
        end_digits = opcode & 0x00FF
        type_f_instructions[end_digits](opcode)

    elif opcode >> 4 == 0x00E:
        end_digit = opcode & 0x000F
        clear_return_instructions[end_digit] # these functions/instructions take no arguments

    else:
        start_digit = (opcode & 0xF000) >> 12
        unique_instructions[start_digit](opcode)


def main():
    # initialize window and renderer
    sdl2.ext.init()
    window = sdl2.ext.Window('CHIPPY', size = (640, 320))
    main_renderer = sdl2.ext.renderer.Renderer(window)
    
