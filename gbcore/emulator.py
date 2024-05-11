# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as log

from .cartridge import load_cartridge

class Emulator:
	def __init__(self):
		self.rom = None
		pass

	def load(self, filename):
		self.rom = load_cartridge(filename)
		log.info(f"ROM Info:\n{self.rom}")
