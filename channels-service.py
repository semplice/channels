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

import dbus

import channels
import channels.common
import channels.objects

from channels.dbus_common import MainLoop, is_authorized

from dbus.mainloop.glib import DBusGMainLoop

# Set handler
channels.common.set_handler("DBus")

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
			bus=dbus.SystemBus()
		)
		
		super().__init__(self.bus_name)
		
		# Build child objects for every action namespace
		self._namespaces = {}
		for module in channels.__all__:
			mod = channels.common.load_module(module)
			self._namespaces[module] = type(
				module,
				(mod, channels.objects.BaseObject),
				dict(path="/org/semplicelinux/channels/%s" % module)
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
		
	DBusGMainLoop(set_as_default=True)
	clss = Service()
	
	# Ladies and gentlemen...
	MainLoop.run()
