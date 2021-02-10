import os
import json
import copy
import pyxel
import pyxel.core as core
import lcl
import dataclasses
from dataclasses import *
from typing import MutableSequence
from typing import Any, Callable, Dict, List, Optional
from logging import debug, info, warning, error

NOTEKEY_NAME_LIST = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
DOREMI_NAME_LIST = ["Do", "Do#","Re","Re#", "Mi", "Fa","Fa#", "So","So#", "Ra","Ra#", "Si"]
TONE_NAME_LIST = ["T","S","P","N"]
VOLUME_NAME_LIST = ["0","1","2","3","4","5","6","7"]
EFFECT_NAME_LIST = ["N","S","V","F"]
MAX_SOUND_LENGTH = 32#48
MAX_MUSIC_NUM = 32
SFX_DEFAULT_CH = 10-1
MAX_MUSIC_LENGTH = 16
MAX_BAR_LENGTH = 16

lcjson = None
lcd = None
lcm = None
loaded_lcmusic_index = 0


# Lovely Composer Data Class -------------------------

@dataclass
class AppSettings:
    pianoroll_display_mode = False

    def __post_init__(self):
        pass

@dataclass
class Code:
    note: int = None#dataclasses.field(default=None)
    type: int = None

    def clear(self):
        self.note = None
        self.type = None

@dataclass
class CodeList(MutableSequence):
    codes:list =  dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.codes = []
        for i in range(32):
            self.codes.append(Code())
    
    def get_code_state(self, index):
        return self.codes[index]

    def __getitem__(self, index):
        return self.codes[index]

    def __setitem__(self, index, val):
        if type(val) is Code:
            self.codes[index] = val

    def __delitem__(self, index):
        del self.codes[index]

    def insert(self, index, val):
        if type(val) is LCVoice:
            self.codes.insert(index, val)

    def clear(self):
        for i in range(len(self.codes)):
            self.codes[i].clear()
            #self.set_voice(i, LCVoice())


@dataclass
class LCRhythm:
    codes:CodeList = dataclasses.field(default_factory=list)
    enable_drum:bool = True
    enable_base:bool = True
    enable_melody:bool = True

    @property
    def drum(self):
        return self.enable_drum
    @drum.setter
    def drum(self, val):
        if type(val) is bool:
            self.enable_drum = val

    @property
    def base(self):
        return self.enable_base
    @base.setter
    def base(self, val):
        if type(val) is bool:
            self.enable_base = val

    @property
    def melody(self):
        return self.enable_melody
    @melody.setter
    def melody(self, val):
        if type(val) is bool:
            self.enable_melody = val

    def clear(self):
        for i in range(len(self.codes)):
            self.codes[i].clear()
        self.enable_drum = True
        self.enable_base = True
        self.enable_melody = True

@dataclass
class LCRhythmList(MutableSequence):
    rhythms:list = dataclasses.field(default_factory=list)

    def __getitem__(self, index):
        return self.rhythms[index]

    def __setitem__(self, index, val):
        if type(val) is Code:
            self.rhythms[index] = val

    def __delitem__(self, index):
        del self.rhythms[index]

    def insert(self, index, val):
        if type(val) is LCVoice:
            self.rhythms.insert(index, val)

    def clear(self):
        for i in range(len(self.rhythms)):
            self.rhythms[i].clear()
            #self.set_voice(i, LCVoice())

    def __len__(self):
        return len(self.rhythms)


@dataclass
class LCVoice:
    n: int = None#dataclasses.field(default=None) note
    t: int = 0#field(default=0) tone
    v: int = 5#dataclasses.field(default=5) volume
    f: int = 0#dataclasses.field(default=0) effect
    id: int = None

    #def __init__(self):
    #    pass
    
    def __post_init__(self):
        if type(self.n) is str:
            self.set_by_str(self.n)
    
    def set_voice(self, v):
        self.id = v.id
        self.n = v.n
        self.t = v.t
        self.v = v.v
        self.f = v.f

    def set_note_by_name(self, name):
        self.n = lcl.get_note_num(name)
    
    def set_tone_by_char(self, name):
        res = lcl.get_tone_num(name)
        if res is None:
            return
        self.t = res

    def set_volume_by_char(self, name):
        res = lcl.get_volume_num(name)
        if res is None:
            return
        self.v = res

    def set_effect_by_char(self, name):
        res = lcl.get_effect_num(name)
        if res is None:
             return
        self.f = res

    def set_by_str(self, formated_str):
        formated_str = formated_str.upper()
        vl = formated_str.split(":")
        if len(vl)>=1:
            self.set_note_by_name(vl[0])
        if len(vl)>=2:
            prop_str = vl[1]
            if len(prop_str)>=1:
                self.set_tone_by_char(prop_str[0])
            if len(prop_str)>=2:
                self.set_volume_by_char(prop_str[1])
            if len(prop_str)>=3:
                self.set_effect_by_char(prop_str[2])
        if len(vl)>=4:
            self.id = int(vl[3])


    def clear(self):
        self.id = None
        self.n = None
        self.t = 0
        self.v = 0
        self.f = 0

    def is_clear(self):
        return self.n is None 

    def note_name(self):
        return lcl.get_note_name(self.n)

    def tone_char(self):
        return lcl.get_tone_name(self.t)

    def volume_char(self):
        return lcl.get_volume_name(self.v)

    def effect_char(self):
        return lcl.get_effect_name(self.f)

    def voice_name(self):
        return self.note_name() + ":" + self.tone_char() + self.volume_char() + self.effect_char()

    def __repr__(self):
        return "LCVoice(" + self.voice_name() + ")"


