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

import dbus

import threading

import logging

from gi.repository import GLib, Polkit

from dbus.mainloop.glib import DBusGMainLoop

authority = Polkit.Authority.get_sync()

logger = logging.getLogger(__name__)

DBusGMainLoop(set_as_default=True)
BUS = dbus.SystemBus()

class LoopWithTimeout():
	"""
	A LoopWithTimeout is a GLibMainLoop that supports timeouts.
	
	We don't directly subclass GLib.MainLoop because we can't.
	"""
	
	def __init__(self, timeout_length):
		"""
		Initializes the loop.
		"""
		
		self.loop = GLib.MainLoop()
		
		self.connected_clients = []
		
		self.timeout = 0
		self.timeout_length = timeout_length
		
		self.add_timeout()
	
	def add_client(self, client):
		"""
		Adds a client to the connected_clients.
		"""
		
		logger.debug("Client %s connected" % client)
		self.connected_clients.append(client)
		
		# Subscribe to changes
		BUS.add_signal_receiver(
			handler_function=self.on_name_owner_changed,
			signal_name="NameOwnerChanged",
			dbus_interface="org.freedesktop.DBus",
			path="/org/freedesktop/DBus",
			arg0=client
		)

	def on_name_owner_changed(self, name, old_owner, new_owner):
		"""
		A callback for NameOwnerChanged that can be hooked on the bus.
		
		This callback is reponsible to update the self.connected_clients
		list so that the MainLoop stays aware of the connected clients.
		
		Note that this method doesn't do any filtering.
		"""
		
		if not name.startswith(":") or new_owner:
			# Us or new_owner (wtf), discard
			return
		
		if name in self.connected_clients:
			# Client disconnection
			logger.debug("Client %s disconnected" % name)
			self.connected_clients.remove(name)
			
			# Unsubscribe to changes
			BUS.remove_signal_receiver(
				handler_or_match=self.on_name_owner_changed,
				signal_name="NameOwnerChanged",
				dbus_interface="org.freedesktop.DBus",
				path="/org/freedesktop/DBus",
				arg0=old_owner
			)

	def on_timeout_elapsed(self):
		"""
		Fired when the timeout elapsed.
		"""
		
		if len(threading.enumerate()) > 1 or self.connected_clients:
			# Threads still running or there still are connected clients,
			# delay the timeout
			return True
		
		self.quit()
		
		return False
	
	def remove_timeout(self):
		"""
		Removes the timeout.
		"""

		if self.timeout > 0:
			# Timeout already present, cancel it
			GLib.source_remove(self.timeout)
			self.timeout = 0
	
	def add_timeout(self):
		"""
		Timeout.
		"""
		
		if not self.timeout:
			self.timeout = GLib.timeout_add_seconds(self.timeout_length, self.on_timeout_elapsed)
	
	def __getattr__(self, name):
		"""
		Proxy to the self.loop object.
		"""
		
		return getattr(self.loop, name)

def get_user(sender):
	"""
	Returns the user name of the given sender.
	"""
	
	return dbus.Interface(
		dbus.SystemBus().get_object(
			"org.freedesktop.DBus",
			"/org/freedesktop/DBus"
		),
		"org.freedesktop.DBus"
	).GetConnectionUnixUser(sender)

def is_authorized(sender, connection, privilege, user_interaction=True):
	"""
	Checks if the sender has the given privilege.
	
	Returns True if yes, False if not.
	"""
	
	if not user_interaction:
		flags = Polkit.CheckAuthorizationFlags.NONE
	else:
		flags = Polkit.CheckAuthorizationFlags.ALLOW_USER_INTERACTION
	
	# Get PID
	pid = dbus.Interface(
		dbus.SystemBus().get_object(
			"org.freedesktop.DBus",
			"/org/freedesktop/DBus"
		),
		"org.freedesktop.DBus"
	).GetConnectionUnixProcessID(sender)
		
	try:
		result = authority.check_authorization_sync(
			Polkit.UnixProcess.new(pid),
			privilege,
			None,
			flags,
			None
		)
	except:
		return False
	
	return result.get_is_authorized()

MainLoop = LoopWithTimeout(5 * 60)
