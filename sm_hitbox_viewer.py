#!/usr/bin/env python3

from retroarch.network_command_socket import NetworkCommandSocket
from qusb2snes.websocket_client import WebsocketClient
from memory import MemoryRegion, SparseMemory

import os
import sys
import time
import curses

addresses = [
    (0x0000, 0x100),
    (0x0100, 0x100),
    (0x0200, 0x100),
    (0x0300, 0x100),
    (0x0400, 0x100),
    (0x0500, 0x100),
    (0x0600, 0x100),
    (0x0700, 0x100),
    (0x0800, 0x100),
    (0x0900, 0x100),
    (0x0a00, 0x100),
    (0x0b00, 0x100),
    (0x0c00, 0x100),
    (0x0d00, 0x100),
    (0x0e00, 0x100),
    (0x0f00, 0x100),
]

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

class HitboxViewer(object):
  def __init__(self, sock, window):
    self.sock = sock
    self.window = window

  def run(self):
    while True:
      self.run_one()

  def run_one(self):
    sock = self.sock
    window = self.window

    mem = SparseMemory.read_from(sock, *addresses)

    window.clear()
    window.move(0, 0)

    camera_x = (mem.short(0x0af6) - 128) & 0xffff
    camera_y = (mem.short(0x0afa) - 112) & 0xffff
    if camera_x >= 10000: camera_x -= 65535
    if camera_y >= 10000: camera_y -= 65535

    window.addstr("X: %d Y: %d\n" % (camera_x, camera_y))

    clips = { }
    room_width = mem.short(0x07a5)
    for y in range(0, 14):
      for x in range(0, 16):
        stack = 0
        tile_x = x * 16 - (camera_x & 0x000f)
        tile_y = y * 16 - (camera_x & 0x000f)
        a = (((camera_x + x * 16) & 0xffff) >> 4) + \
            (((((camera_y + y * 16) & 0x0fff) >> 4) * room_width) & 0xffff)
        bts = 0x16402 + a
        clip = 0x10002 + a * 2
        clips[(x, y)] = clip

    clip_addrs = clips.values()
    clip_regions = [ (addr, 2) for addr in clip_addrs ]
    clip_regions = consolidate_regions(clip_regions, 0x100)
    try:
      # TODO: don't try to read tile memory during a transition?
      clip_mem = SparseMemory.read_from(sock, *clip_regions)
    except:
      return
    for y in range(0, 14):
      s = ''
      for x in range(0, 16):
        clip = clips[(x, y)]
        t = clip_mem.short(clip) >> 12
        if t == 0:
          s += '. '
        else:
          s += '%x ' % t
      window.addstr(s)
      window.clrtoeol()
      window.addstr("\n")
      print()

    window.refresh()

def main():
  sock = NetworkCommandSocket()

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
