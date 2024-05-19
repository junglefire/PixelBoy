# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import random
import ctypes
import array

COL0_FLAG = 0b01
BG_PRIORITY_FLAG = 0b10
ROWS, COLS = 144, 160
TILES = 384

class Render:
	def __init__(self, cgb):
		self.cgb = cgb
		self.color_format = "RGBA"
		self.buffer_dims = (ROWS, COLS)
		# Init buffers as white
		self._screenbuffer_raw = array.array("B", [0x00] * (ROWS*COLS*4))
		self._screenbuffer_attributes_raw = array.array("B", [0x00] * (ROWS*COLS))
		self._tilecache0_raw = array.array("B", [0x00] * (TILES*8*8*4))
		self._spritecache0_raw = array.array("B", [0x00] * (TILES*8*8*4))
		self._spritecache1_raw = array.array("B", [0x00] * (TILES*8*8*4))
		self.sprites_to_render = array.array("i", [0] * 10)
		self._tilecache0_state = array.array("B", [0] * TILES)
		self._spritecache0_state = array.array("B", [0] * TILES)
		self._spritecache1_state = array.array("B", [0] * TILES)
		self.clear_cache()
		# 内存条带化
		self._screenbuffer = memoryview(self._screenbuffer_raw).cast("I", shape=(ROWS, COLS))
		self._screenbuffer_attributes = memoryview(self._screenbuffer_attributes_raw).cast("B", shape=(ROWS, COLS))
		self._tilecache0 = memoryview(self._tilecache0_raw).cast("I", shape=(TILES * 8, 8))
		# OBP0 palette
		self._spritecache0 = memoryview(self._spritecache0_raw).cast("I", shape=(TILES * 8, 8))
		# OBP1 palette
		self._spritecache1 = memoryview(self._spritecache1_raw).cast("I", shape=(TILES * 8, 8))
		self._screenbuffer_ptr = ctypes.c_void_p(self._screenbuffer_raw.buffer_info()[0])
		self._scanlineparameters = [[0, 0, 0, 0, 0] for _ in range(ROWS)]
		self.ly_window = 0

	def _cgb_get_background_map_attributes(self, lcd, i):
		tile_num = lcd.VRAM1[i]
		palette = tile_num & 0b111
		vbank = (tile_num >> 3) & 1
		horiflip = (tile_num >> 5) & 1
		vertflip = (tile_num >> 6) & 1
		bg_priority = (tile_num >> 7) & 1
		return palette, vbank, horiflip, vertflip, bg_priority

	def scanline(self, lcd, y):
		bx, by = lcd.getviewport()	# (SCX, SCY)
		wx, wy = lcd.getwindowpos()	# (WX-7, WY)
		# TODO: Move to lcd class
		self._scanlineparameters[y][0] = bx
		self._scanlineparameters[y][1] = by
		self._scanlineparameters[y][2] = wx
		self._scanlineparameters[y][3] = wy
		self._scanlineparameters[y][4] = lcd._LCDC.tiledata_select
		if lcd.disable_renderer:
			return
		# All VRAM addresses are offset by 0x8000
		# Following addresses are 0x9800 and 0x9C00
		background_offset = 0x1800 if lcd._LCDC.backgroundmap_select == 0 else 0x1C00
		wmap = 0x1800 if lcd._LCDC.windowmap_select == 0 else 0x1C00
		# Used for the half tile at the left side when scrolling
		offset = bx & 0b111
		# Weird behavior, where the window has it's own internal line counter. It's only incremented whenever the
		# window is drawing something on the screen.
		if lcd._LCDC.window_enable and wy <= y and wx < COLS:
			self.ly_window += 1
		for x in range(COLS):
			if lcd._LCDC.window_enable and wy <= y and wx <= x:
				# 计算GameBoy屏幕上窗口区域中当前像素(x, y)对应的tile在VRAM(tile map memory) 中的地址。
				# 这个计算涉及了将屏幕坐标转换为窗口tile map中的tile索引。具体来说： 
				# wmap：这是窗口VRAM tile map的起始地址，它可以是0x1800或0x1C00，取决于LCDC寄存器中的设置
				# self.ly_window//8：根据窗口内部计数器ly_window(它表示从窗口顶部开始的行数)计算出的当前行号
				#		由于一个tile为8x8像素，所以需要除以8来得到tile行号
				# *32：每行有32个tile，因此，把上面得到的行号乘以32可以得到VRAM中对应的tile map行的起始地址
				# %0x400：VRAM的tile map区域大小为0x400(1024 bytes)，取模确保地址不会超出VRAM tile map的范围
				# (x-wx)//8：根据像素的屏幕横坐标以及窗口的横坐标(wx)计算所在tile的横坐标。由于每个tile为8 像素宽，
				#		所以像素坐标减去窗口左边界的值后除以 8 得到 tile 列索引
				# %32：与行的计算类似，确保列索引不会超出每行32个tile的范围
				# 将这些组合在一起，tile_addr表示了VRAM中，当前像素所在tile的实际地址。这个地址接着可用于查找背景色
				# 或图案以进行渲染。
				tile_addr = wmap + (self.ly_window)//8*32%0x400 + (x-wx)//8%32
				wt = lcd.VRAM0[tile_addr]
				# If using signed tile indices, modify index
				if not lcd._LCDC.tiledata_select:
					# (x ^ 0x80 - 128) to convert to signed, then
					# add 256 for offset (reduces to + 128)
					wt = (wt ^ 0x80) + 128
				bg_priority_apply = 0
				if self.cgb:
					palette, vbank, horiflip, vertflip, bg_priority = self._cgb_get_background_map_attributes(lcd, tile_addr)
					if vbank:
						self.update_tilecache1(lcd, wt, vbank)
						tilecache = self._tilecache1
					else:
						self.update_tilecache0(lcd, wt, vbank)
						tilecache = self._tilecache0
					xx = (7 - ((x-wx) % 8)) if horiflip else ((x-wx) % 8)
					yy = (8*wt + (7 - (self.ly_window) % 8)) if vertflip else (8*wt + (self.ly_window) % 8)
					pixel = lcd.bcpd.getcolor(palette, tilecache[yy, xx])
					col0 = (tilecache[yy, xx] == 0) & 1
					if bg_priority:
						# We hide extra rendering information in the lower 8 bits (A) of the 32-bit RGBA format
						bg_priority_apply = BG_PRIORITY_FLAG
				else:
					self.update_tilecache0(lcd, wt, 0)
					xx = (x-wx) % 8
					yy = 8*wt + (self.ly_window) % 8
					pixel = lcd.BGP.getcolor(self._tilecache0[yy, xx])
					col0 = (self._tilecache0[yy, xx] == 0) & 1
				self._screenbuffer[y, x] = pixel
				# COL0_FLAG is 1
				self._screenbuffer_attributes[y, x] = bg_priority_apply | col0
			# background_enable doesn't exist for CGB. It works as master priority instead
			elif (not self.cgb and lcd._LCDC.background_enable) or self.cgb:
				tile_addr = background_offset + (y+by) // 8 * 32 % 0x400 + (x+bx) // 8 % 32
				bt = lcd.VRAM0[tile_addr]
				# If using signed tile indices, modify index
				if not lcd._LCDC.tiledata_select:
					# (x ^ 0x80 - 128) to convert to signed, then
					# add 256 for offset (reduces to + 128)
					bt = (bt ^ 0x80) + 128
				bg_priority_apply = 0
				if self.cgb:
					palette, vbank, horiflip, vertflip, bg_priority = self._cgb_get_background_map_attributes(lcd, tile_addr)
					if vbank:
						self.update_tilecache1(lcd, bt, vbank)
						tilecache = self._tilecache1
					else:
						self.update_tilecache0(lcd, bt, vbank)
						tilecache = self._tilecache0
					xx = (7 - ((x+offset) % 8)) if horiflip else ((x+offset) % 8)
					yy = (8*bt + (7 - (y+by) % 8)) if vertflip else (8*bt + (y+by) % 8)
					pixel = lcd.bcpd.getcolor(palette, tilecache[yy, xx])
					col0 = (tilecache[yy, xx] == 0) & 1
					if bg_priority:
						# We hide extra rendering information in the lower 8 bits (A) of the 32-bit RGBA format
						bg_priority_apply = BG_PRIORITY_FLAG
				else:
					self.update_tilecache0(lcd, bt, 0)
					xx = (x+offset) % 8
					yy = 8*bt + (y+by) % 8
					pixel = lcd.BGP.getcolor(self._tilecache0[yy, xx])
					col0 = (self._tilecache0[yy, xx] == 0) & 1
				self._screenbuffer[y, x] = pixel
				self._screenbuffer_attributes[y, x] = bg_priority_apply|col0
			else:
				# If background is disabled, it becomes white
				self._screenbuffer[y, x] = lcd.BGP.getcolor(0)
				self._screenbuffer_attributes[y, x] = 0
		if y == 143:
			# Reset at the end of a frame. We set it to -1, so it will be 0 after the first increment
			self.ly_window = -1

	def sort_sprites(self, sprite_count):
		# Use insertion sort, as it has O(n) on already sorted arrays. This
		# functions is likely called multiple times with unchanged data.
		# Sort descending because of the sprite priority.
		for i in range(1, sprite_count):
			key = self.sprites_to_render[i] # The current element to be inserted into the sorted portion
			j = i - 1 # Index of the last element in the sorted portion of the array
			# Move elements of the sorted portion greater than the key to the right
			while j >= 0 and key > self.sprites_to_render[j]:
				self.sprites_to_render[j + 1] = self.sprites_to_render[j]
				j -= 1
			# Insert the key into its correct position in the sorted portion
			self.sprites_to_render[j + 1] = key

	def scanline_sprites(self, lcd, ly, buffer, buffer_attributes, ignore_priority):
		if not lcd._LCDC.sprite_enable or lcd.disable_renderer:
			return
		# Find the first 10 sprites in OAM that appears on this scanline.
		# The lowest X-coordinate has priority, when overlapping
		spriteheight = 16 if lcd._LCDC.sprite_height else 8
		sprite_count = 0
		for n in range(0x00, 0xA0, 4):
			y = lcd.OAM[n] - 16 # Documentation states the y coordinate needs to be subtracted by 16
			x = lcd.OAM[n + 1] - 8 # Documentation states the x coordinate needs to be subtracted by 8
			if y <= ly < y + spriteheight:
				# x is used for sorting for priority
				if self.cgb:
					self.sprites_to_render[sprite_count] = n
				else:
					self.sprites_to_render[sprite_count] = x << 16 | n
				sprite_count += 1
			if sprite_count == 10:
				break
		# Pan docs:
		# When these 10 sprites overlap, the highest priority one will appear above all others, etc. (Thus, no
		# Z-fighting.) In CGB mode, the first sprite in OAM ($FE00-$FE03) has the highest priority, and so on. In
		# Non-CGB mode, the smaller the X coordinate, the higher the priority. The tie breaker (same X coordinates) is
		# the same priority as in CGB mode.
		self.sort_sprites(sprite_count)
		for _n in self.sprites_to_render[:sprite_count]:
			if self.cgb:
				n = _n
			else:
				n = _n & 0xFF
			# n = self.sprites_to_render_n[_n]
			y = lcd.OAM[n] - 16 # Documentation states the y coordinate needs to be subtracted by 16
			x = lcd.OAM[n + 1] - 8 # Documentation states the x coordinate needs to be subtracted by 8
			tileindex = lcd.OAM[n + 2]
			if spriteheight == 16:
				tileindex &= 0b11111110
			attributes = lcd.OAM[n + 3]
			xflip = attributes & 0b00100000
			yflip = attributes & 0b01000000
			spritepriority = (attributes & 0b10000000) and not ignore_priority
			if self.cgb:
				palette = attributes & 0b111
				if attributes & 0b1000:
					self.update_spritecache1(lcd, tileindex, 1)
					if lcd._LCDC.sprite_height:
						self.update_spritecache1(lcd, tileindex + 1, 1)
					spritecache = self._spritecache1
				else:
					self.update_spritecache0(lcd, tileindex, 0)
					if lcd._LCDC.sprite_height:
						self.update_spritecache0(lcd, tileindex + 1, 0)
					spritecache = self._spritecache0
			else:
				# Fake palette index
				palette = 0
				if attributes & 0b10000:
					self.update_spritecache1(lcd, tileindex, 0)
					if lcd._LCDC.sprite_height:
						self.update_spritecache1(lcd, tileindex + 1, 0)
					spritecache = self._spritecache1
				else:
					self.update_spritecache0(lcd, tileindex, 0)
					if lcd._LCDC.sprite_height:
						self.update_spritecache0(lcd, tileindex + 1, 0)
					spritecache = self._spritecache0
			dy = ly - y
			yy = spriteheight - dy - 1 if yflip else dy
			for dx in range(8):
				xx = 7 - dx if xflip else dx
				color_code = spritecache[8*tileindex + yy, xx]
				if 0 <= x < COLS and not color_code == 0: # If pixel is not transparent
					if self.cgb:
						pixel = lcd.ocpd.getcolor(palette, color_code)
						bgmappriority = buffer_attributes[ly, x] & BG_PRIORITY_FLAG

						if lcd._LCDC.cgb_master_priority: # If 0, sprites are always on top, if 1 follow priorities
							if bgmappriority: # If 0, use spritepriority, if 1 take priority
								if buffer_attributes[ly, x] & COL0_FLAG:
									buffer[ly, x] = pixel
							elif spritepriority: # If 1, sprite is behind bg/window. Color 0 of window/bg is transparent
								if buffer_attributes[ly, x] & COL0_FLAG:
									buffer[ly, x] = pixel
							else:
								buffer[ly, x] = pixel
						else:
							buffer[ly, x] = pixel
					else:
						# TODO: Unify with CGB
						if attributes & 0b10000:
							pixel = lcd.OBP1.getcolor(color_code)
						else:
							pixel = lcd.OBP0.getcolor(color_code)

						if spritepriority: # If 1, sprite is behind bg/window. Color 0 of window/bg is transparent
							if buffer_attributes[ly, x] & COL0_FLAG: # if BG pixel is transparent
								buffer[ly, x] = pixel
						else:
							buffer[ly, x] = pixel
				x += 1
			x -= 8

	def clear_cache(self):
		self.clear_tilecache0()
		self.clear_spritecache0()
		self.clear_spritecache1()

	def invalidate_tile(self, tile, vbank):
		if vbank and self.cgb:
			self._tilecache0_state[tile] = 0
			self._tilecache1_state[tile] = 0
			self._spritecache0_state[tile] = 0
			self._spritecache1_state[tile] = 0
		else:
			self._tilecache0_state[tile] = 0
			if self.cgb:
				self._tilecache1_state[tile] = 0
			self._spritecache0_state[tile] = 0
			self._spritecache1_state[tile] = 0

	def clear_tilecache0(self):
		for i in range(TILES):
			self._tilecache0_state[i] = 0

	def clear_tilecache1(self):
		pass

	def clear_spritecache0(self):
		for i in range(TILES):
			self._spritecache0_state[i] = 0

	def clear_spritecache1(self):
		for i in range(TILES):
			self._spritecache1_state[i] = 0

	def color_code(self, byte1, byte2, offset):
		"""Convert 2 bytes into color code at a given offset.
		The colors are 2 bit and are found like this:
		Color of the first pixel is 0b10
		| Color of the second pixel is 0b01
		v v
		1 0 0 1 0 0 0 1 <- byte1
		0 1 1 1 1 1 0 0 <- byte2
		"""
		return (((byte2 >> (offset)) & 0b1) << 1) + ((byte1 >> (offset)) & 0b1)

	def update_tilecache0(self, lcd, t, bank):
		if self._tilecache0_state[t]:
			return
		# for t in self.tiles_changed0:
		for k in range(0, 16, 2): # 2 bytes for each line
			byte1 = lcd.VRAM0[t*16 + k]
			byte2 = lcd.VRAM0[t*16 + k + 1]
			y = (t*16 + k) // 2
			for x in range(8):
				colorcode = self.color_code(byte1, byte2, 7 - x)
				self._tilecache0[y, x] = colorcode
		self._tilecache0_state[t] = 1

	def update_tilecache1(self, lcd, t, bank):
		pass

	def update_spritecache0(self, lcd, t, bank):
		if self._spritecache0_state[t]:
			return
		# for t in self.tiles_changed0:
		for k in range(0, 16, 2): # 2 bytes for each line
			byte1 = lcd.VRAM0[t*16 + k]
			byte2 = lcd.VRAM0[t*16 + k + 1]
			y = (t*16 + k) // 2

			for x in range(8):
				colorcode = self.color_code(byte1, byte2, 7 - x)
				self._spritecache0[y, x] = colorcode

		self._spritecache0_state[t] = 1

	def update_spritecache1(self, lcd, t, bank):
		if self._spritecache1_state[t]:
			return
		# for t in self.tiles_changed0:
		for k in range(0, 16, 2): # 2 bytes for each line
			byte1 = lcd.VRAM0[t*16 + k]
			byte2 = lcd.VRAM0[t*16 + k + 1]
			y = (t*16 + k) // 2

			for x in range(8):
				colorcode = self.color_code(byte1, byte2, 7 - x)
				self._spritecache1[y, x] = colorcode

		self._spritecache1_state[t] = 1

	def blank_screen(self, lcd):
		# If the screen is off, fill it with a color.
		for y in range(ROWS):
			for x in range(COLS):
				self._screenbuffer[y, x] = lcd.BGP.getcolor(0)
				self._screenbuffer_attributes[y, x] = 0


