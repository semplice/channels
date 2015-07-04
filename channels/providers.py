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

from channels.common import CURRENT_HANDLER, discovery, actions

import channels.actions

class Providers:
	
	"""
	This class manages providers.
	"""

	def __init__(self):
		"""
		Initializes the class.
		"""
		
		# This is volountairly left blank because otherwise a possible
		# __init__ from another class may take over when creating a mix-in.
		
		pass
	
	@channels.actions.action(
		command="list-providers",
		help="Lists every available provider",
		cli_output="newline",
		out_signature="as"
	)
	def List(self):
		"""
		Lists every available channel.
		"""
		
		return sorted([
			provider
			for provider, obj in discovery.cache.items()
			if provider.endswith(".provider")
		])
	
	@channels.actions.action(
		command="what-provides",
		help="Lists every channel that provides the given provider",
		cli_output="newline",
		in_signature="s",
		out_signature="as"
	)
	def WhatProvides(self, provider):
		"""
		Lists every channel that proides the given provider.
		"""
		
		if not provider.endswith(".provider"): provider += ".provider"
		
		return sorted([
			channel if CURRENT_HANDLER == "DBus" else (
				"%s%s" % (channel, " (enabled)" if obj.enabled else "")
			)
			for channel, obj in discovery.cache.items()
			if not channel.endswith(".provider") and provider in obj.get_providers()
		])
