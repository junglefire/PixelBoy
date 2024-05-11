# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as log

import gbcore as gb

class Emulator:
	def __init__(self):
		self.mobo = None
		pass

	def load(self, filename):
		self.mobo = gb.Mobo()
		self.mobo.load(filename)
