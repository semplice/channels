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

from channels.common import CURRENT_HANDLER, error

if CURRENT_HANDLER == "DBus":
	from channels.objects import BaseObject
	from channels.dbus_common import is_authorized
	import dbus.service
	outside_timeout = BaseObject.outside_timeout

import os

import types

def signal(
	signature=None
):
	
	"""
	Handles a DBus signal.
	If CURRENT_HANDLER != "DBus", the decorated method won't be available.
	"""
	
	def decorator(obj):
		"""
		Modifies the object.
		"""
		
		if CURRENT_HANDLER != "DBus":
			return None

		obj = dbus.service.signal(
			"org.semplicelinux.channels.%s" % obj.__module__.split(".")[-1], # Get the interface name from the module name
			signature=signature
		)(obj)
		
		# This is needed to make the signal detectable by common.get_class_actions()
		obj.__actionargs__ = []
		
		return obj
	
	return decorator

def action(
	root_required=False, # True to require additional privilegies
	polkit_privilege=None, # Privilege to be asked for when on DBus and root_required == True
	dbus_visible=True, # False to hide on DBus
	command=None, # None disables the method on cli handler
	help=None, # Help for the cli handler
	cli_output=None, # How to parse the output on the cli handler ("newline", "print", None)
	cli_group_last=False, # If True, the remaining args will be grouped in one (like *args does)
	in_signature="", # DBus in_signature
	out_signature="", # DBus out_signature
):
	
	"""
	Modifies the method in order to include settings for
	the action handler.
	"""
	
	def create_dbus_fixed_method(obj):
		"""
		When polkit authentication is required, the is_authorized() method
		requires both the sender and the connection objects, which aren't specified
		in the action.
		
		This function creates a clone of the supplied method with the sender
		and connection requirement.
		
		The authentication is handled transparently by this decorator -- actions
		should not attempt to manually verify if the sender is authenticated.
		"""
		
		return types.FunctionType(
			types.CodeType(
				obj.__code__.co_argcount + 2, # argcount of obj + sender and connection
				obj.__code__.co_kwonlyargcount,
				obj.__code__.co_nlocals,
				obj.__code__.co_stacksize,
				obj.__code__.co_flags,
				obj.__code__.co_code,
				obj.__code__.co_consts,
				obj.__code__.co_names,
				tuple(list(obj.__code__.co_varnames[:obj.__code__.co_argcount]) + ["sender", "connection"]),
				obj.__code__.co_filename,
				obj.__code__.co_name,
				obj.__code__.co_firstlineno,
				obj.__code__.co_lnotab,
				obj.__code__.co_freevars,
				obj.__code__.co_cellvars
			),
			obj.__globals__,
			obj.__name__,
			obj.__defaults__,
			obj.__closure__
		)
			
	def decorator(obj):
		"""
		Modifies the object.
		"""
		
		if (
			(CURRENT_HANDLER == "DBus" and not dbus_visible) or
			(CURRENT_HANDLER == "cli" and not command)
		):
			# Should hide
			return None
		
		# Wrap around outside_timeout if on DBus
		if CURRENT_HANDLER == "DBus":
			obj = outside_timeout(
				"org.semplicelinux.channels.%s" % obj.__module__.split(".")[-1], # Get the interface name from the module name
				in_signature=in_signature,
				out_signature=out_signature,
				sender_keyword="sender" if polkit_privilege else None,
				connection_keyword="connection" if polkit_privilege else None
			)(create_dbus_fixed_method(obj) if polkit_privilege else obj)

		def wrapper(*args, **kwargs):
			"""
			Method wrapper.
			"""
			
			if CURRENT_HANDLER == "cli" and root_required:
				# Check for root
				if not os.geteuid() == 0:
					error("This action is available only for privileged users.")
			elif CURRENT_HANDLER == "DBus" and polkit_privilege:
				
				if "sender" in kwargs and "connection" in kwargs:
					# If they are not, the method is called from the inside,
					# so do not check auth
					# FIXME: Should investigate more this type of thing
					# (is it still secure?)
					
					if not is_authorized(
						# We assume that both the sender and the connection are in kwargs
						kwargs["sender"],
						kwargs["connection"],
						polkit_privilege,
						True # user interaction
					):
						# No way
						raise Exception("Not authorized")
					
					# This is weird. Sender and connection are in kwargs BUT
					# we expect them in args. This makes the DBus call fail
					# due to varnames clashes.
					# We workaround this by putting sender and connection at the end of args,
					# and by deleting them from the kwargs.
					args = list(args) + [kwargs["sender"], kwargs["connection"]]
					del kwargs["sender"]
					del kwargs["connection"]
				else:
					# Insert fake sender and connections
					args = list(args) + [None, None]
			
			result = obj(*args, **kwargs)
			
			if CURRENT_HANDLER == "cli" and result != None:
				if cli_output == "print":
					print(result)
				elif cli_output == "newline":
					print("\n".join(result))
				elif cli_output == "keyvalue":
					for key, value in result.items():
						print("%s: %s" % (key, value))
			else:
				return result
		
		# Merge metadata
		wrapper.__name__ = obj.__name__
		wrapper.__dict__.update(obj.__dict__)

		# This should work only on CPython
		wrapper.__actionargs__ = [x for x in obj.__code__.co_varnames[:obj.__code__.co_argcount] if not x in ["self", "sender", "connection"]]

		wrapper.__grouplast__ = cli_group_last
		wrapper.__command__ = command
		wrapper.__commandhelp__ = help
		
		return wrapper
	
	return decorator
