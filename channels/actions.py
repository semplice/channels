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
	outside_timeout = BaseObject.outside_timeout
else:
	outside_timeout = None

import os

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
				out_signature=out_signature
			)(obj) 

		def wrapper(*args, **kwargs):
			"""
			Method wrapper.
			"""
			
			if CURRENT_HANDLER == "cli" and root_required:
				# Check for root
				if not os.geteuid() == 0:
					error("This action is available only for privileged users.")
			
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
		wrapper.__actionargs__ = [x for x in obj.__code__.co_varnames[:obj.__code__.co_argcount] if not x in ["self",]]

		wrapper.__grouplast__ = cli_group_last
		wrapper.__command__ = command
		wrapper.__commandhelp__ = help
		
		return wrapper
	
	return decorator