@dataclass
class LCSound(MutableSequence):
    #vl:LCVoiceList = None#dataclasses.field(default_factory=list)
    vl:list = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.set_size(MAX_SOUND_LENGTH)

    def set_size(self, size):
        self.vl.clear()
        for i in range(size):
            self.vl.append(LCVoice())

    def get_voice(self, tick):
        if tick < len(self.vl):
            return self.vl[tick]

    def set_voice(self, tick, voice):
        if tick < len(self.vl):
            self.vl[tick].set_voice(voice)
    
    def set_note_to_all(self, val):
        for v in self.vl:
            v.n = val

    def set_tone_to_all(self, val):
        for v in self.vl:
            v.t = val

    def set_volume_to_all(self, val):
        for v in self.vl:
            v.v = val

    def set_effect_to_all(self, val):
        for v in self.vl:
            v.f = val

    def add_voice(self, voices):
        self.vl += voices

    def add_voices(self, voices):
        self.vl += voices

    def set_notes_by_str(self, s):
        for i,x in enumerate(s):
            self.vl[i].set_note_by_name(x)

    def set_tones_by_str(self, s):
        for i,x in enumerate(s):
            self.vl[i].set_tone_by_char(x)

    def set_volumes_by_str(self, s):
        for i,x in enumerate(s):
            self.vl[i].set_volume_by_char(x)

    def set_effects_by_str(self, s):
        for i,x in enumerate(s):
            self.vl[i].set_effect_by_char(x)
    
    def _clear_inside(self, voice_list, low, high ):
        for v in voice_list:
            if v.n is not None and v.n >= low and v.n <= high:
                v.clear()
        return voice_list

    def _clear_outside(self, voice_list, low, high ):
        
        for v in voice_list:
            debug(str(v) + " " + str(low) + " " + str(high))
            if v.n is not None and (v.n < low or v.n > high):
                v.clear()
        return voice_list

    def _clear_inside_area(self, start_tick, end_tick, low=None, high=None ):

        if low is None:
            low = 0
        if high is None:
            high = 9999

        notes = self.vl[start_tick:end_tick+1]
        self._clear_inside(notes, low, high)
        debug(str(notes))

    def cut_notes(self, start_tick, end_tick, mode=None, low=None, high=None ):
        if low is None:
            low = 0
        if high is None:
            high = 9999

        # copy
        #new_notes = copy.deepcopy( self.vl[start_tick:end_tick+1] )
        #self._clear_outside(new_notes, low=low, high=high)
        new_notes = self.copy_notes(start_tick, end_tick, mode=mode, low=low, high=high)

        # erace
        self._clear_inside_area(start_tick, end_tick, low=low, high=high)

        return new_notes

    def copy_notes(self, start_tick, end_tick, mode=None, low=None, high=None):
        
        if low is None:
            low = 0
        if high is None:
            high = 9999

        # copy
        new_notes = copy.deepcopy( self.vl[start_tick:end_tick+1] )
        self._clear_outside(new_notes, low=low, high=high)

        return new_notes

    def paste_notes(self, start_tick, notes, mode=None, low=None, high=None):
        
        for i, n in enumerate(notes):
            idx = start_tick + i
            if idx < len(self.vl):
                self.vl[idx] = copy.deepcopy( n )
    
    @property
    def notes(self):
        l = []
        for n in self.vl:
            l.append(n.n)
        return l

    @property
    def tones(self):
        l = []
        for n in self.vl:
            l.append(n.t)
        return l

    @property
    def volumes(self):
        l = []
        for n in self.vl:
            l.append(n.v)
        return l

    @property
    def effects(self):
        l = []
        for n in self.vl:
            l.append(n.f)
        return l

    def notes_str(self):
        s = ""
        for n in self.vl:
            s += n.note_name()
        return s

    def tones_str(self):
        s = ""
        for n in self.vl:
            s += n.tone_char()
        return s

    def volumes_str(self):
        s = ""
        for n in self.vl:
            s += n.volume_char()
        return s

    def effects_str(self):
        s = ""
        for n in self.vl:
            s += n.effect_char()
        return s
    
    def set_voices(self, voices):
        if type(voices) is pyxel.Sound:
            vs = voices[0:len(self.vl)]
            for v in vs:
                self.set_voice(v)
            #for i in range(32-len(vs)):
            #    vs.append(Voice())
            #self.vl = voices

    def set_voice_by_index(self, index, voice):
        self.vl[index] = copy.copy(voice)

    def __len__(self):
        return len(self.vl)

    def __getitem__(self, index) -> LCVoice:
        return self.vl[index]

    def __setitem__(self, index, val):
        if type(val) is LCVoice:
            self.vl[index] = val

    def __delitem__(self, index):
        del self.vl[index]

    def insert(self, index, val):
        if type(val) is LCVoice:
            self.vl.insert(index, val)

    def clear(self):
        for i in range(len(self.vl)):
            self.vl[i].clear()
            #self.set_voice(i, LCVoice())

    def __len__(self):
        return len(self.vl)

    def __repr__(self):
        s = "LCSound(vl=["
        l = []
        for v in self.vl:
            l.append(str(v))
        s += ", ".join(l)
        s += "])"
        return s

