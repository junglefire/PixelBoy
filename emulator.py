# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as log
import time

import gbcore as gb

class Emulator:
	def __init__(self, filename: str):
		self.mobo = gb.Mobo()
		self.mobo.load(filename)
		pass

	def run(self):
		_done = False
		while not _done:
			now = time.perf_counter_ns()
			_done = self.mobo.tick()
			delta = time.perf_counter_ns()-now
			now += delta
		pass

