#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  ansiban.py
#  
#  Copyright 2017 Felix Steinbeck <felix.steinbeck@uni-rostock.de>
#
# Sokoban ist wie Game of Life oder Türme von Hanoi... irgendwann muss man das
# einfach selbst umsetzen. In diesem Fall: UI via ANSI-art, ansonsten so bar-
# knochig wie möglich. kein numpy, kein curses und erst recht nicht sokoengine
#
from __future__ import unicode_literals

import re, sys

if sys.platform.startswith("linux"):
    import tty, termios, subprocess
    dance = 38
    clear = "\033c"
    def getch():
        # TODO: Timeout um Esc zu finden?
        def getc_unix():
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
               tty.setraw(sys.stdin.fileno())
               ch = sys.stdin.read(1)
            finally:
               termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch
        charlist = []
        for i in range(3):
            try: charlist.append(getc_unix())
            except: pass
            if charlist[i] not in [chr(27), chr(91)]: break
        if len(charlist) == 3:
            cmap = {'A': '^', 'B': 'v', 'C': '>', 'D': '<'}
            if charlist[2] in cmap: return cmap[charlist[2]]
            pmap = {'5': 'PgUp', '6': 'PgDn'}
            if charlist[2] in pmap: 
                getc_unix()
                return pmap[charlist[2]]
        if len(charlist) == 1: return charlist[0]
        return charlist
    
    def get_terminal_size():
        try:
            width = int(subprocess.check_output("tput cols", shell=True))
            height = int(subprocess.check_output("tput lines", shell=True))
        except:
            width, height = 80, 25
        return width, height

if sys.platform.startswith("win"):
    # use ansicon or ansi.sys!
    import win_unicode_console, colorama # install via pip
    win_unicode_console.enable()
    colorama.init()
    
    dance = 14
    clear = "\033[0m\033[2J\033[1;1H"
    import msvcrt, struct
    def getch():
        charlist = []
        for i in range(2):
            try: charlist.append(msvcrt.getch())
            except: pass
            if charlist[i] not in [chr(27), chr(224)]: break
        if len(charlist) == 2:
            cmap = {'H': '^', 'P': 'v', 'M': '>', 'K': '<', 'I': 'PgUp', 'Q': 'PgDn'}
            if charlist[1] in cmap: return cmap[charlist[1]]
        if len(charlist) == 1: 
            if charlist[0] == chr(27): return 'q'
            return charlist[0]
    
    def get_terminal_size():
        width, height = 80, 25
        try:
            from ctypes import windll, create_string_buffer
            h = windll.kernel32.GetStdHandle(-12)
            csbi = create_string_buffer(22)
            res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
            if res:
                (bx, by, cx, cy, w, l, t, r, b, mx, my) = struct.unpack("hhhhHhhhhhh", csbi.raw)
                width, height = r - l + 1, b - t
        except Exception as e:
            sys.stderr.write(str(e)+"\n")
        return width, height

from sokoban import *

