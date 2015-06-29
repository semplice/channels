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

import dbus.service
from channels.objects import BaseObject

from channels.common import discovery, actions

import channels.actions

class Channels:
	
	"""
	This class manages channels.
	"""
	
	def __init__(self):
		"""
		Initializes the class.
		"""
		
		# This is volountairly left blank because otherwise a possible
		# __init__ from another class may take over when creating a mix-in.
		
		pass

	@dbus.service.method(
		"org.semplicelinux.usersd.group",
		out_signature="a{i(s)}",
		sender_keyword="sender",
		connection_keyword="connection"
	)
	def GetGroups(self, sender, connection):
		"""
		This method returns a dictionary containing every group's GID as keys,
		and the groupname as values.
		"""
		
		result = {}
					
		for group, obj in self._groups.items():
			result[obj.gid] = (group,)
		
		return result

	@channels.actions.action(
		root_required=True,
		command="enable",
		help="Enables a channel",
		in_signature="s"
	)
	def Enable(self, channel):
		"""
		Enables a channel.
		"""
		
		return actions.enable_channel(channel)
	
	@channels.actions.action(
		root_required=True,
		command="disable",
		help="Disables a channel",
		in_signature="s"
	)
	def Disable(self, channel):
		"""
		Disables a channel.
		"""
		
		return actions.disable_channel(channel)
	
	@channels.actions.action(
		command="list",
		help="Lists every available channel",
		cli_output="newline",
		out_signature="as"
	)
	def List(self):
		"""
		Lists every available channel.
		"""
		
		return sorted([
			"%s%s" % (channel, " (enabled)" if obj.enabled else "")
			for channel, obj in discovery.cache.items()
			if not channel.endswith(".provider")
		])
	
	@channels.actions.action(
		command="query-enabled",
		help="Returns \"True\" if the given channel is enabled, \"False\" otherwise.",
		cli_output="print",
		in_signature="s",
		out_signature="b"
	)
	def QueryEnabled(self, channel):
		"""
		Returns True if the given channel is enabled, False otherwise.
		"""
		
		return discovery.cache[channel].enabled if channel in discovery.cache and not channel.endswith(".provider") else False
