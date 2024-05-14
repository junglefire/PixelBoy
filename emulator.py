# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as log
import time

import displayer as dp 
import gbcore as gb

class Emulator:
	def __init__(self, filename: str):
		self.mobo = gb.Mobo()
		self.mobo.load(filename)
		self.displayer = dp.Displayer(self.mobo)
		pass

	def run(self):
		while True:
			now = time.perf_counter_ns()
			self.mobo.tick()
			delta = time.perf_counter_ns()-now
			now += delta
			self.displayer.update()
		pass