@dataclass
class LCSoundList(MutableSequence):
    sl:list = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.sl.clear()
        for i in range(16):
            self.sl.append(LCSound())

    def set_voice(self, bar, tick, voice):
        snd = self.sl[bar]
        snd.set_voice(tick, voice)

    def get_voice(self, bar, tick):
        snd = self.sl[bar]
        return snd.get_voice(tick)

    def __getitem__(self, index) -> LCSound:
        return self.sl[index]

    def __setitem__(self, index, val):
        if type(val) is LCVoice:
            self.sl[index] = val

    def __delitem__(self, index):
        del self.sl[index]

    def insert(self, index, val):
        if type(val) is LCVoice:
            self.sl.insert(index, val)

    def clear(self):
        for i in range(len(self.sl)):
            self.sl[i].clear()
            #self.set_voice(i, LCVoice())

    def __len__(self):
        return len(self.sl)

    def __repr__(self):
        return "LCSoundList(sl=" + str(self.sl) + ")"


# manager of 4 Channel
@dataclass
class LCChannelList(MutableSequence):
    channels:list = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.channels = []
        for i in range(pyxel.MUSIC_CHANNEL_COUNT):
            self.channels.append(LCSoundList())
    
    def set_voice(self, ch, bar, tick, voice):
        sl = self.channels[ch]
        sl.set_voice(bar, tick, voice)

    def get_voice(self, ch, bar, tick):
        sl = self.channels[ch]
        return sl.get_voice(bar, tick)

    def clear(self):
        for sl in self.channels:
            sl.clear()

    def __len__(self):
        return len(self.channels)

    def __getitem__(self, index) -> LCSoundList:
        return self.channels[index]

    def __setitem__(self, index, val):
        if type(val) is LCVoice:
            self.channels[index] = val

    def __delitem__(self, index):
        del self.channels[index]

    def insert(self, index, val):
        if type(val) is LCVoice:
            self.channels.insert(index, val)

    def __repr__(self):
        
        s = "LCChannelList(channels=["
        l = []
        for v in self.channels:
            l.append(str(v))

        s += ",\n ".join(l)
        s += "])"
        return s

