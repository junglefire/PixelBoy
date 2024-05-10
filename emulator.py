# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as log

# GameBoy Core Module
import gbcore as gb

class Emulator:
	def __init__(self):
		self.rom = None
		pass

	def load(self, filename):
		self.rom = gb.load_cartridge(filename)
		log.info(f"ROM Info:\n{self.rom}")
