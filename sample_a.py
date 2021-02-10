import pyxel
import lcl

def update():
    pass

def draw():
    pass


pyxel.init(256,256)
lcl.load("sample.json")     # Lovely Composer Original File Format Only
lcl.play(0)

pyxel.text(8, 8, "Hello, Lovely Composer Library(LCL)!", 6)
pyxel.text(8, 20, lcl.get_sound_state(), 7)

pyxel.run(update, draw)