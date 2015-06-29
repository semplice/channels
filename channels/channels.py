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

from channels.common import CURRENT_HANDLER, discovery, actions

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
			channel if CURRENT_HANDLER == "DBus" else (
				"%s%s" % (channel, " (enabled)" if obj.enabled else "")
			)
			for channel, obj in discovery.cache.items()
			if not channel.endswith(".provider")
		])
	
	@channels.actions.action(
		command="get-enabled",
		help="Returns \"True\" if the given channel is enabled, \"False\" otherwise",
		cli_output="print",
		in_signature="s",
		out_signature="b"
	)
	def GetEnabled(self, channel):
		"""
		Returns True if the given channel is enabled, False otherwise.
		"""
		
		return discovery.cache[channel].enabled if channel in discovery.cache and not channel.endswith(".provider") else False
	
	@channels.actions.action(
		command="get-details",
		help="Returns the requested details.",
		cli_output="keyvalue",
		cli_group_last=True,
		in_signature="sas",
		out_signature="a{ss}",
	)
	def GetDetails(self, channel, details):
		"""
		Returns the requested details.
		"""
		
		if not channel in discovery.cache or channel.endswith(".provider"):
			return {}
		
		return {detail:discovery.cache[channel]["channel"][detail] for detail in details if detail in discovery.cache[channel]["channel"]}
	
	@channels.actions.action(
		command="get-dependencies",
		help="Prints the dependencies of the given channel",
		cli_output="newline",
		in_signature="s",
		out_signature="as"
	)
	def GetDependencies(self, channel):
		"""
		Returns the dependencies of the given channel.
		"""
		
		return discovery.cache[channel].get_dependencies() if channel in discovery.cache else []
	
	@channels.actions.action(
		command="get-conflicts",
		help="Prints the conflicts of the given channel",
		cli_output="newline",
		in_signature="s",
		out_signature="as"
	)
	def GetConflicts(self, channel):
		"""
		Returns the conflicts of the given channel.
		"""
		
		return discovery.cache[channel].get_conflicts() if channel in discovery.cache else []
	
	@channels.actions.action(
		command="get-providers",
		help="Prints the providers the given channel provides",
		cli_output="newline",
		in_signature="s",
		out_signature="as"
	)
	def GetProviders(self, channel):
		"""
		Returns the providers the given channel provides.
		"""
		
		return discovery.cache[channel].get_providers() if channel in discovery.cache else []
