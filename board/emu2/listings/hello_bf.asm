.data
.org 0x1000
tape:   .space 30000
.code
        JUMP start
        RETI
start:  LOAD X, #tape
        LOAD A, [X]
        ADD #8
        STORE [X], A
        LOAD A, [X]
        TEST #255
        JUMP Z, e1
b1:
        LOAD A, [X+]
        LOAD A, [X]
        ADD #4
        STORE [X], A
        LOAD A, [X]
        TEST #255
        JUMP Z, e2
b2:
        LOAD A, [X+]
        LOAD A, [X]
        ADD #2
        STORE [X], A
        LOAD A, [X+]
        LOAD A, [X]
        ADD #3
        STORE [X], A
        LOAD A, [X+]
        LOAD A, [X]
        ADD #3
        STORE [X], A
        LOAD A, [X+]
        LOAD A, [X]
        ADD #1
        STORE [X], A
        MOVE A, XL
        SUB #4
        MOVE XL, A
        JUMP NC, k3
        MOVE A, XH
        SUB #1
        MOVE XH, A
k3:
        LOAD A, [X]
        SUB #1
        STORE [X], A
        JUMP NZ, b2
e2:
        LOAD A, [X+]
        LOAD A, [X]
        ADD #1
        STORE [X], A
        LOAD A, [X+]
        LOAD A, [X]
        ADD #1
        STORE [X], A
        LOAD A, [X+]
        LOAD A, [X]
        SUB #1
        STORE [X], A
        LOAD A, [X+]
        LOAD A, [X+]
        LOAD A, [X]
        ADD #1
        STORE [X], A
        LOAD A, [X]
        TEST #255
        JUMP Z, e4
b4:
        MOVE A, XL
        SUB #1
        MOVE XL, A
        JUMP NC, k5
        MOVE A, XH
        SUB #1
        MOVE XH, A
k5:
        LOAD A, [X]
        TEST #255
        JUMP NZ, b4
e4:
        MOVE A, XL
        SUB #1
        MOVE XL, A
        JUMP NC, k6
        MOVE A, XH
        SUB #1
        MOVE XH, A
k6:
        LOAD A, [X]
        SUB #1
        STORE [X], A
        JUMP NZ, b1
e1:
        LOAD A, [X+]
        LOAD A, [X+]
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X+]
        LOAD A, [X]
        SUB #3
        STORE [X], A
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X]
        ADD #7
        STORE [X], A
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X]
        ADD #3
        STORE [X], A
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X+]
        LOAD A, [X+]
        LOAD A, [X]
        STORE [LED], A
        MOVE A, XL
        SUB #1
        MOVE XL, A
        JUMP NC, k7
        MOVE A, XH
        SUB #1
        MOVE XH, A
k7:
        LOAD A, [X]
        SUB #1
        STORE [X], A
        LOAD A, [X]
        STORE [LED], A
        MOVE A, XL
        SUB #1
        MOVE XL, A
        JUMP NC, k8
        MOVE A, XH
        SUB #1
        MOVE XH, A
k8:
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X]
        ADD #3
        STORE [X], A
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X]
        SUB #6
        STORE [X], A
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X]
        SUB #8
        STORE [X], A
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X+]
        LOAD A, [X+]
        LOAD A, [X]
        ADD #1
        STORE [X], A
        LOAD A, [X]
        STORE [LED], A
        LOAD A, [X+]
        LOAD A, [X]
        ADD #2
        STORE [X], A
        LOAD A, [X]
        STORE [LED], A
        JUMP $