class ANSIban:
    """Play in Terminal"""
    RESET = "\033[0m"
    BORDERCOLOR = "\033[1;34m"
    
    # empty (0) must not contain ansi-codes as it is used for length-calculations
    RENDER = {
        'native' : dict([reversed(l) for l in Sokoban.DECODE.items()]),
        '2x1' : {
            0              : ("  ",          ),
            Grid.WALL                   : ("\033[0;31m▒▒",),
            Grid.SOKO                   : ("\033[1;33m@@",),
            Grid.CRATE                  : ("\033[0;36m[]",),
            Grid.TARGET                 : ("\033[1;30m<>",),
            Grid.CRATE | Grid.TARGET : ("\033[1;32m[]",),
            Grid.SOKO  | Grid.TARGET : ("\033[0;37m@@",),
        },
        '3x2' : {
            0              : ("   ", "   "),
            Grid.WALL                   : ("\033[0;31m▒▒▒",
                                           "\033[0;31m▒▒▒"),
            Grid.SOKO                   : ("\033[1;33mn_n",
                                           "\033[1;33mu^u"),
            Grid.CRATE                  : ("\033[0;36m┌─┐",
                                           "\033[0;36m└─┘"),
            Grid.TARGET                 : ("\033[1;30m/.\\",
                                           "\033[1;30m\\'/"),
            Grid.CRATE | Grid.TARGET : ("\033[1;32m╔─╗",
                                           "\033[1;32m╚─╝"),
            Grid.SOKO  | Grid.TARGET : ("\033[1;33mn\033[37m_\033[33mn",
                                           "\033[1;33mu\033[1;37m^\033[33mu"),
        },
        '5x3' : {
            0              : ("     ","     ","     "),
            Grid.WALL                   : ("\033[0;31m▒▒▒▒▒",
                                           "\033[0;31m▒▒▒▒▒",
                                           "\033[0;31m▒▒▒▒▒"),
            Grid.SOKO                   : ("\033[1;33m ─╤─ ",
                                           "\033[1;33m╟─O─╢",
                                           "\033[1;33m ─╧─ "),
            Grid.CRATE                  : ("\033[0;36m┌───┐",
                                           "\033[0;36m│·X·│",
                                           "\033[0;36m└───┘"),
            Grid.TARGET                 : ("     ",
                                           "\033[1;30m ·x· ",
                                           "     "),
            Grid.CRATE | Grid.TARGET : ("\033[1;32m┌───┐",
                                           "\033[1;32m│\033[1;36m·X·\033[1;32m│",
                                           "\033[1;32m└───┘"),
            Grid.SOKO  | Grid.TARGET : ("\033[1;33m -╤- ",
                                           "\033[1;33m╟─\033[1;30mx\033[1;33m─╢",
                                           "\033[1;33m -╧- "),
        }
    }

    def __init__(self, leveldir):
        width, height = get_terminal_size()
        if width < 80 or height < 24:
            sys.stderr.write("Need at least 80x25 terminal\n")
            sys.exit(1)
        self.maxdim = (width, height)
        self.soko = Sokoban(leveldir)
        self.headerheight = 1

    def strlen(self, s):
        """Calculate diplayerd string length. remove ANSI-stuff etc."""
        return len(re.sub("\033.+?m", "", s))
    
    def header(self):
        def key(ch, txt): return "\033[0;36m[\033[1;37m"+ch+"\033[0;36m] "+txt+"\033[0m   "
        sys.stdout.write("\033[1;1H") # ansi return to home (no clear, avoid flicker)
        # First part. Banner & keys.
        banner = "\033[1;36mSOCONBAN \033[0;36m0.1    " + \
            key("←↑↓→", "Move") + key("q", "Quit") + \
            key("r", "Restart") + key("u", "Undo")
        self.headerheight = 1
        # add other headerlines / status
        for s in self.state:
            if self.strlen(s) + self.strlen(banner) < self.maxdim[0]:
                banner += s
            else:
                banner += "\n" + s
                self.headerheight += 1
        sys.stdout.write(banner + "\n")

    def listselect(self, liste, start=0):
        curr = start
        hw = self.maxdim[0] - 2
        hh = (self.maxdim[1] - self.headerheight) // 2
        idle = "\033[1;30m[\033[0;33m%3d\033[1;30m]\033[0;37m"
        high = "\033[1;37m[\033[1;33m%3d\033[1;37m]\033[1;32m"
        # TODO: liste trimmen, falls zu lang für terminal. Nicht einfach, bei bunter Liste.
        
        while True:
            s = "\033[%d;1H" % (self.headerheight + 1)
            for i in range(hh):
                s += " "*hw if curr - hh+i < 0 else (idle + " %-" + str(hw-6) + "s") % (curr - hh+i, liste[curr - hh+i])
                s += "\n"
            
            s += (high + " %-" + str(hw-6) + "s\033[0m\n") % (curr, liste[curr])
            
            for i in range(1, hh):
                s += " "*hw if curr + i >= len(liste) else (idle + " %-"+str(hw-6)+"s") % (curr + i, liste[curr + i])
                s += "\n"
            sys.stdout.write(s)
            sys.stdout.flush()
            key = getch()
            if key == "v": 
                curr += 1
                if curr >= len(liste): curr = 0
            if key == "^": 
                curr -= 1
                if curr < 0: curr = len(liste) - 1
            if key == "PgDn": 
                curr += hh
                if curr >= len(liste): curr = 0
            if key == "PgUp": 
                curr -= hh
                if curr < 0: curr = len(liste) - 1
            if key == "\r":
                return curr
            if key == "q":
                return None

    def choosepack(self, lastid):
        # find packs, filenames and names and number of levels, calculate total
        filelen = max(len(p['file']) for p in self.soko.packs)
        titlen = max(len(p['title']) for p in self.soko.packs)
        if titlen > self.maxdim[0] - 11 - filelen:
            titlen = self.maxdim[0] - 11 - filelen
        #fstr = "\033[35m%-"+str(filelen)+"s \033[34m | \033[33m %4d \033[34m | \033[37m %-"+str(titlen)+"s\033[0m"
        # p['file'], 
        fstr = "\033[35m%4d\033[34m |\033[37m %-"+str(titlen)+"s\033[0m"
        packfancy = [fstr % (len(p['levels']), p['title']) for p in self.soko.packs]
        return self.listselect(packfancy, lastid)

    def plot(self, render="auto", border=BORDERCOLOR):
        """
        Rendert ein grid als ASCII/ANSI mit gegebenem renderer. Bei Bedarf auch mit Rahmen.
        Border kann falsey sein (kein Rahmen) oder ein ANSI-code.
        """
        
        assert render == "auto" or render in self.RENDER, "render must be 'auto' or one of: " + ", ".join(self.RENDER.keys())
        
        w = self.soko.currentgrid.width
        h = self.soko.currentgrid.height
        if render == "auto":
            render = "5x3"
            if w * 5 > (self.maxdim[0]-2) or h * 3 > (self.maxdim[1] - self.headerheight - 2): render = "3x2"
            if w * 3 > (self.maxdim[0]-2) or h * 2 > (self.maxdim[1] - self.headerheight - 2): render = "2x1"
            if w * 2 > (self.maxdim[0]-2) or h     > (self.maxdim[1] - self.headerheight - 2): 
                return "Terminal too small / Level too large"
        # construct
        charwidth = len(self.RENDER[render][0][0])
        s = ""
        if border: s += border + "╔" + ("═" * w*charwidth) + "╗" + self.RESET + "\n"
        for row in self.soko.currentgrid.grid:
            for i in range(len(self.RENDER[render][0])):
                if border: s += border + "║" + self.RESET
                s += "".join([self.RENDER[render][c][i] for c in row])
                if border: s += border + "║" + self.RESET
                s += "\n"
        if border: s += border + "╚" + ("═" * w*charwidth) + "╝" + self.RESET + "\n"
        return s
    
    def drawfield(self):
        # levelname
        self.state = ("\033[0;35m%s\033[1;30m // [\033[0;33m%03d\033[1;30m] \033[0;36m%s\033[0m  " % (
            self.soko.packinfo['title'],
            self.soko.levelinfo['idx'],
            self.soko.levelinfo['name']
        ), # status
            "\033[1;37mMOVES: %04d   PUSHES: %04d   TIME: %s\033[0m" % (len(self.soko.undo), self.soko.pushes, re.sub(",.*", "", self.soko.curtime))
            + "   " +("\033[1;31m>>> DEADLOCK <<<\033[0m" if self.soko.currentgrid.isdead() else ("(unsolved)" if self.currsol is None else "(Best solution: %d,%d)" % self.currsol))
            + "         "
        )
        self.header()
        sys.stdout.write(self.plot("auto"))
        # move cursor to bottom
        sys.stdout.write("\033[%d;%dH" % (self.maxdim[1], self.maxdim[0]))
        sys.stdout.flush()
    
    def playlevel(self):
        """
        Start playing currentlevel. return true if solved, false if quit.
        arrowkeys to move
        u to undo
        r to restart
        q to quit
        """
        self.currsol = None
        cs = self.soko.getsolution()
        if cs is not None: self.currsol = (len(cs)-1, cs[-1][1])
        # clear screen
        sys.stdout.write(clear)
        self.drawfield()
        done = False
        while not done:
            # check key
            key = getch()
            if key == "q": return False
            if key in ("<","^", "v", ">", "r", "u"): 
                done = self.soko.play(key)
                self.drawfield()
                if done: return True
                
            
    
    def playpack(self):
        """Start playing from currentlevel until quit or finished"""
        while self.playlevel():
            # freudentanz
            sys.stdout.write("\a")
            for i in range(2, dance):
                for row in self.soko.currentgrid.grid:
                    for col in range(len(row)):
                        if row[col] == i % 3 + 1: row[col] = (i + 1) % 3 + 1
                self.drawfield()
                time.sleep(.04)
            
            pfile = self.soko.packinfo['file']
            pname = self.soko.packinfo['title']
            lname = "[%d] %s" % (self.soko.levelinfo['idx'], self.soko.levelinfo['name'])

            sol = self.soko.getsolution()
            solved = "Found a new Solution!"
            if sol is not None:
                if (len(sol)-1) <= len(self.soko.undo):
                    solved = "Best solution so far: %d moves, %d pushes" % (len(sol)-1, sol[-1][1])
                else:
                    solved = "Found a better solution! (less than %d moves)" % (len(sol)-1)
            
            pwidth = max(len(x) for x in (pfile, pname, lname, self.soko.curtime, solved))
            pwidth = max(pwidth, 15) # <press a key>
            left = self.maxdim[0] // 2 - pwidth // 2 - 6
            top = self.maxdim[1] // 2 - 4
            
            stat = (
                 "\033[0;33;44m█▀▀▀▀▀▀▀▀▀▀▀▀"                      +( "▀"  * pwidth) + "█\033[0m",
                 "\033[0;33;44m█\033[1;32;44m  "            + solved.center(pwidth+8)+"  \033[0;33m█\033[0m",
                 "\033[0;33;44m█\033[0;33;44m──────────"           +( "─"  * pwidth)+ "──\033[0;33m█\033[0m",
                ("\033[0;33;44m█\033[0;37;44m  File:   \033[1;37m%"+("-%d" % pwidth)+"s  \033[0;33m█\033[0m") % pfile,
                ("\033[0;33;44m█\033[0;37;44m  Name:   \033[1;37m%"+("-%d" % pwidth)+"s  \033[0;33m█\033[0m") % pname,
                ("\033[0;33;44m█\033[0;37;44m  Level:  \033[1;37m%"+("-%d" % pwidth)+"s  \033[0;33m█\033[0m") % lname,
                 "\033[0;33;44m█\033[0;33;44m──────────"           +( "─"  * pwidth)+ "──\033[0;33m█\033[0m",
                ("\033[0;33;44m█\033[0;37;44m  Moves:  \033[1;37m%"+("-%d" % pwidth)+"d  \033[0;33m█\033[0m") % len(self.soko.undo),
                ("\033[0;33;44m█\033[0;37;44m  Pushes: \033[1;37m%"+("-%d" % pwidth)+"d  \033[0;33m█\033[0m") % self.soko.pushes,
                ("\033[0;33;44m█\033[0;37;44m  Time:   \033[1;37m%"+("-%d" % pwidth)+"s  \033[0;33m█\033[0m") % self.soko.curtime,
                 "\033[0;33;44m█\033[0;33;44m──────────"           +( "─"  * pwidth)+ "──\033[0;33m█\033[0m",
                 "\033[0;33;44m█\033[0;37;44m          "           +( " "  * pwidth)+ "  \033[0;33m█\033[0m",
                 "\033[0;33;44m█▄▄▄▄▄▄▄▄▄▄▄▄"                      +( "▄"  * pwidth)+ "█\033[0m"
            )
            for es in enumerate(stat):
                sys.stdout.write("\033[%d;%dH" % (top+es[0], left))
                sys.stdout.write(es[1])
            scursor = "\033[%d;%dH\033[1;33;44m" % (top+11, left+3)
            if solved[0] == "F": # this check feels filthy
                sys.stdout.write(scursor + "Saving solution...".center(pwidth+8))
                sys.stdout.flush()
                self.soko.setsolution()
            sys.stdout.write(scursor + "<Press a key>".center(pwidth+8))

            # move cursor to bottom
            sys.stdout.write("\033[%d;%dH" % (self.maxdim[1], self.maxdim[0]))
            sys.stdout.flush()
            getch()
            
            if self.soko.levelinfo['idx'] + 1 >= self.soko.packinfo['levels']:
                sys.stdout.write(clear+"\033[1;32m")
                for r in enumerate((
                    "                      █                                        ",
                    " █████░               █             ████▒                      ",
                    " █   ▓█               █             █  ▒█░                     ",
                    " █    █ ░███░   ▓██▒  █  ▒█         █   ▒█  ███   █▒██▒   ███  ",
                    " █   ▓█ █▒ ▒█  ▓█  ▓  █ ▒█          █    █ █▓ ▓█  █▓ ▒█  ▓▓ ▒█ ",
                    " █████░     █  █░     █▒█           █    █ █   █  █   █  █   █ ",
                    " █      ▒████  █      ██▓           █    █ █   █  █   █  █████ ",
                    " █      █▒  █  █░     █░█░          █   ▒█ █   █  █   █  █     ",
                    " █      █░ ▓█  ▓█  ▓  █ ░█          █  ▒█░ █▓ ▓█  █   █  ▓▓  █ ",
                    " █      ▒██▒█   ▓██▒  █  ▒█         ████▒   ███   █   █   ███▒ ")):
                    sys.stdout.write("\033[%d;%dH" % (self.maxdim[1] // 2 - 5 + r[0], self.maxdim[0] // 2 - 32))
                    sys.stdout.write(r[1])
                sys.stdout.write("\033[0m")
                sys.stdout.write("\033[%d;%dH" % (self.maxdim[1], self.maxdim[0]))
                sys.stdout.flush()
                getch()
                return True
            else:
                self.soko.loadlevel(self.soko.levelinfo['idx'] + 1)
        return False
    
    def main(self):
        newpack = 0
        skip = False
        if self.soko.levelinfo is not None:
            # resume
            newpack = self.soko.packinfo['idx']
            skip = True
            
        while True:
            if not skip:
                sys.stdout.write(clear)
                self.state = ("\033[0;32mPacks: \033[1;32m%d\033[1;30m  ::  \033[0;32mLevels: \033[1;32m%d\033[1;30m  ::  \033[1;31mSelect Pack\033[0m" % (len(self.soko.packs), self.soko.cumlevels),)
                self.header()
                newpack = self.choosepack(newpack)
                if newpack is None:
                    sys.stdout.write(clear)
                    sys.stdout.flush()
                    self.soko.savegame()
                    return
                self.soko.loadpack(newpack)
            while True:
                sys.stdout.write(clear)
                self.state = ("\033[0;32mPack: \033[1;32m%s\033[1;30m  ::  \033[0;32mLevels: \033[1;32m%d\033[1;30m  ::  \033[1;31mSelect Level\033[0m" % (self.soko.packinfo['title'], self.soko.packinfo['levels']),)
                self.header()
                if not skip:
                    def movs(n):
                        gs = self.soko.getsolution(n)
                        return (len(gs)-1, gs[-1][1]) if gs is not None else None
                    ltxt = [x[0] + (" - unsolved" if movs(n) is None else " - solved: %d,%d" % movs(n)) for n,x in enumerate(self.soko.levellist())]
                    newlevel = self.listselect(ltxt, self.soko.levelinfo['idx'])
                    if newlevel is None: break
                    self.soko.loadlevel(newlevel)
                self.playpack()
                skip = False


def main(args):
    return 0

if __name__ == '__main__':
    g = ANSIban("levels.zip")
    g.main()