@dataclass
class LCMusic:
    speed:int = 30
    loop_start_bar:int = None
    loop_end_bar:int = None
    enable_loop:bool = True
    sel_scale_id = 0
    channels:LCChannelList = None#dataclasses.field(default_factory=list) = None
    code_channels:LCChannelList = None
    #channel_ids:list = dataclasses.field(default_factory=list)
    rhythms:LCRhythmList = None
    bars_number_per_page = 1

    def __post_init__(self):
        self.channels = LCChannelList()
        self.code_channels = LCChannelList()
        self.rhythms = LCRhythmList()
        #self.rhythms.clear()

    def clear(self):
        self.speed = 30
        self.sel_scale_id = 0
        self.loop_start_bar = None
        self.loop_end_bar = None
        self.bars_number_per_page = 1
        self.pianoroll_display_mode = 0
        self.channels.clear()
        self.code_channels.clear()
        self.rhythms.clear()
    
    def cut_notes(self, ch, bar, start_tick, end_tick, mode=None, low=None, high=None ):
        snd = self.channels[ch][bar]
        return snd.cut_notes(start_tick, end_tick, mode=mode, low=low, high=high)

    def cut_notes_allch(self, bar, start_tick, end_tick, mode=None, low=None, high=None ):
        tl = []
        for ch_id in range(len(self.channels)):
            notes = self.cut_notes(ch_id, bar, start_tick, end_tick, mode=mode, low=low, high=high)
            tl.append(notes)
        return tl
    
    def copy_notes(self, ch, bar, start_tick, end_tick, mode=None, low=None, high=None):
        snd = self.channels[ch][bar]
        return snd.copy_notes(start_tick, end_tick, mode=mode, low=low, high=high)

    def copy_notes_allch(self, bar, start_tick, end_tick, mode=None , low=None, high=None):
        tl = []
        for ch_id in range(len(self.channels)):
            notes = self.copy_notes(ch_id, bar, start_tick, end_tick, mode=mode, low=low, high=high)
            tl.append(notes)
        return tl

    def paste_notes(self, ch, bar, start_tick, notes, mode=None, low=None, high=None):
        snd = self.channels[ch][bar]
        snd.paste_notes(start_tick, notes, mode=mode, low=low, high=high)

    def paste_notes_allch(self, bar, start_tick, notes_list, mode=None, low=None, high=None ):
        for ch_id in range(len(self.channels)):
            self.paste_notes(ch_id, bar, start_tick, notes_list[ch_id], mode=mode, low=low, high=high)
    
    def import_from_pyxrec(self, file_path, ref_channels):
        return
        if os.path.exists(file_path):
            debug("LCMusic import_pyxel_sounds():")
            load(file_path, False, False, True, True)
            #self.cache_pyxel_sounds()
            #self.cache_pyxel_musics(self._code_music)
        
            # import all sound data
            for i in range(USER_SOUND_BANK_COUNT):
                ch_num = i % MUSIC_CHANNEL_COUNT
                ch_bar = i // MUSIC_CHANNEL_COUNT
                csl = ref_channels[ch_num]
                s = csl[ch_bar]

                for j in range(MAX_SOUND_LENGTH):
                    v = LCVoice()
                    v.n = sound(i).get_note(j)
                    v.t = sound(i).get_tone(j)
                    v.v = sound(i).get_volume(j)
                    v.f = sound(i).get_effect(j)
                    s[j].set_voice(v)

    def load_from_pyxres(self, user_filepath, code_filepath):
        pyxel.load(code_filepath, False, False, True, False)

        pyxel.load(user_filepath, False, False, True, False)

    def set_voice(self, ch, bar, tick, voice):
        self.channels.set_voice(ch, bar, tick, voice)
        pass

    def get_voice(self, ch, bar, tick):
        return self.channels.get_voice(ch, bar, tick)

    @property
    def ch(self, index):
        return self.channels[index]
    @ch.setter
    def ch(self, index, val):
        if type(val) is LCSoundList:
            self.channels[index] = val

    @property
    def code_ch(self, index):
        return self.code_channels[index]
    @ch.setter
    def code_ch(self, index, val):
        if type(val) is LCSoundList:
            self.code_channels[index] = val

    @property
    def r(self, index):
        return self.rhythms[index]
    @ch.setter
    def r(self, index, val):
        if type(val) is LCRhythmList:
            self.rhythms[index] = val

    def to_json(self):
        pass

    def to_midi(self):
        pass

    def load_json(self):
        pass

    def set_by_music(self):
        pass
    #def get_exsound(self):
    #    pass

    def __repr__(self):
        
        s = "LCMusic(speed=" + str(self.speed) + ", channels=["
        l = []
        for v in self.channels:
            l.append(str(v))

        s += ",\n ".join(l)
        s += "])"
        return s

@dataclass
class LCData:
    musics:list = dataclasses.field(default_factory=list)

    voice_samples = []

    def __post_init__(self):
        self.musics = []
        for i in range(MAX_MUSIC_NUM):
            self.musics.append(LCMusic())
    
    def get_music(self, index) -> LCMusic:
        return self.musics[index]

    def update_music(self, index, music_data:LCMusic):
        self.musics[index] = copy.deepcopy(music_data)

    def clear(self):
        for sl in self.musics:
            sl.clear()

    def __len__(self):
        return len(self.musics)

    def __getitem__(self, index)-> LCMusic:
        return self.musics[index]

    def __setitem__(self, index, val):
        if type(val) is LCMusic:
            self.musics[index] = val

    def __delitem__(self, index):
        del self.musics[index]

    def insert(self, index, val):
        if type(val) is LCVoice:
            self.musics.insert(index, val)



# Extended Pyxel Audio class --------------------------

