; LCD helpers (macros: each use expands to 2 words, STORE cannot take a constant source).
.macro LCDCMD
        LOAD A, #\1
        STORE [LCD_CMD], A
.endm
.macro LCDBYTE
        LOAD A, #\1
        STORE [LCD_DATA], A
.endm
