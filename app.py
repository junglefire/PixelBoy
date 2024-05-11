# -*- coding: utf-8 -*- 
#!/usr/bin/env python
import logging as logger
import click

from emulator import Emulator

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
	emu = Emulator()
	emu.load(filename)
	emu.run()

if __name__ == "__main__":
	main()