class ExSound(pyxel.Sound):

    def __init__(self, c_obj: Any):
        super(ExSound, self).__init__(c_obj)

    def set_note_num(self, note_list):
        key_names = ""
        for note in note_list:
            key_names += lcl.get_note_name(note)
        self.set_note(key_names)
    
    def clear(self):
        self.set("","","","",30)

    def clear_sfx(self):
        self.set("c3","S","2","N",30)

    def get_notes(self):
        return self._note
    
    def get_notes_str(self):
        s = ""
        for n in self._note:
            s += lcl.get_note_name(n)
        return s

    def get_tones_str(self):
        s = ""
        for n in self._tone:
            s += lcl.get_tone_name(n)
        return s

    def get_volumes_str(self):
        s = ""
        for n in self._volume:
            s += lcl.get_volume_name(n)
        return s

    def get_effects_str(self):
        s = ""
        for n in self._effect:
            s += lcl.get_effect_name(n)
        return s
    
    def get_note(self, index):
        if index < len(self._note):
            return self._note[index]
        return None

    def get_tone(self, index):
        if index < len(self._tone):
            return self._tone[index]
        return None

    def get_volume(self, index):
        if index < len(self._volume):
            return self._volume[index]
        return None

    def get_effect(self, index):
        if index < len(self._effect):
            return self._effect[index]
        return None

    def get_note_char(self, index):
        return lcl.get_note_name(self.get_note(index))

    def get_tone_char(self, index):
        return lcl.get_tone_name(self.get_tone(index))

    def get_volume_char(self, index):
        return lcl.get_volume_name(self.get_volume(index))

    def get_effect_char(self, index):
        return lcl.get_effect_name(self.get_effect(index))

    def get_speed(self):
        return pyxel.core.sound_speed_getter(self._c_obj)
    
    def get_lcsound(self):
        lcs = LCSound()
        for i,n in enumerate(self.note):
            v = LCVoice(n)
            v.t = self.tone[i]
            v.v = self.volume[i]
            v.f = self.effect[i]
            lcs[i] = v
        return lcs
    
    def set_by_lcsound(self, lcs:LCSound, speed=30):
        vl = lcs
        self.set(vl.notes_str(), vl.tones_str(), vl.volumes_str(), vl.effects_str(), speed )
        """
        self.set_note(vl.notes_str())
        self.set_tone(vl.tones_str())
        self.set_volume(vl.volumes_str())
        self.set_effect(vl.effects_str())
        self.speed = speed
        """

        #for i,v in enumerate(lcs):
        #    self.
    
    def set_by_voice(self, voice:LCVoice, speed=30):
        lcs = LCSound()
        lcs.set_voice(0, voice)
        self.set_by_lcsound(lcs, speed)
    
    def set_by_str(self, fmt_str):
        
        debug("LCSound set_by_str()," + fmt_str)
        fmt_str = fmt_str.upper()
        token = fmt_str.split(":")

        if len(token) >= 1:
            notes_str = token[0]
            #self.set_note(notes_str)     for official pyxel's BUG

            #l = len(self.note)
            r_num = notes_str.count("R")
            notes_str.replace('R', '')
            notes_str.replace(' ', '')

            note_num = int(len(notes_str) / 2) + r_num
            tones_str = ""
            volumes_str = ""
            effects_str = ""

            if len(token) >= 2:
                prop_str = token[1]
                if len(prop_str)>=1:
                    tones_str = prop_str[0]*note_num
                    #self.set_tone(prop_str[0]*l)
                if len(prop_str)>=2:
                    volumes_str = prop_str[1]*note_num
                    #self.set_volume(prop_str[1]*l)
                if len(prop_str)>=3:
                    effects_str = prop_str[2]*note_num
                    #self.set_effect(prop_str[2]*l)

            if len(token) >= 3:
                speed_str = token[2]
                if len(speed_str)>=1:
                    self.speed = int(speed_str)
                else:
                    self.speed = 30
            if len(token) >= 4:
                id_str = token[3]
                if len(id_str)>=1:
                    self.id = int(id_str)
                else:
                    self.id = None
            
            print(notes_str, tones_str, volumes_str, effects_str, self.speed)
            self.set(notes_str, tones_str, volumes_str, effects_str, self.speed)

        debug("LCSound set_by_str()_end,")

    def __repr__(self):
        nm = str(type(self))
        nm += "("
        nm += "notes:[" + str(self.get_notes_str())
        nm += "], tones:[" + str(self.get_tones_str())
        nm += "], volumes:[" + str(self.get_volumes_str())
        nm += "], effects:[" + str(self.get_effects_str())
        nm += "], speed:" + str(self.speed)
        nm += ")"
        return nm


class ExMusic(pyxel.Music):
    def __init__(self, c_obj: Any):
        super(ExMusic, self).__init__(c_obj)
        self.init()
    
    #def __post_init__(self):

    def init(self):
        ll = []
        for i in range(pyxel.MUSIC_CHANNEL_COUNT):
            l=[]
            for j in range(16):
                l.append(j*pyxel.MUSIC_CHANNEL_COUNT + i)
            ll.append(l)
        self.set(ll[0], ll[1], ll[2], ll[3])

    @property
    def ch_all(self):
        return [self.ch0, self.ch1, self.ch2, self.ch3]

    def __repr__(self):
        s = "ExMusic("
        l = []
        for i, ch in enumerate(self.ch_all):
            l.append("ch" + str(i) + ":[" + ",".join([str(x) for x in ch]) + "]")
        s += ", ".join(l) + ")"
        return s


# * pyxel init wrapper *
def init(width: int,
    height: int,
    *,
    caption: str = pyxel.DEFAULT_CAPTION,
    scale: int = pyxel.DEFAULT_SCALE,
    palette: List[int] = pyxel.DEFAULT_PALETTE,
    fps: int = pyxel.DEFAULT_FPS,
    quit_key: int = pyxel.DEFAULT_QUIT_KEY,
    fullscreen: bool = False):

    pyxel.init(width,
        height,
        caption=caption ,
        scale=scale,
        palette=palette,
        fps=fps,
        quit_key=quit_key,
        fullscreen=fullscreen
    )


def count_lcmusic():
    return len(lcd)


def get_lcjson():
    return lcjson


def get_lcdata():
    return lcd


def get_lcmusic():
    return lcm


