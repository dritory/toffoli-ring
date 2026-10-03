; Counter on the LED port: +1 on every 60 Hz tick.
.data
n:      .byte 0
.code
        JUMP start
        RETI                    ; interrupt vector (unused)
start:
wait:   LOAD A, [FRAME]
        TEST #1                 ; AND, flags only
        JUMP Z, wait
        LOAD A, [n]
        ADD #1
        STORE [n], A
        STORE [LED], A
        JUMP wait
