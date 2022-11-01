#!/usr/bin/env python3

# ----------------------------------------------------------------------
# Super Metroid Hitbox Viewer
# Based on SuperMetroid_HitBox2_Bizhawk.lua
# (http://smethack.f5.si/?plugin=attach&refer=Lua%20Script%20Download&openfile=SuperMetroid_HitBox2_Bizhawk.lua)
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <http://unlicense.org/>
#
# ----------------------------------------------------------------------

from retroarch.network_command_socket import NetworkCommandSocket
from qusb2snes.websocket_client import WebsocketClient
from memory import MemoryRegion, SparseMemory

import os
import sys
import time
import curses
import argparse

def addrs_to_regions(addrs, max_region_size):
  regions = [ ]
  addrs = sorted(addrs)

  region_start = None
  region_end = None

  for addr in addrs:
    # print(addr)
    if region_start is None:
      region_start = addr
      region_end = addr + 1
    elif addr > region_start + max_region_size:
      regions.append((region_start, region_end - region_start))
      region_start = addr
      region_end = addr + 1
    else:
      region_end = addr + 1

  if region_start is not None:
    regions.append((region_start, region_end - region_start))

  return regions

def consolidate_regions(regions, max_region_size):
  addrs = [ ]
  for r in regions:
    for addr in range(r[0], r[0] + r[1]):
      addrs.append(addr)
  return addrs_to_regions(addrs, max_region_size)

disp_width = 16    # (in tiles)
disp_height = 14   # (in tiles)
tile_width = 16    # (in pixels)
tile_height = 16   # (in pixels)

class State(object):
  def __init__(self, **attrs):
    for name in attrs:
      setattr(self, name, attrs[name])

  def __repr__(self):
    return "State(%s)" % ', '.join([ '%s=%s' % (k,repr(v)) for k,v in
      self.__dict__.items() ])

  @staticmethod
  def read_from(sock):
    mem = SparseMemory.read_from(
        sock,
        (0x07a5, 0x2),
        (0x0af6, 0x6),
    )

    camera_x = (mem.short(0x0af6) - disp_width*tile_width//2) & 0xffff
    camera_y = (mem.short(0x0afa) - disp_height*tile_height//2) & 0xffff
    if camera_x >= 10000: camera_x -= 65535
    if camera_y >= 10000: camera_y -= 65535

    room_width = mem.short(0x07a5)

    return State(
        camera_x=camera_x,
        camera_y=camera_y,
        room_width=room_width)

class RoomTiles(object):
  def __init__(self, tiles):
    self.tiles = tiles

  def __getitem__(self, coords):
    return self.tiles[coords]

  @classmethod
  def read_from(cls, sock, state):
    clips = cls.get_clips(state)
    clip_mem = cls.read_clip_mem(sock, clips)
    if clip_mem is None: return None

    tiles = { }
    for y in range(0, disp_height):
      for x in range(0, disp_width):
        clip = clips[(x, y)]
        tiles[(x, y)] = clip_mem.short(clip) >> 12

    return RoomTiles(tiles)

  @classmethod
  def get_clips(cls, state):
    clips = { }

    for y in range(0, disp_height):
      for x in range(0, disp_width):
        a = (((state.camera_x + x * tile_width) & 0xffff) >> 4) + \
            (((((state.camera_y + y * tile_height) & 0x0fff) >> 4) * state.room_width) & 0xffff)
        bts = 0x16402 + a
        clip = 0x10002 + a * 2
        clips[(x, y)] = clip

    return clips

  @classmethod
  def read_clip_mem(self, sock, clips):
    clip_addrs = clips.values()
    clip_regions = [ (addr, 2) for addr in clip_addrs ]
    clip_regions = consolidate_regions(clip_regions, 0x100)
    try:
      # TODO: don't try to read tile memory during a transition?
      clip_mem = SparseMemory.read_from(sock, *clip_regions)
      return clip_mem
    except RuntimeError: # TODO: capture specific exception that read_from raises
      return None

class HitboxViewer(object):
  def __init__(self, sock, window):
    self.sock = sock
    self.window = window

    self.adj_x = 0
    self.adj_y = 0
    self.done = False

  def run(self):
    self.done = False
    while not self.done:
      self.run_one()

  def run_one(self):
    sock = self.sock
    window = self.window

    window.erase()
    window.move(0, 0)

    state = State.read_from(self.sock)
    state.camera_x += self.adj_x
    state.camera_y += self.adj_y

    self.draw_coords(state)

    tiles = RoomTiles.read_from(self.sock, state)
    self.draw_tiles(tiles)

    window.refresh()

    s = self.get_input()
    self.handle_input(s)

  def draw_coords(self, state):
    x_coord_label = "X: %d" % state.camera_x
    y_coord_label = "Y: %d" % state.camera_y
    if self.adj_x != 0: x_coord_label += " (%+d)" % self.adj_x
    if self.adj_y != 0: y_coord_label += " (%+d)" % self.adj_y
    self.window.addstr("%s %s\n" % (x_coord_label, y_coord_label))

  def draw_tiles(self, tiles):
    for y in range(0, disp_height):
      s = ''
      for x in range(0, disp_width):
        t = tiles[(x, y)]
        if t == 0:
          s += '. '
        else:
          s += '%x ' % t
      self.window.addstr(s)
      self.window.addstr("\n")

  def get_input(self):
    self.window.timeout(25)
    ch = self.window.getch()
    if ch >= 32 and ch < 128:
      s = chr(ch)
    else:
      s = ch
    return s

  def handle_input(self, ch):
    # TODO: For some reason up/down/left/right do not work...
    if ch == 'q' or ch == 'Q':
      self.done = True
    elif ch == 'h' or ch == curses.KEY_LEFT:
      self.adj_x -= 16
    elif ch == 'l' or ch == curses.KEY_RIGHT:
      self.adj_x += 16
    elif ch == 'k' or ch == curses.KEY_UP:
      self.adj_y -= 16
    elif ch == 'j' or ch == curses.KEY_DOWN:
      self.adj_y += 16
    elif ch == 'r' or ch == 'R':
      self.adj_x = 0
      self.adj_y = 0

def create_sock(client_name, client_type):
  if client_type == 'usb2snes':
    return WebsocketClient(client_name)
  elif client_type == 'retroarch':
    return NetworkCommandSocket()
  elif client_type is None:
    raise ValueError('No client type provided')
  else:
    raise ValueError('Invalid client type %s' % client_type)

def main():
  parser = argparse.ArgumentParser(description='SM Room Timer')
  client_type_group = parser.add_mutually_exclusive_group(required=True)
  client_type_group.add_argument('--usb2snes', dest='client_type', action='store_const', const='usb2snes')
  client_type_group.add_argument('--retroarch', dest='client_type', action='store_const', const='retroarch')
  args = parser.parse_args()

  sock = create_sock('sm_hitbox_viewer', args.client_type)

  screen = curses.initscr()

  try:
    curses.start_color()
    curses.use_default_colors()
    curses.curs_set(0)
    curses.noecho()

    window = curses.newwin(0, 0, 1, 2)
    window.clear()

    viewer = HitboxViewer(sock, window)
    viewer.run()

  finally:
    curses.endwin()

if __name__ == '__main__':
  main()