def get_loaded_lcmusic_index() -> int:
    return loaded_lcmusic_index


def get_note_num(key_name:str, standard_notation:bool=False):

    if type(key_name) is not str:
        return None

    n = key_name.strip()
    if n == "":
        return None

    if n == "R":
        return -1

    octave = 0
    if n[-1].isdecimal():
        octave = int(n[-1])
        if standard_notation:
            octave -= 2
        n = n[0:len(n)-1]
    
    if n in NOTEKEY_NAME_LIST:
        key = n.index(n)
        num = key + octave*12
        num = max(num, -1)
        return num
    else:
        return None


def get_tone_num(s:str):
    if type(s) is not str:
        return None
    
    s = s.upper()

    if s in TONE_NAME_LIST:
        return TONE_NAME_LIST.index(s)
    return None


def get_volume_num(s:str):    
    if type(s) is int:
        return s
    elif type(s) is not str:
        return None

    if s in VOLUME_NAME_LIST:
        return VOLUME_NAME_LIST.index(s)
    return None


def get_effect_num(s:str):    
    if type(s) is not str:
        return None
    
    s = s.upper()

    if s in EFFECT_NAME_LIST:
        return EFFECT_NAME_LIST.index(s)
    return None


def get_note_name(note:int, standard_notation=False):
    if note is None or note == -1:
        return "R"
    octave = note//12

    if octave<5:
        if standard_notation:
            octave += 2
        return NOTEKEY_NAME_LIST[note%12] + str( octave )
    else:
        return "R"


def get_note_doremi_name( note:int, standard_notation:bool=False):
    if note is None or note == -1:
        return "R"
    octave = note//12
    
    if octave<5:
        if standard_notation:
            octave += 2
        return DOREMI_NAME_LIST[note%12] +str( octave )
    else:
        return "R"


def get_tone_name(val:int):
    if val is None or val == -1:
        return "T"
    return TONE_NAME_LIST[val]


def get_volume_name(val:int):
    if val is None or val == -1:
        return "5"
    return VOLUME_NAME_LIST[val]


def get_effect_name(val:int):
    if val is None or val == -1:
        return "N"
    return EFFECT_NAME_LIST[val]


def get_scaled_note(note:int, scale_key_list:list):
    if note is None:
        return -1
    n = note
    while True:
        if scale_key_list[n%12] or n == 0:
            return n
        n -= 1
    return n


def get_sound_state():
    s = ""
    for key,snd in pyxel._sound_bank.items():
        t = "LCL used"  if isinstance(snd, lcl.ExSound) else ""
        t +=  " " + str(snd.__class__)
        s += "sound({}): {}\n".format(key, t)
    return s


def mixing_note(un, cn):
    #if un["note"] is not None and un["note"] >= 0 or (un["note"]==-1 and cn["note"]is None or cn["note"]):
    if un["note"] is not None and un["note"] >= 0:
        return un
    else:
        return cn


# ---------------------------------------------------------
# Extended Audio function
#
#_sound_bank: Dict[int, ExSound] = {}
#_music_bank: Dict[int, ExMusic] = {}

def sound(snd: int, *, system: bool = False) -> ExSound:
    obj = core.sound(int(snd), int(system))

    #if snd not in pyxel._sound_bank:
    pyxel._sound_bank[snd] = ExSound(obj)

    return pyxel._sound_bank[snd]

def music(msc: int) -> ExMusic:
    if msc not in pyxel._music_bank:
        pyxel._music_bank[msc] = ExMusic(core.music(int(msc)))

    return pyxel._music_bank[msc]

#def playm(msc: int, *, loop: bool = False) -> None:
#    core.playm(int(msc), int(loop))

def play_str(fmt_str, ch_id=0):
    v = lcl.sound(pyxel.SOUND_BANK_FOR_SYSTEM, system=True)
    v.set_by_str(fmt_str)
    pyxel.play(ch_id, pyxel.SOUND_BANK_FOR_SYSTEM, loop=False)

def play_voice(v:LCVoice, ch_id=0):
    lcl.sound(pyxel.SOUND_BANK_FOR_SYSTEM, system=True).set_by_voice(v)
    pyxel.play(ch_id, pyxel.SOUND_BANK_FOR_SYSTEM, loop=False)

def play_voice_str(fmt_str, ch_id=0):
    v = LCVoice()
    v.set_by_str(fmt_str)
    lcl.play_voice(v, ch_id=ch_id)

def sfx(ch_id=0):
    pyxel.play(ch_id, pyxel.SOUND_BANK_FOR_SYSTEM, loop=False)

def sfx_str(fmt_str):
    lcl.play_str(fmt_str, ch_id=SFX_DEFAULT_CH)



# ------------------------------------------------------
# Lovely Composer Music Player Core
# ------------------------------------------------------

def init( ):
    pass
    #rtn = load(lc_json_file_path)

