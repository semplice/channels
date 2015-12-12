# -*- coding: utf-8 -*-
#
# channels - Update channels management front-end
# Copyright (C) 2015  Eugenio "g7" Paolantonio <me@medesimo.eu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# Authors:
#    Eugenio "g7" Paolantonio <me@medesimo.eu>
#

from types import FunctionType

import os

import sys

import shutil

import importlib

import threading

import libchannels.discovery
import libchannels.resolver
import libchannels.actions
import libchannels.updates

CURRENT_HANDLER = None

# Discovery
discovery = libchannels.discovery.ChannelDiscovery()
discovery.discover()

# Resolver
resolver = libchannels.resolver.DependencyResolver(discovery.cache)

# Actions
actions = libchannels.actions.Actions(discovery, resolver)

# Updates
updates = libchannels.updates.Updates()

def create_rotated_log(logfile, maximum=5):
	"""
	Creates a rotated log file and returns its file descriptor.
	
	This is a pretty simple routine, which doesn't perform size-checks
	like logging's handler does.
	
	Note: the containing directory must be already present.
	
	`logfile` is the full log file path.
	"""
	
	# Remove the most older file, if present
	older = logfile + ".%s" % maximum
	if os.path.exists(older):
		os.remove(older)
	
	# Now rotate everything else
	for i in range(maximum-1, -1, -1):
		log = logfile + ".%s" % i if not i == 0 else logfile
		if os.path.exists(log):
			shutil.move(log, logfile + ".%s" % (i+1))
	
	# Finally create the descriptor and return it
	return os.open(logfile, os.O_RDWR | os.O_CREAT)

def thread():
	
	"""
	Function decorator that ease the creation of threaded methods.
	"""
	
	def decorator(obj):
		"""
		Modifies the object.
		"""
		
		if not obj:
			return None
		
		def wrapper(*args, **kwargs):
			"""
			The function wrapper.
			"""
			
			threading.Thread(target=obj, args=args, kwargs=kwargs).start()
		
		# Merge metadata
		wrapper.__name__ = obj.__name__
		wrapper.__dict__.update(obj.__dict__)
		
		return wrapper if not CURRENT_HANDLER == "cli" else obj
	
	return decorator

def error(message, exit=1):
	"""
	Prints an error message, and exits (if exit != None).
	"""
	
	sys.stderr.write("%s: error: %s\n" % (sys.argv[0], message))
	if exit != None:
		sys.exit(exit)

def set_handler(handler):
	"""
	Sets the CURRENT_HANDLER property.
	"""
	
	global CURRENT_HANDLER
	
	CURRENT_HANDLER = handler if handler in ("DBus", "cli") else None

def load_module(name):
	"""
	Loads a module, and returns its core class.
	"""
	
	return getattr(importlib.import_module("channels.%s" % name), name.capitalize())

def get_class_actions(clss, with_internals=True):
	"""
	Returns a list of available actions in the given class.
	"""
	
	return [
		y for x, y in clss.__dict__.items()
		if type(y) == FunctionType and not x.startswith("_") and hasattr(y, "__actionargs__") and (not with_internals and not getattr(y, "__internal__") or with_internals)
	]
