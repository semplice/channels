# -*- coding: utf-8 -*-
#
# channels - Update channel management front-end
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

import channels.common
from channels.common import CURRENT_HANDLER, updates

if CURRENT_HANDLER == "DBus":
	from channels.dbus_common import get_user
else:
	get_user = lambda x: None

import channels.actions

import apt.progress.base, apt.progress.text

import os

import sys

import shutil

import math

import logging

import pwd

from apt_pkg import size_to_str

from threading import Lock

logger = logging.getLogger(__name__)

# Progress reporting
#updates.cache_progress = apt.progress.text.OpProgress()
#updates.acquire_progress = apt.progress.text.AcquireProgress()

APT_LOGFILE = "/var/log/channels/systemupdate.log"

class DBusOpProgress(apt.progress.base.OpProgress):
	"""
	An OpProgress variant ready to be used on DBus.
	"""
	
	def __init__(self, on_changed, on_done):
		"""
		Initializes the class.
		"""
		
		super().__init__()
		
		self.on_changed = on_changed
		self.on_done = on_done
	
	def done(self):
		"""
		Fires the signal, with 100 as percentage.
		"""
		
		self.on_done()
	
	def update(self):
		"""
		Fires the signal with the current percentage.
		"""
		
		if self.major_change:
			self.on_changed(self.op, self.subop, self.percent)

class DBusAcquireProgress(apt.progress.base.AcquireProgress):
	"""
	An AcquireProgress variant ready to be used on DBus.
	"""
	
	def __init__(self, on_start, on_stop, on_done, on_fail, on_fetch):
		"""
		Initializes the class.
		"""
		
		super().__init__()
		
		self.on_start = on_start
		self.on_stop = on_stop
		self.on_done = on_done
		self.on_fail = on_fail
		self.on_fetch = on_fetch
		
		self.stop_requested = False
	
	def start(self):
		"""
		Fires the on_start signal.
		"""
		
		self.on_start()
		
		self._current_id = 0
	
	def stop(self):
		"""
		Fires the on_stop signal.
		"""
		
		self.on_stop()
	
	def done(self, item):
		"""
		Fires the done signal.
		"""
		
		# Skip items without id
		if item.owner.id == 0:
			return
		
		self.on_done(item.owner.id)
	
	def fail(self, item):
		"""
		Fires the fail signal.
		"""
		
		# Skip items without id
		if item.owner.id == 0:
			# FIXME: This should be logged!
			return
		
		self.on_fail(item.owner.id)
	
	def fetch(self, item):
		"""
		Fires the fetch signal.
		"""
		
		# Set an id only if missing
		if item.owner.id == 0:
			self._current_id += 1
			item.owner.id = self._current_id
		
		self.on_fetch(item.owner.id, item.description, item.shortdesc)
	
	def pulse(self, owner):
		"""
		Determines if the acquire process should continue.
		"""
		
		if self.stop_requested:
			self.stop_requested = False
			return False
		
		return True	

class DBusInstallProgress(apt.progress.base.InstallProgress):
	"""
	An InstallProgress variant ready to be used on DBus.
	"""
	
	def __init__(self, on_start, on_finish, on_progress_changed, on_status_changed):
		"""
		Initializes the class.
		"""
		
		super().__init__()
		
		self.last_progress = 0.0
		
		self.on_start = on_start
		self.on_finish = on_finish
		self.on_progress_changed = on_progress_changed
		self.on_status_changed = on_status_changed
		
		self.display = None
		self.xauthority = None
	
	def queue_display_settings(self, display, uid):
		"""
		Queues display settings.
		"""
		
		self.display = display
		
		# Get XAUTHORITY
		try:
			self.xauthority = os.path.join(pwd.getpwuid(uid).pw_dir, ".Xauthority")
		except Exception as err:
			logger.warning("Unable to get Xauthority path: %s" % err)
			self.xauthority = None
	
	def start_update(self):
		""""
		Fires the start signal.
		"""
		
		self.on_start()
	
	def finish_update(self):
		"""
		Fires the finish signal.
		"""
		
		self.on_finish()
	
	def status_change(self, pkg, percent, status):
		"""
		Fires the status_change signal.
		"""
		
		if not percent == self.last_progress:
			self.on_progress_changed(percent)
		
		self.on_status_changed(pkg, status)
	
	def fork(self):
		"""
		Forks a child process so that apt can be launched in there.
		"""
		
		# apt_pkg is an external C(++) extension, and thus it doesn't
		# use Python's sys.std{out,err}.
		# Capturing its output is unfortunately needed.
		#
		# Stream redirection in these cases should be done at low-level,
		# but it's not easily possible to redirect them in-memory in order
		# to re-route them again to the logger.
		#
		# We will let apt write directly to another file descriptor,
		# by redirecting std{out,err} to the APT_LOGFILE's descriptor.
		#
		# We won't restore the redirection as eventually the fork will
		# die.
		# The only catch is that the StreamHandler would be redirected too.
		
		pid = os.fork()
		if pid == 0:
			
			# Set-up required environment variables
			os.environ["DEBIAN_FRONTEND"]          = "gnome" # FIXME
			os.environ["APT_LISTCHANGES_FRONTEND"] = "none"
			os.environ["APT_LISTBUGS_FRONTEND"]    = "none"
			if self.display:
				os.environ["DISPLAY"]              = self.display
				if self.xauthority and os.path.exists(self.xauthority):
					os.environ["XAUTHORITY"]       = self.xauthority
				else:
					logger.warning("%s does not exist!" % self.xauthority)
			
			logger.info(os.environ)
			
			desc = channels.common.create_rotated_log(APT_LOGFILE)
			os.dup2(desc, sys.stdout.fileno())
			os.dup2(desc, sys.stderr.fileno())
		
		return pid

