"""Scripted button events per program: name -> (cycles to run, [(cycle, 'press'|'release', button)]).
A key 'prog@variant' runs programs/prog.asm with a different script."""


def tap(cycle, button, hold=25):
    return [(cycle, 'press', button), (cycle + hold, 'release', button)]


SCRIPTS = {
    'counter': (20000, []),
    'life': (60000, []),
    # frame = about 71 cycles, first frame ends near cycle 283. Buttons: 0 up, 1 down, 2 left, 3 right
    'snake': (9000, tap(1530, 1) + tap(2100, 2) + tap(2400, 3)   # 2400: reverse, ignored
                    + tap(2700, 0) + tap(3300, 3) + tap(3700, 1) + tap(4200, 2)),
    'snake@death': (1200, tap(300, 1) + tap(390, 2) + tap(470, 0)),   # 2x2 spiral into its own body
    'pong': (12000, [(400, 'press', 1), (900, 'release', 1), (1500, 'press', 0), (2000, 'release', 0),
                     (3000, 'press', 1), (3300, 'release', 1), (5000, 'press', 0), (5200, 'release', 0)]),
    'scroll': (30000, []),
}
