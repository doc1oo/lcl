import pyxel
import lcl

def update():
    pass

def draw():
    pass


pyxel.init(256,256)
lcl.load("sample.json")
lcl.play(0, load_channels=2, load_pages=8)

pyxel.text(8, 8, "Saving Pyxel sound ! ( load_channels=2, load_pages=8 )", 6)
pyxel.text(8, 20, lcl.get_sound_state(), 7)

pyxel.run(update, draw)