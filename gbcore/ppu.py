# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as logger
import array

from .parameters import *
from .render import *

def rgb_to_bgr(color):
	a = 0xFF
	r = (color >> 16) & 0xFF
	g = (color >> 8) & 0xFF
	b = color & 0xFF
	return (a << 24) | (b << 16) | (g << 8) | r

# 0xFF40 - LCDC (LCD Control)
class LCDCRegister:
	def __init__(self, value):
		self.set(value)

	def set(self, value):
		self.value = value
		self.lcd_enable = value & (1 << 7)
		self.windowmap_select = value & (1 << 6)
		self.window_enable = value & (1 << 5)
		self.tiledata_select = value & (1 << 4)
		self.backgroundmap_select = value & (1 << 3)
		self.sprite_height = value & (1 << 2)
		self.sprite_enable = value & (1 << 1)
		self.background_enable = value & (1 << 0)
		self.cgb_master_priority = self.background_enable # Different meaning on CGB

	def _get_sprite_height(self):
		return self.sprite_height
	
# 0xFF41 - LCDS (LCD Status)
class STATRegister:
	def __init__(self):
		self.value = 0b1000_0000
		self._mode = 0

	def set(self, value):
		value &= 0b0111_1000 # Bit 7 is always set, and bit 0-2 are read-only
		self.value &= 0b1000_0111 # Preserve read-only bits and clear the rest
		self.value |= value # Combine the two

	def update_LYC(self, LYC, LY):
		if LYC == LY:
			self.value |= 0b100 # Sets the LYC flag
			if self.value & 0b0100_0000: # LYC interrupt enabled flag
				return INTR_LCDC
		else:
			# Clear LYC flag
			self.value &= 0b1111_1011
		return 0

	def set_mode(self, mode):
		if self._mode == mode:
			# Mode already set
			return 0
		self._mode = mode
		self.value &= 0b11111100 # Clearing 2 LSB
		self.value |= mode # Apply mode to LSB
		# Check if interrupt is enabled for this mode
		# Mode "3" is not interruptable
		if mode != 3 and self.value & (1 << (mode + 3)):
			return INTR_LCDC
		return 0

# 调色板
class PaletteRegister:
	def __init__(self, value):
		self.value = 0
		self.lookup = [0] * 4
		self.set(value)
		self.palette_mem_rgb = [0] * 4

	def set(self, value):
		# Pokemon Blue continuously sets this without changing the value
		if self.value == value:
			return False
		self.value = value
		for x in range(4):
			self.lookup[x] = (value >> x * 2) & 0b11
		return True

	def get(self):
		return self.value

	def getcolor(self, i):
		return self.palette_mem_rgb[self.lookup[i]]

# GameBoy图像处理器
class PPU:
	def __init__(self, color_palette):
		# 显存
		self.VRAM0 = array.array("B", [0] * VIDEO_RAM)
		self.OAM = array.array("B", [0] * OBJECT_ATTRIBUTE_MEMORY)
		# 寄存器
		self._LCDC = LCDCRegister(0)
		self._STAT = STATRegister() # Bit 7 is always set.
		# 状态变量
		self.SCY = 0x00
		self.SCX = 0x00
		self.LY = 0x00
		self.LYC = 0x00
		self.WY = 0x00
		self.WX = 0x00
		# 调色板
		self.BGP = PaletteRegister(0xFC)
		self.BGP.palette_mem_rgb = [(rgb_to_bgr(c)) for c in color_palette]
		self.OBP0 = PaletteRegister(0xFF)
		self.OBP0.palette_mem_rgb = [(rgb_to_bgr(c)) for c in color_palette]
		self.OBP1 = PaletteRegister(0xFF)
		self.OBP1.palette_mem_rgb = [(rgb_to_bgr(c)) for c in color_palette]
		# 内部变量
		self.next_stat_mode = 2
		self.disable_renderer = False
		self.clock = 0
		self.clock_target = 0
		self.frame_done = False
		# 渲染引擎
		self.render = Render(False)

	def tick(self, cycles):
		interrupt_flag = 0
		self.clock += cycles
		if self._LCDC.lcd_enable:
			if self.clock >= self.clock_target:
				# Change to next mode
				interrupt_flag |= self._STAT.set_mode(self.next_stat_mode)
				# Pan Docs:
				# The following are typical when the display is enabled:
				#   Mode 2  2_____2_____2_____2_____2_____2___________________2____
				#   Mode 3  _33____33____33____33____33____33__________________3___
				#   Mode 0  ___000___000___000___000___000___000________________000
				#   Mode 1  ____________________________________11111111111111_____
				multiplier = 1
				# LCD state machine
				if self._STAT._mode == 2: # Searching OAM
					if self.LY == 153:
						self.LY = 0
						self.clock %= FRAME_CYCLES
						self.clock_target %= FRAME_CYCLES
					else:
						self.LY += 1
					self.clock_target += 80 * multiplier
					self.next_stat_mode = 3
					interrupt_flag |= self._STAT.update_LYC(self.LYC, self.LY)
				elif self._STAT._mode == 3:
					self.clock_target += 170 * multiplier
					self.next_stat_mode = 0
				elif self._STAT._mode == 0: # HBLANK
					self.clock_target += 206 * multiplier
					self.render.scanline(self, self.LY)
					self.render.scanline_sprites(self, self.LY, self.render._screenbuffer, self.render._screenbuffer_attributes, False)
					if self.LY < 143:
						self.next_stat_mode = 2
					else:
						self.next_stat_mode = 1
				elif self._STAT._mode == 1: # VBLANK
					self.clock_target += 456 * multiplier
					self.next_stat_mode = 1
					self.LY += 1
					interrupt_flag |= self._STAT.update_LYC(self.LYC, self.LY)
					if self.LY == 144:
						interrupt_flag |= INTR_VBLANK
						self.frame_done = True
					if self.LY == 153:
						# Reset to new frame and start from mode 2
						self.next_stat_mode = 2
		else:
			# See also `self.set_lcdc`
			if self.clock >= FRAME_CYCLES:
				self.frame_done = True
				self.clock %= FRAME_CYCLES
				# Renderer
				self.render.blank_screen(self)
		return interrupt_flag

	def get_stat(self):
		return self._STAT.value

	def set_stat(self, value):
		self._STAT.set(value)

	def get_lcdc(self):
		return self._LCDC.value

	def set_lcdc(self, value):
		self._LCDC.set(value)
		if not self._LCDC.lcd_enable:
			# https://www.reddit.com/r/Gameboy/comments/a1c8h0/what_happens_when_a_gameboy_screen_is_disabled/
			# 1. LY (current rendering line) resets to zero. A few games rely on this behavior, namely Mr. Do! When LY
			# is reset to zero, no LYC check is done, so no STAT interrupt happens either.
			# 2. The LCD clock is reset to zero as far as I can tell.
			# 3. I believe the LCD enters Mode 0.
			self.clock = 0
			self.clock_target = FRAME_CYCLES # Doesn't render anything for the first frame
			self._STAT.set_mode(0)
			self.next_stat_mode = 2
			self.LY = 0

	def getwindowpos(self):
		return (self.WX - 7, self.WY)

	def getviewport(self):
		return (self.SCX, self.SCY)