def load(lc_json_file_path):
    global lcjson
    global lcd
    global lcm

    if not os.path.isfile(lc_json_file_path):
        return False

    with open(lc_json_file_path) as f:
        lcjson = f.read()
        lcjson = json.loads(lcjson, object_hook=json_loader_hook)
        lcd = lcjson["lcdata"]
        lcm = lcd[0]
        return True
    return False

def mixing_sound(snd_idx, code_idx):

    mixed_note_list = []
    user = _user_sound[snd_idx]
    code = _code_sound[code_idx]

    for j in range(lcl.MAX_SOUND_LENGTH):
        pass
        #mixed_note = {"note":None,"tone":None,}
        #if j < len(user["all"]) and j < len(code["all"]):
        #mixed_note = mixing_note(user["all"][j], code["all"][j] )
        """
        else:
            if j < len(user):
                mixed_note = user["all"][j]
            elif j < len(code):
                mixed_note = code["all"][j]
            else:
                break
        """
        #mixed_note_list.append(copy.copy(mixed_note))

    return mixed_note_list


def non_remix_bar_sound(bar):

    sound_stack = []
    for ch in lcm.channels:
        #print(ch[bar])
        lcs = ch[bar]
        #us = pyxel.sound(snd_idx)
        sound_stack.append(copy.copy(lcs))
        
    limited_output_stack = sound_stack[0:4]

    return limited_output_stack


def mixing_bar_sound(bar):

    #music = pyxel.music(0)
    #r_ptn = parent._songs["rhythm_pattern"][bar]

    # ユーザ・コードの全チャンネルのノートをいったんスタックに積む
    # user ch:0 -> code ch:0-> user ch:1 ... -> user ch:3 -> code ch:3 の順に積む
    ch_num=0
    sound_stack = []
    for ch in lcm.channels:
        #print(ch[bar])
        lcs = ch[bar]
        #us = pyxel.sound(snd_idx)
        sound_stack.append(copy.copy(lcs))
        """
        if r_ptn>=1:
            if ch_num==0 and _code_rhythm_button.value==False \
                or ch_num==1 and _code_base_button.value==False \
                or ch_num==2 and _code_arpeggio_button.value==False:
                pass
            else:
                cs = parent._code_sound[ snd_idx + parent._songs["rhythm_pattern"][bar]-1 ] 
                n = copy.copy(cs["all"][j])
                #if n["note"] is not None:
                #    n["note"] -= j
                sound_stack.append(n)
        """
        ch_num+=1
    
    # 8チャンネルのうちノートの存在するチャンネルの分だけ新しいスタックに乗せる
    output_stack = []
    for s in sound_stack:
        print(s.notes)
        if len(s.notes)>=1:
            output_stack.append(s)

    # 上位4位以外のノートは切り捨てる
    limited_output_stack = output_stack[0:4]
    while len(limited_output_stack)<4:
        limited_output_stack.append(pyxel.LCSound())   # 穴埋め

    return limited_output_stack


def _get_start_index_for_tail(load_channels=4, load_pages=16):
    return pyxel.USER_SOUND_BANK_COUNT - (load_channels * load_pages)


def update_note_mixing(load_channels=4, load_pages=16, load_to_tail=True, channel_compress=False):

    for h in range(0, load_pages):
        str_notes   = ["","","",""]
        str_tones   = ["","","",""]
        str_volumes = ["","","",""]
        str_effects = ["","","",""]

        if channel_compress:
            mixed_note_list = mixing_bar_sound(h)   # 1小節分のノート
        else:
            mixed_note_list = non_remix_bar_sound(h)
        
        #debug("mixed_note_list:%s", str(mixed_note_list))
        
        # 1列ごとのノート情報 32回ループ
        for i in range(lcl.MAX_SOUND_LENGTH):

            # 1ノート情報ごと 最大4回ループ
            for j in range(load_channels):
                lcs = mixed_note_list[j]
                v = lcs[i]

                if v.n is not None and v.n>=0:
                    str_notes[j] +=  lcl.get_note_name( v.n )
                else:
                    str_notes[j] += "R"
                str_tones[j]   += v.tone_char()
                str_volumes[j] += v.volume_char()
                str_effects[j] += v.effect_char()

        # 最終的にsoundにセット
        for i in range(load_channels):
            snd_idx = i + (h*load_channels)
            if load_to_tail:
                snd_idx += _get_start_index_for_tail(load_channels, load_pages)
            debug("snd_idx: %d", snd_idx )
            lcl.sound(snd_idx).set(str_notes[i], str_tones[i], str_volumes[i], str_effects[i], lcm.speed)


def load_lcmusic(lcm_index:int, load_channels=4, load_pages=16, load_to_tail=True, channel_compress=False):
    global loaded_lcmusic_index
    global lcm

    debug("load_sound len(lcd): " + str(len(lcd)))

    if lcm_index >= count_lcmusic() or lcm_index <= -1:
        error("lcmusic index is out of range")
        return False
    
    lcm = lcd[lcm_index]
    update_note_mixing(load_channels, load_pages, load_to_tail, channel_compress)
    loaded_lcmusic_index = lcm_index


