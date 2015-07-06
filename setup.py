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

from distutils.core import setup

setup(
	name='channels',
	version='0.1.0',
	description='Update channels management front-end',
	author='Eugenio Paolantonio',
	author_email='me@medesimo.eu',
	url='https://github.com/semplice/channels',
	scripts=[
		'channels.py',
		'channels-service.py'
	],
	packages=[
		'channels'
	],
	data_files=[
		("/etc/dbus-1/system.d", ["dbus/org.semplicelinux.channels.conf"]),
		("/usr/share/polkit-1/actions", ["dbus/org.semplicelinux.channels.policy"]),
		("/usr/share/dbus-1/system-services", ["dbus/org.semplicelinux.channels.service"])
	],
	requires=[
		'argparse',
		'importlib',
		'os',
		'types',
		'dbus',
		'threading',
		'gi.repository.GLib',
		'gi.repository.Polkit',
		'libchannels'
	]
)
