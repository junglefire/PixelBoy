# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as log
import ctypes
import time

# import PySDL2
from sdl2.ext import get_events
from sdl2 import *

from .parameters import *

# The GUI class is the user interface for interaction, encompassing user input and output and image display
class GUI:
	def __init__(self, cpu, ppu, joypad):
		SDL_Init(SDL_INIT_VIDEO|SDL_INIT_GAMECONTROLLER)
		self._ftime = time.perf_counter_ns()
		self._window = SDL_CreateWindow(b"PixelBoy", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, COLS*SCALE, ROWS*SCALE, SDL_WINDOW_RESIZABLE)
		self._sdlrenderer = SDL_CreateRenderer(self._window, -1, SDL_RENDERER_ACCELERATED)
		SDL_RenderSetLogicalSize(self._sdlrenderer, COLS, ROWS)
		self._sdltexturebuffer = SDL_CreateTexture(self._sdlrenderer, SDL_PIXELFORMAT_ABGR8888, SDL_TEXTUREACCESS_STATIC, COLS, ROWS) 
		SDL_ShowWindow(self._window)
		self.ppu = ppu
		self.cpu = cpu
		self.joypad = joypad
		pass

	def handle_event(self) -> bool:
		event = SDL_Event()
		while SDL_PollEvent(ctypes.byref(event)) != 0:
			if event.type == SDL_QUIT:
				return True	
			elif event.type == SDL_KEYDOWN or event.type == SDL_KEYUP:
				if self.joypad.key_event(event):
					self.cpu.set_interruptflag(INTR_HIGHTOLOW)
			else:
				pass
		return False

	def update(self):
		SDL_UpdateTexture(self._sdltexturebuffer, None, self.ppu.render._screenbuffer_ptr, COLS * 4)
		SDL_RenderCopy(self._sdlrenderer, self._sdltexturebuffer, None, None)
		SDL_RenderPresent(self._sdlrenderer)
		SDL_RenderClear(self._sdlrenderer)
	
	def __del__(self):
		SDL_DestroyTexture(self._sdltexturebuffer)
		SDL_DestroyRenderer(self._sdlrenderer)
		SDL_DestroyWindow(self._window)
		SDL_Quit()		