class Updates:
	
	"""
	This class manages updates.
	"""
	
	export_properties = [
		"refreshing",
		"checking",
		"downloading",
		"installing",
		"cacheOpening",
		"cacheFailure",
		"CurrentDownloadRate",
		"CurrentDownloadETA",
	]
	
	cacheFailure = False
	cacheOpening = False
	refreshing = False
	checking = False
	downloading = False
	installing = False
	
	user_lock_count = 0
	
	cache_operation_lock = Lock()
	
	def __init__(self):
		"""
		Initializes the class.
		"""
		
		# Lock failed
		updates.lock_failure_callback = self.LockFailed
		
		# Generic failure
		updates.generic_failure_callback = self.GenericFailure
		
		# Cache progress
		updates.cache_progress = (
			apt.progress.text.OpProgress()
			if CURRENT_HANDLER != "DBus"
			else DBusOpProgress(self.CacheOpenProgress, self.CacheOpenDone)
		)
		
		# Cache update progress
		updates.cache_acquire_progress = (
			apt.progress.text.AcquireProgress()
			if CURRENT_HANDLER != "DBus"
			else DBusAcquireProgress(
				self.CacheUpdateStarted,
				self.CacheUpdateStopped,
				self.CacheUpdateItemDone,
				self.CacheUpdateItemFailed,
				self.CacheUpdateItemFetch
			)
		)
		
		# Package acquire progress
		updates.packages_acquire_progress = (
			apt.progress.text.AcquireProgress()
			if CURRENT_HANDLER != "DBus"
			else DBusAcquireProgress(
				self.PackageAcquireStarted,
				self.PackageAcquireStopped,
				self.PackageAcquireItemDone,
				self.PackageAcquireItemFailed,
				self.PackageAcquireItemFetch
			)
		)
		
		# Package installation progress
		updates.packages_install_progress = (
			apt.progress.base.InstallProgress()
			if CURRENT_HANDLER != "DBus"
			else DBusInstallProgress(
				self.PackageInstallStarted,
				self.PackageInstallFinished,
				self.PackageInstallProgressChanged,
				self.PackageInstallStatusChanged
			)
		)
		updates.packages_install_failure_callback = self.PackageInstallFailed

	@channels.actions.signal()
	def LockFailed(self):
		"""
		Signal emitted when the APT Lock acquiring failed.
		"""
		
		pass
	
	@channels.actions.signal(
		signature="ss"
	)
	def GenericFailure(self, error, description):
		"""
		Signal emitted when a generic failure happened.
		"""
		
		pass
	
	@channels.actions.signal()
	def PackageAcquireStarted(self):
		"""
		Signal emitted when the package acquire operation started.
		"""
		
		self.downloading = True
	
	@channels.actions.signal()
	def PackageAcquireStopped(self):
		"""
		Signal emitted when the package acquire operation stopped.
		"""
		
		self.downloading = False
	
	@channels.actions.signal(
		signature="i"
	)
	def PackageAcquireItemDone(self, transaction_id):
		"""
		Signal emitted when an item of the package acquire operation has been done.
		"""
		
		pass
	
	@channels.actions.signal(
		signature="i"
	)
	def PackageAcquireItemFailed(self, transaction_id):
		"""
		Signal emitted when an item of the package acquire operation failed.
		"""
		
		pass
	
	@channels.actions.signal(
		signature="iss"
	)
	def PackageAcquireItemFetch(self, transaction_id, description, shortdesc):
		"""
		Signal emitted when an item of the package acquire operation just
		started the fetch operation.
		"""
		
		pass
	
	@channels.actions.signal()
	def PackageInstallStarted(self):
		"""
		Signal emitted when the package installation process has been
		started.
		"""
		
		self.installing = True
	
	@channels.actions.signal()
	def PackageInstallFinished(self):
		"""
		Signal emitted when the package installation process has been
		finished.
		"""
		
		self.installing = False
	
	@channels.actions.signal()
	def PackageInstallFailed(self, message):
		"""
		Signal emitted when the package installation process failed.
		
		Note: this is handled by libchannels and not by python-apt-
		"""
		
		self.installing = False
	
	@channels.actions.signal(
		signature="ss"
	)
	def PackageInstallStatusChanged(self, package, status):
		"""
		Signal emitted when a package changed its status.
		"""
		
		pass
	
	@channels.actions.signal(
		signature="d"
	)
	def PackageInstallProgressChanged(self, percent):
		"""
		Signal emitted when the install progress changed.
		"""
		
		pass

	@channels.actions.signal()
	def CacheUpdateStarted(self):
		"""
		Signal emitted when the cache update operation started.
		"""
		
		self.refreshing = True
	
	@channels.actions.signal()
	def CacheUpdateStopped(self):
		"""
		Signal emitted when the cache update operation stopped.
		"""
		
		self.refreshing = False
	
	@channels.actions.signal(
		signature="i"
	)
	def CacheUpdateItemDone(self, transaction_id):
		"""
		Signal emitted when an item of the cache update operation has been done.
		"""
		
		pass
	
	@channels.actions.signal(
		signature="i"
	)
	def CacheUpdateItemFailed(self, transaction_id):
		"""
		Signal emitted when an item of the cache update operation failed.
		"""
		
		pass
	
	@channels.actions.signal(
		signature="iss"
	)
	def CacheUpdateItemFetch(self, transaction_id, description, shortdesc):
		"""
		Signal emitted when an item of the cache update operation just
		started the fetch operation.
		"""
		
		pass
	
	@channels.actions.signal(
		signature="ssi"
	)
	def CacheOpenProgress(self, op, subop, percentage):
		"""
		Signal emitted whenever the cache open action progresses.
		"""
		
		if not self.cacheOpening:
			self.cacheOpening = True
	
	@channels.actions.signal()
	def CacheOpenDone(self):
		"""
		Signal emitted when the cache open action finished.
		"""
		
		self.cacheOpening = False
	
	@channels.actions.signal()
	def UpdateCheckStarted(self):
		"""
		Signal emitted when the update check process started.
		"""
		
		self.cacheFailure = False
		self.checking = True
	
	@channels.actions.signal()
	def UpdateCheckFailed(self):
		"""
		Signal emitted when the update check process failed.
		"""
		
		self.cacheFailure = True
		self.checking = False
	
	@channels.actions.signal()
	def UpdateCheckStopped(self):
		"""
		Signal emitted when the update check process finished.
		"""
		
		self.cacheFailure = False
		self.checking = False
	
	@channels.actions.signal()
	def UpdateFound(self, id, name, version, reason, status, size):
		"""
		Signal emitted when an update has been found.
		"""
		
		pass
	
	@channels.actions.signal()
	def PackageStatusChanged(self, id, reason):
		"""
		Signal emitted when a package status has been changed.
		
		When the reason is "keep", the package has been kept: the UI
		should handle that (for example, by unticking a checkbox).
		"""
		
		pass
	
	@property
	def CurrentDownloadRate(self):
		"""
		Returns the current download rate, or an empty string.
		"""
		
		if not self.refreshing and not self.downloading:
			return ""
		
		return size_to_str(
			updates.cache_acquire_progress.current_cps
			if self.refreshing else
			updates.packages_acquire_progress.current_cps
		) + "B/s"
	
	@property
	def CurrentDownloadETA(self):
		"""
		Returns the current download ETA, or an empty string.
		"""
		
		if not self.refreshing and not self.downloading:
			return ""
		
		try:
			eta = int(
				updates.cache_acquire_progress.total_bytes / updates.cache_acquire_progress.current_cps
				if self.refreshing else
				updates.packages_acquire_progress.total_bytes / updates.packages_acquire_progress.current_cps
			)
		except ZeroDivisionError:
			return ""
		
		minutes = math.floor(eta / 60)
		hours = math.floor(minutes / 60)
		days = math.floor(hours / 24)
		
		minutes -= hours*60
		hours -= days*24
		
		# FIXME: Translations
		return "%s%s%s" % (
			"%sd " % days if days > 0 else "",
			"%sh " % hours if hours > 0 else "",
			"%sm" % minutes if minutes > 0 or hours > 0 else "< 1m"
		)
		
	
	@channels.common.thread()
	@channels.actions.action(
		root_required=True,
		polkit_privilege="org.semplicelinux.channels.check-updates",
		command="updates-refresh",
		help="Refreshes the package cache.",
	)
	def Refresh(self):
		"""
		Refreshes the package cache.
		"""
		
		
		self.cache_operation_lock.acquire()
		
		# Clear
		updates.clear()
		print("CHanged is %s" % updates.changed)
		
		try:
			updates.update()
		except:
			# FIXME: Should handle them
			pass
		
		
		self.cache_operation_lock.release()
	
	@channels.common.thread()
	@channels.actions.action(
		root_required=True,
		polkit_privilege="org.semplicelinux.channels.fetch-updates",
		command="updates-fetch",
		help="Fetches the updates."
	)
	def Fetch(self):
		"""
		Fetches the updates.
		"""
		
		if CURRENT_HANDLER == "cli":
			self.CheckUpdates(True, False) # FIXME
		
		updates.fetch()

	@channels.common.thread()
	@channels.actions.action(
		root_required=True,
		polkit_privilege="org.semplicelinux.channels.fetch-install-updates",
		command="updates-fetch-install",
		help="Fetches and installs the updates.",
		in_signature="s",
		cli_ignore=["display"]
	)
	def FetchInstall(self, display, sender):
		"""
		Fetches the updates.
		"""

		if CURRENT_HANDLER == "cli":
			self.CheckUpdates(True, False) # FIXME
		elif CURRENT_HANDLER == "DBus":
			# Queue user name and current display where debconf would
			# look at
			updates.packages_install_progress.queue_display_settings(
				display,
				get_user(sender)
			)

		if updates.fetch():
			updates.install() # Do not launch another useless thread
	
	@channels.actions.action(
		polkit_privilege="org.semplicelinux.channels.fetch-updates",
		command=None
	)
	def FetchStop(self):
		"""
		Stops the current fetch process.
		"""
		
		if self.downloading:
			# This works only on the DbusAcquireProgress but we are sure
			# that we are using it if we are here
			updates.packages_acquire_progress.stop_requested = True
	
	@channels.common.thread()
	@channels.actions.action(
		root_required=True,
		polkit_privilege="org.semplicelinux.channels.install-updates",
		command="updates-install",
		help="Installs the updates.",
		in_signature="s",
		cli_ignore=["display"]
	)
	def Install(self, display, sender):
		"""
		Installs the updates.
		"""

		if CURRENT_HANDLER == "cli":
			self.CheckUpdates(True, False) # FIXME
		elif CURRENT_HANDLER == "DBus":
			# Queue user name and current display where debconf would
			# look at
			updates.packages_install_progress.queue_display_settings(
				display,
				get_user(sender)
			)

		print ("INSTALLING")
		updates.install()
	
	@channels.actions.action(
		#polkit_privilege="org.semplicelinux.channels.enable-channel",
		command=None
	)
	def Clear(self):
		"""
		Clears the changes made.
		"""
		
		updates.clear()
	
	@channels.common.thread()
	@channels.actions.action(
		#polkit_privilege="org.semplicelinux.channels.enable-channel",
		command=None,
		internal=True,
		in_signature="bb"
	)
	def CheckUpdates(self, dist_upgrade, force):
		"""
		Marks the package for (dist-)upgrade and fires UpdateFound for
		every update.
		
		If dist_upgrade is True, the packages will marked using the
		dist-upgrade rules.
		
		If force is True, the packages will be re-marked even if CheckUpdates()
		has been ran before.
		"""
		
		self.cache_operation_lock.acquire()
		
		if CURRENT_HANDLER == "DBus": self.UpdateCheckStarted()

		if not updates.changed or force:
			if not updates.mark_for_upgrade(dist_upgrade):
				if CURRENT_HANDLER == "DBus":
					self.UpdateCheckFailed()
					self.cache_operation_lock.release()
				return
		
		if CURRENT_HANDLER == "DBus":
			updates.get_changes(self.UpdateFound, finish_callback=self.UpdateCheckStopped)
		
		self.cache_operation_lock.release()
	
	@channels.common.thread()
	@channels.actions.action(
		polkit_privilege="org.semplicelinux.channels.change-package-status",
		command=None,
		in_signature="is",
		#out_signature="b"
	)
	def ChangeStatus(self, id, reason):
		"""
		Marks the package matching the given id with the given reason.
		
		Note: other packages may be affected by this actions. For every
		change made, the PackageStatusChanged() signal is fired.
		"""
		
		if self.downloading:
			# Do not do anything if downloading
			return
		
		self.cache_operation_lock.acquire()
		
		updates.change_status(id, reason)
		
		updates.get_user_changes(callback=self.PackageStatusChanged)
		
		self.cache_operation_lock.release()
	
	@channels.actions.action(
		command=None,
		out_signature="ss"
	)
	def GetUpdateInfos(self):
		"""
		Returns useful update informations.
		"""
		
		self.cache_operation_lock.acquire()
		
		required_download, required_space = updates.get_update_infos()
		
		self.cache_operation_lock.release()
		
		return size_to_str(required_download) + "B", size_to_str(required_space) + "B"
