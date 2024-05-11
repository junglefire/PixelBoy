# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as logger
import click

import gbcore as gb

# parse command line
@click.command()
@click.option('--filename', type=str, required=True, help='GameBoy ROM file')
@click.option('--debug', type=bool, required=False, is_flag=True, help='print debug log information')
def main(filename: str, debug: bool) -> None:
	if debug:
		logger.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s', level=logger.DEBUG)
	else:
		logger.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s', level=logger.INFO)
	# Application
	emu = gb.Emulator()
	emu.load(filename)

if __name__ == "__main__":
	main()
