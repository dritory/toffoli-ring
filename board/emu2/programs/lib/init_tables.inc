; Start-up routine: the CPU fills the four LOOKUP tables through the write ports TBL0..TBL3.
; Table address = operand<<8 | A, so one pass over b (outer) and a (inner) writes every table
; in order; each port auto-increments and wraps to 0 after 65536 writes.
; Call once with interrupts off.  Destroys A, C.  Costs about 17 cycles per entry (1.1 M clocks).
.data
_t_b:   .byte 0
_t_lo:  .byte 0
_t_hi:  .byte 0
_t_q:   .byte 0
_t_r:   .byte 0
.code
init_tables:
        LOAD A, #0
        STORE [_t_b], A
_t_row: LOAD A, #0
        STORE [_t_lo], A
        STORE [_t_hi], A
        STORE [_t_r], A
        LOAD A, [_t_b]
        CMP #0                  ; divide by zero row: quotient 255, remainder = A
        LOAD A, #0
        JUMP NZ, _t_q0
        LOAD A, #255
_t_q0:  STORE [_t_q], A
        LOAD C, #0              ; DJNZ from 0 counts 256 entries
_t_in:  LOAD A, [_t_lo]
        STORE [TBL0], A         ; MUL   = low byte of a*b
        ADD [_t_b]              ; lo += b, carry out
        STORE [_t_lo], A
        LOAD A, [_t_hi]
        STORE [TBL1], A         ; MULH  = high byte
        ADC #0                  ; hi += carry
        STORE [_t_hi], A
        LOAD A, [_t_q]
        STORE [TBL2], A         ; DIV
        LOAD A, [_t_r]
        STORE [TBL3], A         ; MOD
        ADD #1                  ; r + 1
        CMP [_t_b]              ; reached b? then r = 0 and q + 1
        JUMP NZ, _t_nr
        LOAD A, [_t_q]
        ADD #1
        STORE [_t_q], A
        LOAD A, #0
_t_nr:  STORE [_t_r], A
        DJNZ _t_in
        LOAD A, [_t_b]
        ADD #1
        STORE [_t_b], A
        JUMP NZ, _t_row
        RET
