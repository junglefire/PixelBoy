# -*- coding: utf-8 -*- 
#!/usr/bin/env python

# import PySDL2
from sdl2.ext import get_events
from sdl2 import *

P10, P11, P12, P13 = range(4)

def reset_bit(x, bit):
	return x & ~(1 << bit)

def set_bit(x, bit):
	return x | (1 << bit)

class Joypad:
	def __init__(self):
		self.directional = 0xF
		self.standard = 0xF

	def key_event(self, event):
		_directional = self.directional
		_standard = self.standard
		if event.type == SDL_KEYDOWN:
			if event.key.keysym.sym == SDLK_RIGHT:
				self.directional = reset_bit(self.directional, P10)
			elif event.key.keysym.sym == SDLK_LEFT:
				self.directional = reset_bit(self.directional, P11)
			elif event.key.keysym.sym == SDLK_UP:
				self.directional = reset_bit(self.directional, P12)
			elif event.key.keysym.sym == SDLK_DOWN:
				self.directional = reset_bit(self.directional, P13)
			elif event.key.keysym.sym == SDLK_a:
				self.standard = reset_bit(self.standard, P10)
			elif event.key.keysym.sym == SDLK_b:
				self.standard = reset_bit(self.standard, P11)
			elif event.key.keysym.sym == SDLK_BACKSPACE:
				self.standard = reset_bit(self.standard, P12)
			elif event.key.keysym.sym == SDLK_RETURN:
				self.standard = reset_bit(self.standard, P13)
			else:
				pass
		elif event.type == SDL_KEYUP:
			if event.key.keysym.sym == SDLK_RIGHT:
				self.directional = set_bit(self.directional, P10)
			elif event.key.keysym.sym == SDLK_LEFT:
				self.directional = set_bit(self.directional, P11)
			elif event.key.keysym.sym == SDLK_UP:
				self.directional = set_bit(self.directional, P12)
			elif event.key.keysym.sym == SDLK_DOWN:
				self.directional = set_bit(self.directional, P13)
			elif event.key.keysym.sym == SDLK_a:
				self.standard = set_bit(self.standard, P10)
			elif event.key.keysym.sym == SDLK_b:
				self.standard = set_bit(self.standard, P11)
			elif event.key.keysym.sym == SDLK_BACKSPACE:
				self.standard = set_bit(self.standard, P12)
			elif event.key.keysym.sym == SDLK_RETURN:
				self.standard = set_bit(self.standard, P13)
			else:
				pass
		# XOR to find the changed bits, AND it to see if it was high before.
		# Test for both directional and standard buttons.
		return ((_directional^self.directional)&_directional) or ((_standard^self.standard)&_standard)

	def pull(self, joystickbyte):
		P14 = (joystickbyte >> 4) & 1
		P15 = (joystickbyte >> 5) & 1
		# Bit 7 - Not used (No$GMB)
		# Bit 6 - Not used (No$GMB)
		# Bit 5 - P15 out port
		# Bit 4 - P14 out port
		# Bit 3 - P13 in port
		# Bit 2 - P12 in port
		# Bit 1 - P11 in port
		# Bit 0 - P10 in port
		# Guess to make first 4 and last 2 bits true, while keeping selected bits
		joystickByte = 0xFF & (joystickbyte | 0b11001111)
		if P14 and P15:
			pass
		elif not P14 and not P15:
			pass
		elif not P14:
			joystickByte &= self.directional
		elif not P15:
			joystickByte &= self.standard
		return joystickByte


