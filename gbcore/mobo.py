# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as logger
import array

from .cartridge import load_cartridge
from .bootrom import BootROM
from .joypad import Joypad
from .parameters import *
# from .sound import Sound
from .timer import Timer
from .ram import RAM
from .cpu import CPU
from .ppu import PPU
from .gui import GUI

defaults = {
	"color_palette": (0xFFFFFF, 0x999999, 0x555555, 0x000000),
	"cgb_color_palette": (
		(0xFFFFFF, 0x7BFF31, 0x0063C5, 0x000000), 
		(0xFFFFFF, 0xFF8484, 0x943A3A, 0x000000), 
		(0xFFFFFF, 0xFF8484, 0x943A3A, 0x000000)
	),
	"scale": 3,
	"window": "SDL2",
	"log_level": "DEBUG",
}

class Mobo:
	def __init__(self):
		self.cartridge = None
		self.ram = None
		self.cpu = None
		self.ppu = None
		self.timer = None
		self.joypad = None
		self.bootrom = None
		self.gui = None
		# self.sound = None
		# 串口 
		self.serialbuffer = [0] * 1024
		self.serialbuffer_count = 0
		self.bootrom_enabled = True
		self.cgb = False
		pass

	def load(self, filename):
		self.cartridge = load_cartridge(filename)
		logger.info(f"ROM Info:\n{self.cartridge}")
		self.timer = Timer()
		self.ram = RAM(False, False)
		self.cpu = CPU(self)
		self.ppu = PPU(defaults["color_palette"])
		self.bootrom = BootROM(bootrom_file=None, cgb=False)
		self.joypad = Joypad()
		self.gui = GUI(self.cpu, self.ppu, self.joypad)
		# self.sound = Sound(False, False)

	def tick(self):
		if self.gui.handle_event() == True:
			return True
		while self.processing_frame():
			cycles = self.cpu.tick()
			if self.timer.tick(cycles):
				self.cpu.set_interruptflag(INTR_TIMER)
			lcd_interrupt = self.ppu.tick(cycles)
			if lcd_interrupt:
				self.cpu.set_interruptflag(lcd_interrupt)
		self.gui.update()
		return False

	def getitem(self, i):
		if 0x0000 <= i < 0x4000: # 16kB ROM bank #0
			if self.bootrom_enabled and (i <= 0xFF or (self.cgb and 0x200 <= i < 0x900)):
				return self.bootrom.getitem(i)
			else:
				return self.cartridge.getitem(i)
		elif 0x4000 <= i < 0x8000: # 16kB switchable ROM bank
			return self.cartridge.getitem(i)
		elif 0x8000 <= i < 0xA000: # 8kB Video RAM
			if not self.cgb or self.ppu.vbk.active_bank == 0:
				return self.ppu.VRAM0[i - 0x8000]
			else:
				return self.ppu.VRAM1[i - 0x8000]
		elif 0xA000 <= i < 0xC000: # 8kB switchable RAM bank
			return self.cartridge.getitem(i)
		elif 0xC000 <= i < 0xE000: # 8kB Internal RAM
			bank_offset = 0
			if self.cgb and 0xD000 <= i:
				# Find which bank to read from at FF70
				bank = self.getitem(0xFF70)
				bank &= 0b111
				if bank == 0x0:
					bank = 0x01
				bank_offset = (bank-1) * 0x1000
			return self.ram.internal_ram0[i - 0xC000 + bank_offset]
		elif 0xE000 <= i < 0xFE00: # Echo of 8kB Internal RAM
			# Redirect to internal RAM
			return self.getitem(i - 0x2000)
		elif 0xFE00 <= i < 0xFEA0: # Sprite Attribute Memory (OAM)
			return self.ppu.OAM[i - 0xFE00]
		elif 0xFEA0 <= i < 0xFF00: # Empty but unusable for I/O
			return self.ram.non_io_internal_ram0[i - 0xFEA0]
		elif 0xFF00 <= i < 0xFF4C: # I/O ports
			if i == 0xFF04:
				return self.timer.DIV
			elif i == 0xFF05:
				return self.timer.TIMA
			elif i == 0xFF06:
				return self.timer.TMA
			elif i == 0xFF07:
				return self.timer.TAC
			elif i == 0xFF0F:
				return self.cpu.interrupts_flag_register
			elif 0xFF10 <= i < 0xFF40:
				pass
				# [alex] return self.sound.get(i - 0xFF10)
			elif i == 0xFF40:
				return self.ppu.get_lcdc()
			elif i == 0xFF41:
				return self.ppu.get_stat()
			elif i == 0xFF42:
				return self.ppu.SCY
			elif i == 0xFF43:
				return self.ppu.SCX
			elif i == 0xFF44:
				return self.ppu.LY
			elif i == 0xFF45:
				return self.ppu.LYC
			elif i == 0xFF46:
				return 0x00 # DMA
			elif i == 0xFF47:
				return self.ppu.BGP.get()
			elif i == 0xFF48:
				return self.ppu.OBP0.get()
			elif i == 0xFF49:
				return self.ppu.OBP1.get()
			elif i == 0xFF4A:
				return self.ppu.WY
			elif i == 0xFF4B:
				return self.ppu.WX
			else:
				return self.ram.io_ports[i - 0xFF00]
		elif 0xFF4C <= i < 0xFF80: # Empty but unusable for I/O
			# CGB registers
			if self.cgb and i == 0xFF4D:
				return self.key1
			elif self.cgb and i == 0xFF4F:
				return self.ppu.vbk.get()
			elif self.cgb and i == 0xFF68:
				return self.ppu.bcps.get() | 0x40
			elif self.cgb and i == 0xFF69:
				return self.ppu.bcpd.get()
			elif self.cgb and i == 0xFF6A:
				return self.ppu.ocps.get() | 0x40
			elif self.cgb and i == 0xFF6B:
				return self.ppu.ocpd.get()
			elif self.cgb and i == 0xFF51:
				# logger.debug("HDMA1 is not readable")
				return 0x00 # Not readable
			elif self.cgb and i == 0xFF52:
				# logger.debug("HDMA2 is not readable")
				return 0x00 # Not readable
			elif self.cgb and i == 0xFF53:
				# logger.debug("HDMA3 is not readable")
				return 0x00 # Not readable
			elif self.cgb and i == 0xFF54:
				# logger.debug("HDMA4 is not readable")
				return 0x00 # Not readable
			elif self.cgb and i == 0xFF55:
				return self.hdma.hdma5 & 0xFF
			return self.ram.non_io_internal_ram1[i - 0xFF4C]
		elif 0xFF80 <= i < 0xFFFF: # Internal RAM
			return self.ram.internal_ram1[i - 0xFF80]
		elif i == 0xFFFF: # Interrupt Enable Register
			return self.cpu.interrupts_enabled_register
		# else:
		#	logger.critical("Memory access violation. Tried to read: %0.4x", i)

	def setitem(self, i, value):
		if 0x0000 <= i < 0x4000: # 16kB ROM bank #0
			# Doesn't change the data. This is for MBC commands
			self.cartridge.setitem(i, value)
		elif 0x4000 <= i < 0x8000: # 16kB switchable ROM bank
			# Doesn't change the data. This is for MBC commands
			self.cartridge.setitem(i, value)
		elif 0x8000 <= i < 0xA000: # 8kB Video RAM
			if not self.cgb or self.ppu.vbk.active_bank == 0:
				self.ppu.VRAM0[i - 0x8000] = value
				if i < 0x9800: # Is within tile data -- not tile maps
					# Mask out the byte of the tile
					self.ppu.render.invalidate_tile(((i & 0xFFF0) - 0x8000) // 16, 0)
			else:
				self.ppu.VRAM1[i - 0x8000] = value
				if i < 0x9800: # Is within tile data -- not tile maps
					# Mask out the byte of the tile
					self.ppu.renderer.invalidate_tile(((i & 0xFFF0) - 0x8000) // 16, 1)
		elif 0xA000 <= i < 0xC000: # 8kB switchable RAM bank
			self.cartridge.setitem(i, value)
		elif 0xC000 <= i < 0xE000: # 8kB Internal RAM
			bank_offset = 0
			if self.cgb and 0xD000 <= i:
				# Find which bank to read from at FF70
				bank = self.getitem(0xFF70)
				bank &= 0b111
				if bank == 0x0:
					bank = 0x01
				bank_offset = (bank-1) * 0x1000
			self.ram.internal_ram0[i - 0xC000 + bank_offset] = value
		elif 0xE000 <= i < 0xFE00: # Echo of 8kB Internal RAM
			self.setitem(i - 0x2000, value) # Redirect to internal RAM
		elif 0xFE00 <= i < 0xFEA0: # Sprite Attribute Memory (OAM)
			self.ppu.OAM[i - 0xFE00] = value
		elif 0xFEA0 <= i < 0xFF00: # Empty but unusable for I/O
			self.ram.non_io_internal_ram0[i - 0xFEA0] = value
		elif 0xFF00 <= i < 0xFF4C: # I/O ports
			if i == 0xFF00:
				self.ram.io_ports[i - 0xFF00] = self.joypad.pull(value)
			elif i == 0xFF01:
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
			elif i == 0xFF0F:
				self.cpu.interrupts_flag_register = value
			elif 0xFF10 <= i < 0xFF40:
				pass
				# self.sound.set(i - 0xFF10, value)
			elif i == 0xFF40:
				self.ppu.set_lcdc(value)
			elif i == 0xFF41:
				self.ppu.set_stat(value)
			elif i == 0xFF42:
				self.ppu.SCY = value
			elif i == 0xFF43:
				self.ppu.SCX = value
			elif i == 0xFF44:
				self.ppu.LY = value
			elif i == 0xFF45:
				self.ppu.LYC = value
			elif i == 0xFF46:
				self.transfer_DMA(value)
			elif i == 0xFF47:
				if self.ppu.BGP.set(value):
					# TODO: Move out of MB
					self.ppu.render.clear_tilecache0()
			elif i == 0xFF48:
				if self.ppu.OBP0.set(value):
					# TODO: Move out of MB
					self.ppu.render.clear_spritecache0()
			elif i == 0xFF49:
				if self.ppu.OBP1.set(value):
					# TODO: Move out of MB
					self.ppu.render.clear_spritecache1()
			elif i == 0xFF4A:
				self.ppu.WY = value
			elif i == 0xFF4B:
				self.ppu.WX = value
			else:
				self.ram.io_ports[i - 0xFF00] = value
		elif 0xFF4C <= i < 0xFF80: # Empty but unusable for I/O
			if self.bootrom_enabled and i == 0xFF50 and (value == 0x1 or value == 0x11):
				logger.debug("Bootrom disabled!")
				self.bootrom_enabled = False
			# CGB registers
			elif self.cgb and i == 0xFF4D:
				self.key1 = value
			elif self.cgb and i == 0xFF4F:
				self.ppu.vbk.set(value)
			elif self.cgb and i == 0xFF51:
				self.hdma.hdma1 = value
			elif self.cgb and i == 0xFF52:
				self.hdma.hdma2 = value # & 0xF0
			elif self.cgb and i == 0xFF53:
				self.hdma.hdma3 = value # & 0x1F
			elif self.cgb and i == 0xFF54:
				self.hdma.hdma4 = value # & 0xF0
			elif self.cgb and i == 0xFF55:
				self.hdma.set_hdma5(value, self)
			elif self.cgb and i == 0xFF68:
				self.ppu.bcps.set(value)
			elif self.cgb and i == 0xFF69:
				self.ppu.bcpd.set(value)
				self.ppu.renderer.clear_tilecache0()
				self.ppu.renderer.clear_tilecache1()
			elif self.cgb and i == 0xFF6A:
				self.ppu.ocps.set(value)
			elif self.cgb and i == 0xFF6B:
				self.ppu.ocpd.set(value)
				self.ppu.renderer.clear_spritecache0()
				self.ppu.renderer.clear_spritecache1()
			else:
				self.ram.non_io_internal_ram1[i - 0xFF4C] = value
		elif 0xFF80 <= i < 0xFFFF: # Internal RAM
			self.ram.internal_ram1[i - 0xFF80] = value
		elif i == 0xFFFF: # Interrupt Enable Register
			self.cpu.interrupts_enabled_register = value
		else:
			logger.critical("Memory access violation. Tried to write: 0x%0.2x to 0x%0.4x", value, i)

	def getserial(self):
		b = "".join([chr(x) for x in self.serialbuffer[:self.serialbuffer_count]])
		self.serialbuffer_count = 0
		return b

	def processing_frame(self):
		b = (not self.ppu.frame_done)
		self.ppu.frame_done = False # Clear vblank flag for next iteration
		return b

	def transfer_DMA(self, src):
		# http://problemkaputt.de/pandocs.htm#lcdoamdmatransfers
		# TODO: Add timing delay of 160µs and disallow access to RAM!
		dst = 0xFE00
		offset = src * 0x100
		for n in range(0xA0):
			self.setitem(dst + n, self.getitem(n + offset))


