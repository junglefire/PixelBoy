# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as log
import ctypes
import time

# import PySDL2
from sdl2.ext import get_events
from sdl2 import *

import gbcore as gb

ROWS, COLS = 144, 160
SCALE = 3

class Displayer:
	def __init__(self, mobo):
		SDL_Init(SDL_INIT_VIDEO|SDL_INIT_GAMECONTROLLER)
		self._ftime = time.perf_counter_ns()
		self._window = SDL_CreateWindow(b"PixelBoy", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, COLS*SCALE, ROWS*SCALE, SDL_WINDOW_RESIZABLE)
		self._sdlrenderer = SDL_CreateRenderer(self._window, -1, SDL_RENDERER_ACCELERATED)
		SDL_RenderSetLogicalSize(self._sdlrenderer, COLS, ROWS)
		self._sdltexturebuffer = SDL_CreateTexture(self._sdlrenderer, SDL_PIXELFORMAT_ABGR8888, SDL_TEXTUREACCESS_STATIC, COLS, ROWS) 
		SDL_ShowWindow(self._window)
		self.mobo = mobo
		pass

	def update(self):
		event = SDL_Event()
		running = True
		while SDL_PollEvent(ctypes.byref(event)) != 0:
			if event.type == SDL_QUIT:
				running = False
				break
		SDL_UpdateTexture(self._sdltexturebuffer, None, self.mobo.ppu.render._screenbuffer_ptr, COLS * 4)
		SDL_RenderCopy(self._sdlrenderer, self._sdltexturebuffer, None, None)
		SDL_RenderPresent(self._sdlrenderer)
		SDL_RenderClear(self._sdlrenderer)
	
	def __del__(self):
		SDL_DestroyTexture(self._sdltexturebuffer)
		SDL_DestroyRenderer(self._sdlrenderer)
		SDL_DestroyWindow(self._window)
		SDL_Quit()		