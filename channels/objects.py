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

from channels.dbus_common import MainLoop, is_authorized, get_user

import dbus
import dbus.service

from gi.repository import GLib, Polkit

# FIXME:
# Properties are not introspectable.
# Python DBus does not support properties OOTB unfortunately, so we end up
# with implementing the spec's Get(), GetAll(), Set() and PropertiesChanged()
# ourselves [1].
#
# While this works, having them introspectable would be a great thing.
# This of course needs some more work [2], and frankly I don't really care
# if those damn properties are introspectable or not! :D
#
# [1] http://stackoverflow.com/questions/3740903/python-dbus-how-to-export-interface-property
# [2] http://bazaar.launchpad.net/~laney/python-dbusmock/introspection-properties/view/head:/dbusmock/mockobject.py

class BaseObject(dbus.service.Object):
	"""
	A base object!
	"""
	
	# The DBus object path
	path = "/org/semplicelinux/channels/baseobject"
	
	# The DBus interface name
	interface_name = "org.semplicelinux.channels.baseobject"
	
	# The Polkit policy to use (None to disable authentication)
	polkit_policy = None
	
	# The properties to export to the Bus
	export_properties = []
	
	# The list of UIDs that can set properties without authentication.
	# NOTE: Please populate it from the __init__ method of your object!
	set_privileges = []

	def outside_timeout(*args, **kwargs):
		"""
		Decorator that ensures that the timeout doesn't elapse in the
		middle of our work.
		
		This mess of nested functions is needed because is not possible
		to use another decorator with @dbus.service.method. [1]
		We are then manually wrapping our decorator to python3-dbus's.
		
		[1] https://www.libreoffice.org/bugzilla/show_bug.cgi?id=22409
		"""
				
		def my_shiny_decorator(func):
		
			# Wrap the function around dbus.service.method
			func = dbus.service.method(*args, **kwargs)(func)
			
			def wrapper(self, *args, **kwargs):
													
				MainLoop.remove_timeout()
				result = func(self, *args, **kwargs)
				MainLoop.add_timeout()
				
				return result
			
			# Merge metadata, otherwise the method would not be
			# introspected
			wrapper.__name__ = func.__name__
			wrapper.__dict__.update(func.__dict__)
			wrapper.__module__ = wrapper.__module__
			
			return wrapper
		
		return my_shiny_decorator
	

	def __init__(self, bus_name):
		"""
		Initializes the object.
		"""
		
		super().__init__(bus_name, self.path)
	
	def store_property(self, name, value):
		"""
		Override this method to do things when the user changes
		a property.
		"""
		
		pass
	
	@outside_timeout(
		dbus_interface=dbus.PROPERTIES_IFACE,
		in_signature="ss",
		out_signature="v"
	)
	def Get(self, interface_name, property_name):
		"""
		An implementation of the Get() method of the
		properties interface.
		"""
		
		return self.GetAll(interface_name)[property_name]
	
	@outside_timeout(
		dbus_interface=dbus.PROPERTIES_IFACE,
		in_signature="s",
		out_signature="a{sv}"
	)
	def GetAll(self, interface_name):
		"""
		An implementation of the GetAll() method of the
		properties interface.
		"""
		
		if interface_name == self.interface_name:
			result = {}
			
			for prop in self.export_properties:
				try:
					result[prop.capitalize()] = getattr(self, prop)
				except:
					pass
			
			return result
		else:
			raise Exception(
				"org.semplicelinux.usersd.UnknownInterface",
				"The object does not implement the %s interface" % interface_name
			)
	
	@outside_timeout(
		dbus_interface=dbus.PROPERTIES_IFACE,
		in_signature="ssv",
		sender_keyword="sender",
		connection_keyword="connection"
	)
	def Set(self, interface_name, property_name, new_value, sender=None, connection=None):
		"""
		An implementation of the Set() method of the
		properties interface.
		"""
		
		if sender and connection and not get_user(sender) in self.set_privileges and (self.polkit_policy and not is_authorized(
			sender,
			connection,
			self.polkit_policy,
			True # user interaction
		)):
			raise Exception("E: Not authorized")
		
		self.store_property(property_name, new_value)
