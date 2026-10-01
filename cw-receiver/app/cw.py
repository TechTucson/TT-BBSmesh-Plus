import math
import time
from collections import deque

import numpy as np

MORSE = {
    '.-':'A','-...':'B','-.-.':'C','-..':'D','.':'E','..-.':'F','--.':'G','....':'H','..':'I',
    '.---':'J','-.-':'K','.-..':'L','--':'M','-.':'N','---':'O','.--.':'P','--.-':'Q','.-.':'R',
    '...':'S','-':'T','..-':'U','...-':'V','.--':'W','-..-':'X','-.--':'Y','--..':'Z',
    '-----':'0','.----':'1','..---':'2','...--':'3','....-':'4','.....':'5','-....':'6','--...':'7',
    '---..':'8','----.':'9','.-.-.-':'.','--..--':',','..--..':'?','-..-.':'/','-....-':'-','.--.-.':'@'
}

class CWDecoder:
    def __init__(self, sample_rate=12000, tone=700, wpm=18):
        self.sample_rate = sample_rate
        self.tone = tone
        self.wpm = wpm
        self.dot_ms = 1200.0 / max(5, wpm)
        self.frame_ms = 10
        self.frame_n = max(32, int(sample_rate * self.frame_ms / 1000))
        self.phase = 0.0
        self.noise = 1.0
        self.level = 0.0
        self.state = False
        self.state_since = time.monotonic()
        self.symbol = ''
        self.raw = deque(maxlen=200)
        self.text = deque(maxlen=1000)
        self.events = deque(maxlen=100)

    def _tone_power(self, x):
        n = len(x)
        if n == 0:
            return 0.0
        t = np.arange(n)
        w = 2 * math.pi * self.tone / self.sample_rate
        c = np.cos(w*t)
        s = np.sin(w*t)
        i = float(np.dot(x, c))
        q = float(np.dot(x, s))
        return math.sqrt(i*i + q*q) / n

    def feed(self, samples):
        now = time.monotonic()
        for pos in range(0, len(samples)-self.frame_n+1, self.frame_n):
            frame = samples[pos:pos+self.frame_n].astype(np.float32)
            power = self._tone_power(frame)
            self.level = 0.85*self.level + 0.15*power
            if not self.state:
                self.noise = 0.995*self.noise + 0.005*max(power, 0.1)
            threshold = max(self.noise * 3.0, 20.0)
            keyed = power > threshold
            t = time.monotonic()
            if keyed != self.state:
                duration_ms = (t-self.state_since)*1000.0
                self._transition(self.state, duration_ms)
                self.state = keyed
                self.state_since = t
        return now

    def _transition(self, was_keyed, duration_ms):
        dot = self.dot_ms
        if was_keyed:
            mark = '.' if duration_ms < dot*2.0 else '-'
            self.symbol += mark
            self.raw.append(mark)
        else:
            if duration_ms >= dot*6.0:
                self._finish_symbol()
                if self.text and self.text[-1] != ' ':
                    self.text.append(' ')
                self.raw.append(' / ')
            elif duration_ms >= dot*2.0:
                self._finish_symbol()
                self.raw.append(' ')

    def _finish_symbol(self):
        if not self.symbol:
            return
        ch = MORSE.get(self.symbol, '?')
        self.text.append(ch)
        self.events.append({'morse': self.symbol, 'char': ch})
        self.symbol = ''

    def snapshot(self):
        return {
            'tone_hz': self.tone,
            'wpm': self.wpm,
            'level': round(self.level, 2),
            'noise': round(self.noise, 2),
            'keyed': self.state,
            'pending': self.symbol,
            'raw': ''.join(self.raw),
            'text': ''.join(self.text),
        }
