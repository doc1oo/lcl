import pyxel
import lcl

def update():
    pass

def draw():
    pass


pyxel.init(256,256)
lcl.load("sample.json")
lcl.play(9, load_to_tail=False, load_channels=3, load_pages=8,  loop=False)

pyxel.text(8, 8, "sound load to 0 - xx!", 6)
pyxel.text(8, 20, lcl.get_sound_state(), 7)

pyxel.run(update, draw)