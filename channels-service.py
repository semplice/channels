#!/usr/bin/python3
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

import os

os.environ["DEBIAN_FRONTEND"] = "gnome" # FIXME

import sys

import argparse

import logging
import logging.handlers

import dbus

import channels
import channels.common
import channels.objects

from channels.dbus_common import MainLoop, BUS, is_authorized

LOGPATH = "/var/log/channels/channels.log"

# Set handler
channels.common.set_handler("DBus")

logger = logging.getLogger()

class Service(channels.objects.BaseObject):
	"""
	The main object, exported to /org/semplicelinux/channels.
	"""
	
	path = "/org/semplicelinux/channels"

	def __init__(self):
		"""
		Initializes the object.
		"""
		
		self.bus_name = dbus.service.BusName(
			"org.semplicelinux.channels",
			bus=BUS
		)
		
		super().__init__(self.bus_name)
		
		# Build child objects for every action namespace
		self._namespaces = {}
		for module in channels.__all__:
			mod = channels.common.load_module(module)
			self._namespaces[module] = type(
				module,
				(mod, channels.objects.BaseObject),
				dict(
					path="/org/semplicelinux/channels/%s" % module,
					interface_name="org.semplicelinux.channels.%s" % module
				)
			)()
			# Perhaps super() is better?
			channels.objects.BaseObject.__init__(self._namespaces[module], self.bus_name)
						
			# Patch class' dbus table with informations on the module members,
			# to have them properly introspected.
			# This shouldn't be needed, so it's a FIXME
			
			self._dbus_class_table["__main__.%s" % module]["org.semplicelinux.channels.%s" % module] = {}
			
			for obj in channels.common.get_class_actions(mod):
				self._dbus_class_table["__main__.%s" % module]["org.semplicelinux.channels.%s" % module][obj.__name__] = obj

if __name__ == "__main__":

	# No root, no party
	if os.getuid() != 0:
		sys.stdout.write("ERROR: channels-service must be run as root.\n")
		sys.exit(1)

	# Parse arguments
	parser = argparse.ArgumentParser(description="Update channels management service")
	parser.add_argument(
		"-d", "--debug",
		action="store_true",
		help="enables debug mode"
	)
	args = parser.parse_args()

	# Set-up logging
	if not os.path.exists("/var/log/channels/"):
		os.mkdir("/var/log/channels", 0o755)
	
	formatter = logging.Formatter(
		"%(asctime)s %(name)s: [%(levelname)s:%(lineno)d] %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S"
	)
	
	logger.setLevel(logging.INFO if not args.debug else logging.DEBUG)
	
	# Rotated log, in /var/log/channels/channels.log(.X)
	# Defaults to INFO if debug is not activated.
	rotation_handler = logging.handlers.RotatingFileHandler(
		LOGPATH,
		maxBytes=1024 * 1024,
		backupCount=5
	)
	rotation_handler.setLevel(logging.INFO if not args.debug else logging.DEBUG)
	rotation_handler.setFormatter(formatter)
	
	# Stream log
	# Defaults to WARNING if debug is not activated
	stream_handler = logging.StreamHandler()
	stream_handler.setLevel(logging.WARNING if not args.debug else logging.DEBUG)
	stream_handler.setFormatter(formatter)
	
	logger.addHandler(rotation_handler)
	logger.addHandler(stream_handler)

	logger.info("Starting-up the service...")
	clss = Service()
	
	# Ladies and gentlemen...
	MainLoop.run()