def setup_music(music_id=7, bar:int=0, load_channels=4, load_pages=16, load_to_tail=True):

    debug("bar:%d load_channels:%d load_pages:%d", bar, load_channels, load_pages)
    m = lcl.music(music_id)

    # if load_to_tail=True then shift load sound index
    index_shift = _get_start_index_for_tail(load_channels, load_pages) if load_to_tail else 0

    # if No loop end setting ----
    if lcm.loop_end_bar is None:
        pl = [[] for i in range(4)]

        # calc play start bar's sound index
        bar_idx = bar * load_channels + index_shift

        # calc play end bar's sound index
        end_bar_idx = load_pages * load_channels + index_shift
        debug("bar_idx:%d end_bar_idx:%d", bar_idx, end_bar_idx)

        # first time play list
        for i in range(load_channels):
            pl[i] = list(range(bar_idx+i, end_bar_idx, load_channels))

        m.set(pl[0], pl[1], pl[2], pl[3])
        debug("%s",str(pl))
    
    # loop play ----
    else:
        # sound play list by channel
        pl = [[] for i in range(4)]

        # calc play start bar's sound index
        bar_idx = bar * load_channels + index_shift

        # calc play end bar's sound index
        end_bar_idx = (lcm.loop_end_bar+1) * load_channels + index_shift

        # calc loop start bar's sound index
        loop_start_bar_idx = 0
        if lcm.loop_start_bar is not None:
            loop_start_bar_idx = lcm.loop_start_bar * load_channels + index_shift
        
        debug("bar_idx:%d end_bar_idx:%d loop_start_bar_idx:%d", bar_idx, end_bar_idx, loop_start_bar_idx)

        # first time play list
        for i in range(load_channels):
            pl[i] += list(range(bar_idx+i, end_bar_idx+i, load_channels))

        # after repeat loop /  near infinity times
        for h in range(100):
            for i in range(load_channels):
                pl[i] += range(loop_start_bar_idx+i, end_bar_idx, load_channels)

        debug("%s",str(pl))
        m.set(pl[0], pl[1], pl[2], pl[3])


def setup_music_for_page_loop(music_id=7, bar:int=0, load_channels=4, load_to_tail=True):
    m = lcl.music(music_id)

    bar_idx = bar * load_channels
    if load_to_tail:
        bar_idx += _get_start_index_for_tail(load_channels, 1)

    debug("bar_idx:%d ", bar_idx)

    pl = [[] for i in range(4)]
    for i in range(load_channels):
        pl[i] += list(bar_idx+i)
        
    debug("%s",str(pl))
    m.set(pl[0], pl[1], pl[2], pl[3])


def stop_channels(load_channels=4):
    for i in range(load_channels):
        pyxel.stop(i)


def play_page_loop(lcm_index:int=0, start_bar:int=0, music_id:int=7, load_channels=4, load_to_tail=True, channel_compress=False):
    
    if lcm_index >= count_lcmusic() or lcm_index <= -1:
        error("lcmusic index is out of range")
        return False
    
    #stop_channels(load_channels)
    pyxel.stop()
    
    load_lcmusic(lcm_index, load_channels, load_to_tail, channel_compress)
    setup_music_for_page_loop(music_id, start_bar, load_channels, load_to_tail)

    pyxel.playm(music_id, loop=True)
    return True


def play(lcm_index:int, start_bar:int=0, loop:bool=False, music_id:int=7,
         load_channels:int=4, load_pages:int=16, load_to_tail:bool=True, channel_compress:bool=False):

    if lcm_index >= count_lcmusic() or lcm_index <= -1:
        error("lcmusic index is out of range")
        return False

    pyxel.stop()
    
    load_lcmusic(lcm_index, load_channels, load_pages, load_to_tail, channel_compress)
    setup_music(music_id, start_bar, load_channels, load_pages, load_to_tail)

    pyxel.playm(music_id, loop=loop)
    return True


# Misc ------------------------------------------------------------------------

def obj_to_dict(obj):
    dic = obj.__dict__
    class_key = "__" + obj.__class__.__name__ + "__"
    dic[class_key] = True
    return dic

class LCJSONEncoder(json.JSONEncoder):

    def default(self, o):
        for c in json_class_list:
            if isinstance(o, c):
                return obj_to_dict(o)

        return super(LCJSONEncoder, self).default(o) # 他の型はdefaultのエンコード方式を使用

        #raise TypeError(f"Object of type '{type_name}' is not JSON serializable")

def json_loader_hook(dic):

    for key, val in json_class_dict.items():
        if key in dic:
            obj = val()
            for k,v in dic.items():
                setattr(obj, k, v)
            return obj

    return dic # 他の型はdefaultのデコード方式を使用

# module variables ---

json_class_list = [
LCData,
LCMusic,
LCChannelList,
LCSoundList,
LCSound,
LCVoice,
LCRhythmList,
LCRhythm,
AppSettings
]

json_class_dict ={}
for c in json_class_list:
    json_class_dict["__" + c.__name__ + "__"] = c
#debug(json_class_dict)
