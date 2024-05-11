# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as log
import time

import gbcore as gb

class Emulator:
	def __init__(self):
		self.mobo = None
		pass

	def load(self, filename):
		self.mobo = gb.Mobo()
		self.mobo.load(filename)

	def run(self):
		while True:
			now = time.perf_counter_ns()
			self.mobo.tick()
			delta = time.perf_counter_ns()-now
			now += delta
			# time.sleep(1)
		pass

