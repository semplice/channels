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

import sys

import importlib

import libchannels.discovery
import libchannels.resolver
import libchannels.actions

CURRENT_HANDLER = None

# Discovery
discovery = libchannels.discovery.ChannelDiscovery()
discovery.discover()

# Resolver
resolver = libchannels.resolver.DependencyResolver(discovery.cache)

# Actions
actions = libchannels.actions.Actions(discovery, resolver)

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

def get_class_actions(clss):
	"""
	Returns a list of available actions in the given class.
	"""
	
	return [
		y for x, y in clss.__dict__.items()
		if type(y) == FunctionType and not x.startswith("_") and hasattr(y, "__actionargs__")
	]
