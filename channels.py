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

import channels
import channels.common

import argparse
import importlib

# Set handler
channels.common.set_handler("cli")

def show_actions():
	"""
	Outputs a list of supported actions, alongside their help messages.
	"""
	
	actions = {}
	for module in channels.__all__:
		mod = channels.common.load_module(module)
		
		actions[module] = [(x.__command__, x.__actionargs__, x.__commandhelp__) for x in channels.common.get_class_actions(mod)]
	
	print("""Available actions:

generic actions:
  show - Shows available actions

%(actions)s

""" % {
	# Sorry for this, but sometimes I need to have fun
	"actions": "\n\n".join(
		[
			"\n".join(
				["%s actions:" % module] + [
					"  %s%s%s" % (
						action[0],
						" [%s]" % ", ".join(action[1]) if action[1] else "",
						" - %s" % action[2] if action[2] else "",
					) for action in sorted(action_list)
				]
			) for module, action_list in actions.items()
		]
	)
})		

def execute_action(info):
	"""
	Executes the action given in the info list (typically args.action).
	
	Returns True when the action has been executed, False when it's not available.
	"""

	# Search for the action
	for module in channels.__all__:
		mod = channels.common.load_module(module)()
		members = {x.__command__:x for x in channels.common.get_class_actions(mod.__class__)}
		
		if info[0] in members:
			x = members[info[0]]
			getattr(mod, x.__name__)(
				*(
					(
						# If __grouplast__ is True, we should group the last items
						# in a single list.
						# This is the same as doing something like:
						#   def Action(self, arg1, arg2, *args)
						# (supplying "action arg1 arg2 arg3 arg4" will group arg3 and arg4 in a list),
						# but in a way that works too on DBus (it's not possible to use *args in dbus-python).
						info[1:len(x.__actionargs__)] + [info[len(x.__actionargs__):]]
						if x.__grouplast__ else info[1:] # Otherwise, business as usual.
					)
					if len(info) > 1 else []
				)
			)
			
			return True
	
	return False

# Handle arguments
parser = argparse.ArgumentParser(
	description="Update channels management front-end",
	epilog="Use \"%(prog)s show\" to show available actions.",
	usage="%(prog)s action [arguments...]"
)

# action
parser.add_argument(
	"action",
	nargs="+",
	help="the action to execute"
)

args = parser.parse_args()

if args.action[0] == "show":
	show_actions()
elif not execute_action(args.action):
	# Action not found
	channels.common.error("Action %s not found. Use \"show\" to show a list of available actions." % args.action[0])
