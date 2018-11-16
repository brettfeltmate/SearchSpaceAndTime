# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

import klibs
from klibs import P
from klibs.KLConstants import STROKE_INNER, TK_S, NA, RC_COLORSELECT, RC_KEYPRESS
from klibs.KLUtilities import *
from klibs.KLKeyMap import KeyMap
from klibs.KLUserInterface import any_key, ui_request
from klibs.KLGraphics import fill, blit, flip, clear
from klibs.KLGraphics.KLDraw import *
from klibs.KLGraphics.colorspaces import const_lum as colors
from klibs.KLResponseCollectors import ResponseCollector
from klibs.KLEventInterface import TrialEventTicket as ET
from klibs.KLCommunication import message
from klibs.KLExceptions import TrialException
from klibs.KLTime import Stopwatch

# Import required external libraries
import sdl2
import time
import random
import math
import aggdraw # For drawing mask cells in a single texture
import numpy as np
from PIL import Image

# Define some useful constants
SPACE = "space"
TIME = "time"
HOMO = "homo"
HETERO = "hetero"
BLACK = (0,0,0,255)
WHITE = (255,255,255,255)

class SearchSpaceAndTime(klibs.Experiment):
	'''
	Spatial & temporal search paradigm
	2x2 design; varying distractor-distractor & target-distractor similarity
	Regardless of task, present target item to be found at beginning (block? trial?)

	Spatial search:
	Present arrays containing distractors & target, have Ss press a button once located
		RT: Time between presentation of array & response 

	Temporal search:
	Present RSVP stream containing distractors & target, have Ss press a button when they see the target
		RT: Time between presentation of target & response

	Varying d-d similarity:
		sample colours from wheel slices, the width of which determines their similarity
	
	Varying t-d similarity:
		When dissimilar, sample from region outside of distractor slice
		When similar, sample from within distractor slice
	'''

	def setup(self):
		# Stimulus sizes
		fix_thickness = deg_to_px(0.1)
		fix_size = deg_to_px(0.6)
		target_size = deg_to_px(2)

		# Initilize drawbjects
		self.target = Rectangle(width=target_size)

		self.search_rc = ResponseCollector(uses=RC_KEYPRESS)
		self.search_keymap = KeyMap(
			'target_found',
			['Space'],
			['target_found'],
			[sdl2.SDLK_SPACE]
		)

	def block(self):
		# Two block types: Spatial & temporal search
		# If constant w/n a block, determine target & distractor colouring here
		pass

	def setup_response_collector(self):
		self.search_rc.terminate_after = [60,TK_S]
		self.search_rc.keypress_listener.key_map = self.search_keymap
		self.search_rc.keypress_listener.interrupts = True

	def trial_prep(self):
		# Generate wheel to select colors from
		self.color_selector = ColorWheel(deg_to_px(3),rotation=random.randrange(0,360))
		self.target_angle = random.randrange(0,360)
		self.target_color = self.color_selector.color_from_angle(self.target_angle)

		self.target.fill = self.target_color

		self.target_distractor = HOMO
		self.distractor_distractor = HETERO
		self.cell_count = 64

		self.item_array = self.generate_array(self.cell_count, self.distractor_distractor, self.target_distractor)
		
		self.evm.register_ticket(ET("array_on", 1000))

		hide_mouse_cursor()
		self.present_target()

	def trial(self):
		# Wait 1s before presenting array
		while self.evm.before("array_on", True):
			ui_request()
		
		# Present array
		fill()
		blit(self.item_array, registration=5, location=P.screen_c)
		flip()

		# Start timing from presentation of array
		self.search_rc.collect()

		if len(self.search_rc.keypress_listener.responses):
			trial_rt = self.search_rc.keypress_listener.response(value=False,rt=True)
		else:
			trial_rt = 'NA'

		
		return {
			"block_num": P.block_number,
			"trial_num": P.trial_number,
			"search_type": "Spatial",
			"cell_count": self.cell_count,
			"target_distractor": self.target_distractor,
			"distractor_distractor": self.distractor_distractor,
			"trial_rt": trial_rt,
			"slice_lower_bound": self.slice_bounds[0] % 360,
			"slice_upper_bound": self.slice_bounds[1] % 360
		}
		clear()

	def trial_clean_up(self):
		self.search_rc.keypress_listener.reset()

	def clean_up(self):
		pass

	def present_target(self):
		fill()
		blit(self.target, location=P.screen_c, registration=5)
		flip()

	def generate_array(self, cell_count, distractor_distractor, target_distractor):
		# Randomly determine target's position within the array
		target_pos = [random.randint(0,7), random.randint(0,7)]
		# Determine wheel sections to sample colours from
		slice_width = 45 if distractor_distractor == HOMO else 90

		target_lower_padded = self.target_angle - 20
		target_upper_padded = self.target_angle + 20

		if target_distractor == HOMO:
			self.slice_bounds = [target_lower_padded-slice_width, 
								 target_upper_padded+slice_width]
		else:
			self.slice_bounds = [target_lower_padded+slice_width, 
								 target_upper_padded + slice_width*2]

		# Set array size
		array_size = deg_to_px(9)
		# Set cell size
		cell_size = array_size / (math.sqrt(cell_count)) # Array comprised of 64 cells arranged 8x8
		# Black outline around cells
		cell_outline_width = deg_to_px(.1)
		black_pen = aggdraw.Pen((0,0,0),cell_outline_width)
		# Initialize array for cells to be applied to
		canvas = Image.new('RGBA', [array_size,array_size], (0,0,0,0))
		array = aggdraw.Draw(canvas)

		# Generate cells
		for row in range(0,8):
			for col in range(0,8):
				# Determine coordinates of cell
				top_left = (row*cell_size, col*cell_size)
				bottom_right = ((row+1)*cell_size, (col+1)*cell_size)

				# Check if this is where the target should go
				if (row, col) == (target_pos[0],target_pos[1]):
					color_brush = aggdraw.Brush(tuple(self.target_color[:3]))
					# Create cell
					array.rectangle(
						(top_left[0], top_left[1], bottom_right[0], bottom_right[1]),
						black_pen,
						color_brush
					)
				else:
					cell_angle = random.randrange(self.slice_bounds[0], self.slice_bounds[1])
					cell_color = self.color_selector.color_from_angle(cell_angle)

					color_brush = aggdraw.Brush(tuple(cell_color[:3]))
					array.rectangle(
						(top_left[0], top_left[1], bottom_right[0], bottom_right[1]),
						black_pen,
						color_brush
					)
		# Apply cells to array
		array.flush()
		return np.asarray(canvas)


