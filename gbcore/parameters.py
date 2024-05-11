# -*- coding: utf-8 -*- 
#!/usr/bin/env python

VIDEO_RAM = 8 * 1024 # 8KB
OBJECT_ATTRIBUTE_MEMORY = 0xA0
INTR_VBLANK, INTR_LCDC, INTR_TIMER, INTR_SERIAL, INTR_HIGHTOLOW = [1 << x for x in range(5)]
FRAME_CYCLES = 70224


