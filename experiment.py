# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

import klibs
from klibs import P
from klibs.KLConstants import STROKE_CENTER, TK_S, NA, RC_KEYPRESS, RECT_BOUNDARY
from klibs.KLUtilities import *
from klibs.KLKeyMap import KeyMap
from klibs.KLUserInterface import any_key, ui_request
from klibs.KLGraphics import fill, blit, flip, clear
from klibs.KLGraphics.KLDraw import *
from klibs.KLGraphics.colorspaces import const_lum as colors
from klibs.KLResponseCollectors import *
from klibs.KLEventInterface import TrialEventTicket as ET
from klibs.KLCommunication import message
from klibs.KLExceptions import TrialException
from klibs.KLTime import Stopwatch, CountDown, precise_time

# Import required external libraries
import sdl2
import time
import random
import math


# Define some useful constants
SPACE = "space"
TIME = "time"
HOMO = "homo"
HETERO = "hetero"
COLOR = "color"
LINE = "line"
BLACK = (0,0,0,255)
WHITE = (255,255,255,255)

class SearchSpaceAndTime(klibs.Experiment):

	def setup(self):
		# Stimulus sizes
		fix_thickness = deg_to_px(0.1)
		fix_size = deg_to_px(0.6)
		self.item_size = deg_to_px(1)
		self.item_thickness = deg_to_px(.1)

		# Initilize drawbjects
		self.fixation = FixationCross(fix_size, fix_thickness, fill=WHITE)
		
		self.spatial_rc = ResponseCollector(uses=[CursorResponse])
		self.temporal_rc = ResponseCollector(uses=[MouseButtonResponse], flip_screen=True)
		

		self.stimulus_type = LINE
		self.search_type  = TIME

		self.item_duration = .1 # seconds
		self.isi = .05  # seconds
		self.rsvp_stream = []
		self.temporal_presentation_times = [] # populated at trial time and reset in trial_cleanup
		self.temporal_responses = []		  # populated at trial time and reset in trial_cleanup

	def block(self):
		self.cell_count = 64
		self.target_distractor = HETERO
		self.distractor_distractor = HETERO

		self.create_stimuli(self.stimulus_type)
		

	def setup_response_collector(self):
		self.spatial_rc.terminate_after = [10, TK_S]
		self.spatial_rc.cursor_listener.interrupts = True 
		#self.spatial_rc.display_refresh = self.present_array()

		self.temporal_rc.terminate_after = [99999, TK_S]
		# self.temporal_rc.mousebutton_listener.key_map = self.temporal_keymap #probably trash, was just used in debugging, kept around in case the 
		self.temporal_rc.mousebutton_listener.interrupts = False 
		self.temporal_rc.mousebutton_listener.max_response_count = 999
		self.temporal_rc.display_callback = self.present_stream

	def trial_prep(self):
		if self.search_type == SPACE:
			array_radius = deg_to_px(4.5)
			theta = 360.0 / self.cell_count

			self.item_locs = []

			for i in range(1, self.cell_count+1):
				self.item_locs.append(point_pos(origin=P.screen_c, amplitude=array_radius, angle=0, rotation=theta*i))

			random.shuffle(self.item_locs)
			self.target_loc = self.item_locs.pop()

			self.target_bounds = [
				point_pos(self.target_loc, amplitude=self.item_size/2, angle=0, rotation=135),
				point_pos(self.target_loc, amplitude=self.item_size/2, angle=0, rotation=315)
			]
		
			self.spatial_rc.cursor_listener.add_boundary('target_boundary', self.target_bounds, RECT_BOUNDARY)
		else:
			self.rsvp_stream = self.prepare_stream()
			self.rsvp_stream.reverse() # items are extracted via pop() in present_stream() 


		events = [[1000, 'present_target']]
		events.append([events[-1][0] + 1000, 'present_fixation'])
		events.append([events[-1][0] + 1000, 'search_onset'])
		
		for e in events:
			self.evm.register_ticket(ET(e[1], e[0]))

		hide_mouse_cursor()
		self.present_target()


	def trial(self):					
		# Wait 1s before presenting array
		while self.evm.before("present_fixation", True):
			ui_request()

		self.present_fixation()

		while self.evm.before("search_onset", True):
			ui_request()
		

		if self.search_type == SPACE:
			self.present_array()
			self.spatial_rc.collect()


			if len(self.spatial_rc.cursor_listener.responses):
				spatial_located, spatial_rt = self.spatial_rc.cursor_listener.response()
			else:
				spatial_located = 'miss'
				spatial_rt = 'NA'
		else:
			try:
				# the display callback "present_stream()" pops an element each pass; when all targets have been shown this bad boy throws an error
				self.temporal_rc.collect()
			except IndexError:
				self.temporal_responses = self.temporal_rc.mousebutton_listener.responses

		
		trial_data = {
			"block_num": P.block_number,
			"trial_num": P.trial_number,
			"search_type": "Spatial",
			"cell_count": self.cell_count,
			"target_distractor": self.target_distractor,
			"distractor_distractor": self.distractor_distractor,
		}
		for tpt in self.temporal_presentation_times:
			onset_key = 't{0}_onset'.format(self.temporal_presentation_times.index(tpt)+1)
			onset_val = tpt[0]
			dist_count_key = 't{0}_distractor_count'.format(self.temporal_presentation_times.index(tpt)+1)
			dist_count_val = tpt[1]
			trial_data[onset_key] = onset_val
			trial_data[dist_count_key] = dist_count_val
		return trial_data
		clear()

	def trial_clean_up(self):
		self.spatial_rc.cursor_listener.reset()
		self.temporal_rc.mousebutton_listener.reset()
		
		# log responses to database
		for tr in self.temporal_responses:
			self.database.insert({
				'trial_num': P.trial_number,
				'rt': tr.rt,
				'target_loc': NA
			}, 'responses')

		
		self.temporal_responses = []
		self.temporal_presentation_times = []


	def clean_up(self):
		pass

	def present_target(self):
		msg = "This is your target!"
		msg_loc = [P.screen_c[0], (P.screen_c[1] - deg_to_px(2))]

		fill()
		message(msg, location=msg_loc, registration=5)
		blit(self.target_item, location=P.screen_c, registration=5)
		flip()

	def present_fixation(self):
		fill()
		blit(self.fixation, location=P.screen_c, registration=5)
		flip()

	def create_stimuli(self, stimulus_type):
		if stimulus_type == COLOR:
		# Generate wheel to select colors from
			self.color_selector = ColorWheel(deg_to_px(1),rotation=random.randrange(0,360))
			
			# Select target colouring
			self.target_color = self.color_selector.color_from_angle(0)
			self.target_item = Rectangle(width=self.item_size, fill=self.target_color)

			# Select distractor colourings
			ref_angle = 20 if self.target_distractor == HOMO else 150
			bound = 1 if self.distractor_distractor == HOMO else 4

			self.distractor_fills = []
			for i in range(0,bound):
				self.distractor_fills.append(self.color_selector.color_from_angle( ref_angle+(20*i) ))

			# Now that we have our colouring, create stimuli
			
			self.distractors = []
			for f in self.distractor_fills:
				self.distractors.append(Rectangle(width=self.item_size, fill=f))
		else:

			self.target_item = Rectangle(self.item_size, self.item_thickness, fill=BLACK, rotation=45)

			ref_angle = 45 if self.target_distractor == HOMO else 135
			bound = 1 if self.distractor_distractor == HOMO else 4

			self.distractor_tilts = []
			for i in range(0, bound):
				self.distractor_tilts.append(ref_angle + (i * 5))

			self.distractors = []
			for t in self.distractor_tilts:
				self.distractors.append(Rectangle(self.item_size, self.item_thickness, fill=BLACK, rotation=t))

	def present_array(self):

		fill()
		self.bounds = Rectangle(width=self.item_size, stroke=[self.item_thickness, WHITE, STROKE_INNER])
		blit(self.target_item, registration=5, location=self.target_loc)
		blit(self.bounds, registration=5, location=self.target_loc)
		blit(self.fixation, registration=5, location=P.screen_c)
		for loc in self.item_locs:
			blit(random.choice(self.distractors), registration=5, location=loc)
		flip()
		show_mouse_cursor()
		mouse_pos(position=P.screen_c)

	def prepare_stream(self):
		target_counter = 0
		stream_items = []

		while not target_counter == 15:
			distractor_count = random.randint(5,10)
			for i in range(distractor_count):
				stream_items.append([random.choice(self.distractors), False, None])
			stream_items.append([self.target_item, True, distractor_count])
			target_counter += 1

		return stream_items
	

	def present_stream(self):
		duration_cd = CountDown(self.item_duration)
		isi_cd = CountDown(self.isi)
		item = self.rsvp_stream.pop()
		fill()
		blit(item[0], registration=5, location=P.screen_c)
		flip()

		duration_cd.reset()
		while duration_cd.counting():
			pass
		
		fill()

		if item[1]:
			self.temporal_presentation_times.append([self.evm.trial_time_ms, item[2]])
		isi_cd.reset()
		while isi_cd.counting():
			pass

	