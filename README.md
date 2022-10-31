Super Metroid Hitbox Viewer
===========================

This is a simple hitbox viewer for Super Metroid.  It reads game memory
over a socket, using either usb2snes or the retroarch network command
protocol.

Usage
-----

If you are using usb2snes:

```
./sm_hitbox_viewer.py --usb2snes
```

If you are using retroarch:

```
./sm_hitbox_viewer.py --retroarch
```

Keys
----

| Key | Action         |
| --- | -------------- |
| q   | Quit           |
| j   | Navigate down  |
| k   | Navigate up    |
| h   | Navigate left  |
| l   | Navigate right |
| r   | Reset view     |

Limitations
-----------

Currently the program only shows a simple hex represenatation of the
room tile map.  It makes no attempt yet to read the BTS map.  This is
good enough for basic out-of-bounds navigation.

Reading game memory from fxpak/sd2snes is probably slow, though it may
be fast enough for simple out-of-bounds hitbox viewing.

Thanks
------

Thanks to supermetroidftp and others for the [lua hitbox viewer for
bizhawk](http://smethack.f5.si/?plugin=attach&refer=Lua%20Script%20Download&openfile=SuperMetroid_HitBox2_Bizhawk.lua).
This program started as a port of that script to python.

