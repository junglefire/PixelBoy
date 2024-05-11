# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as logger
import array

from .cartridge import load_cartridge
from .timer import Timer
from .ram import RAM
from .cpu import CPU

class Mobo:
	def __init__(self):
		self.cartridge = None
		self.ram = None
		self.cpu = None
		self.timer = None
		self.VRAM0 = array.array("B", [0] * 8 * 1024)
		# 串口 
		self.serialbuffer = [0] * 1024
		self.serialbuffer_count = 0
		pass

	def load(self, filename):
		self.cartridge = load_cartridge(filename)
		logger.info(f"ROM Info:\n{self.cartridge}")
		self.timer = Timer()
		self.ram = RAM(False, False)
		self.cpu = CPU(self)

	def tick(self):
		cycles = self.cpu.tick()
		if self.timer.tick(cycles):
			self.cpu.set_interruptflag(INTR_TIMER)
		pass

	def getitem(self, i):
		if 0x0000 <= i < 0x4000: # 16kB ROM bank #0
			return self.cartridge.getitem(i)
		elif 0x4000 <= i < 0x8000: # 16kB switchable ROM bank
			return self.cartridge.getitem(i)
		elif 0x8000 <= i < 0xA000: # 8kB Video RAM
			return self.VRAM0[i - 0x8000]
		elif 0xA000 <= i < 0xC000: # 8kB switchable RAM bank
			return self.cartridge.getitem(i)
		elif 0xC000 <= i < 0xE000: # 8kB Internal RAM
			bank_offset = 0
			return self.ram.internal_ram0[i - 0xC000 + bank_offset]
		elif 0xFF00 <= i < 0xFF4C: # I/O ports
			if i == 0xFF04:
				return self.timer.DIV
			elif i == 0xFF05:
				return self.timer.TIMA
			elif i == 0xFF06:
				return self.timer.TMA
			elif i == 0xFF07:
				return self.timer.TAC
		elif 0xFF80 <= i < 0xFFFF: # Internal RAM
			return self.ram.internal_ram1[i - 0xFF80]
		else:
			logger.critical("Memory access violation. Tried to read: %0.4x", i)

	def setitem(self, i, value):
		if 0x0000 <= i < 0x4000: # 16kB ROM bank #0
			# Doesn't change the data. This is for MBC commands
			self.cartridge.setitem(i, value)
		elif 0x4000 <= i < 0x8000: # 16kB switchable ROM bank
			# Doesn't change the data. This is for MBC commands
			self.cartridge.setitem(i, value)
		elif 0x8000 <= i < 0xA000: # 8kB Video RAM
			self.lcd.VRAM0[i - 0x8000] = value
		elif 0xA000 <= i < 0xC000: # 8kB switchable RAM bank
			self.cartridge.setitem(i, value)
		elif 0xC000 <= i < 0xE000: # 8kB Internal RAM
			bank_offset = 0
			self.ram.internal_ram0[i - 0xC000 + bank_offset] = value
		elif 0xFF00 <= i < 0xFF4C: # I/O ports
			if i == 0xFF01:
				self.serialbuffer[self.serialbuffer_count] = value
				self.serialbuffer_count += 1
				self.serialbuffer_count &= 0x3FF
				self.ram.io_ports[i - 0xFF00] = value
			elif i == 0xFF04:
				self.timer.reset()
			elif i == 0xFF05:
				self.timer.TIMA = value
			elif i == 0xFF06:
				self.timer.TMA = value
			elif i == 0xFF07:
				self.timer.TAC = value & 0b111 # TODO: Move logic to Timer class
		elif 0xFF80 <= i < 0xFFFF: # Internal RAM
			self.ram.internal_ram1[i - 0xFF80] = value
		else:
			logger.critical("Memory access violation. Tried to write: 0x%0.2x to 0x%0.4x", value, i)	

	def getserial(self):
		b = "".join([chr(x) for x in self.serialbuffer[:self.serialbuffer_count]])
		self.serialbuffer_count = 0
		return b


