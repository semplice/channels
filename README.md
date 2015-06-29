channels
========

This project contains command-line and DBus frontends to Semplice's libchannels.

Design
------

To avoid duplicating efforts, both the command-line frontend and the DBus service
use the same underlying code.

This means that behaviour is modified at runtime (well, everything in Python is at runtime...)
and thus it might be a bit difficult to follow what happens.

A core part is the `@channels.actions.action` decorator. This, based on the handler type set at
runtime, properly set-ups the actions. Actions that should be shown only on the cli handler (`dbus_visible=False`)
will be replaced by NoneType objects on DBus. The same happens on actions that should be shown only on DBus (`command=None`).

Usage
-----

### Command-line

The command syntax is `channels [action] [action_arguments]`

For example, to list every available channel:

	g7@meddle:~/semplice/channels/channels$ channels list
	jessie
	sample
	semplice-current (enabled)
	semplice-devel
	semplice-jessie
	sid (enabled)
	g7@meddle:~/semplice/channels/channels$ 

...and to query the status of one specific channel:

	g7@meddle:~/semplice/channels/channels$ channels get-enabled semplice-current
	True
	g7@meddle:~/semplice/channels/channels$ channels get-enabled semplice-jessie
	False
	g7@meddle:~/semplice/channels/channels$ 

Use `channels show` to show a list of supported actions.

### D-Bus

The service (`channels-service.py`) exports its objects under the `org.semplicelinux.channels` BUS_NAME on
the System Bus.

Every action namespace has its own object. For example, the `channels` namespace is located at `/org/semplicelinux/channels/channels`.  
The interface used depend on the namespace. In the `channels` one, the interface is `org.semplicelinux.channels.channels`.

For example, to list every available channel:

	g7@meddle:~/semplice/channels/channels$ dbus-send --system --dest="org.semplicelinux.channels" --print-reply /org/semplicelinux/channels/channels org.semplicelinux.channels.channels.List
	method return sender=:1.1192 -> dest=:1.1193 reply_serial=2
	   array [
		  string "jessie"
		  string "sample"
		  string "semplice-current"
		  string "semplice-devel"
		  string "semplice-jessie"
		  string "sid"
	   ]
	g7@meddle:~/semplice/channels/channels$ 

...and to query the status of one specific channel:

	g7@meddle:~/semplice/channels/channels$ dbus-send --system --dest="org.semplicelinux.channels" --print-reply /org/semplicelinux/channels/channels org.semplicelinux.channels.channels.GetEnabled string:"semplice-current"
	method return sender=:1.1192 -> dest=:1.1194 reply_serial=2
	   boolean true
	g7@meddle:~/semplice/channels/channels$ dbus-send --system --dest="org.semplicelinux.channels" --print-reply /org/semplicelinux/channels/channels org.semplicelinux.channels.channels.GetEnabled string:"semplice-jessie"
	method return sender=:1.1192 -> dest=:1.1195 reply_serial=2
	   boolean false
	g7@meddle:~/semplice/channels/channels$ 
