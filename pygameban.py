#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  pygameban.py
#  
# Sokoban ist wie Game of Life oder Türme von Hanoi... irgendwann muss man das
# einfach selbst umsetzen. In diesem Fall: UI via SDL mit pygame.
#
# Und weil auch eine Programmierübung ist, ist alles python 2 & 3 kompatibel :-)
from __future__ import unicode_literals

import pygame, random, re, time, os

import gfx
from sokoban import *

DEFAULT_SIZE = (800, 600)

class Pygameban:
    """Eye-friendly oldschool-GFX with pygame"""
    # classvars are config. may be set on runtime?
    #FONT   = None  # Use default Font (missing some unicode so... don't)
    #PATHPREFIX = os.path.dirname(__file__)
    PATHPREFIX = os.path.dirname(os.path.abspath(sys.argv[0]))
    FONT   = os.path.join(PATHPREFIX, 'font.ttf') # TTF-file to use as font. Prefer Monospace.
    FONTAA = False # Enable font antialiasing
    STATUS = 23 # Number of text rows. (height / STATUS) is row height.
    BORDER = 2
    REPEAT = (200,90) # key repeat delay and interval. set to (0,0) to deactivate keyrepeat
    
    def __init__(self, leveldir):
        pygame.init()
        di = pygame.display.Info()
        # in case of multihead, this is too large (all monitors instead of one)
        self.disp = (di.current_w, di.current_h)
        self.curr = DEFAULT_SIZE
        pygame.font.init()
        pygame.display.set_caption('IKSOKOBAN')
        pygame.display.set_icon(gfx.icon())
        self.resize()
        gfx.mapsprites()
        if sys.platform == "win32": # this is a workaround needed for py2exe
            pygame.display.set_icon(pygame.transform.scale(gfx.sprites['icon'], (32,32)))
        self.modal("Loading...")
        pygame.key.set_repeat(*self.REPEAT)
        self.soko = Sokoban(leveldir)
        self.menuselect = 0 # selected row in current menu
        self.menulist = [] # a list of dicts (pygame.Surface(), func, args, next-state (see main))
        self.currsol = None # last solution metadata (moves, pushes)
        # states
        # 0 = exit
        # 1 = Main Menu
        # 2 = select pack
        # 3 = select level (with preview) 
        # 4 = play level
        # 5 = replay solution
        self.state = 1
        
    def resize(self, w=DEFAULT_SIZE[0], h=DEFAULT_SIZE[1]):
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        fontsize = self.screen.get_height() // (self.STATUS + 2) # <<-- +2 Textgrößenkorrektur
        if self.FONT:
            # when compiling with py2exe, loading font will fail ("Can't seek in stream")
            # font.ttf has to be added in library.zip/pygame/freesansbold.ttf
            try: 
                self.font = pygame.font.Font(self.FONT, fontsize)
            except:
                self.font = pygame.font.Font(pygame.font.get_default_font(), fontsize)
        else:
            self.font = pygame.font.SysFont(None, fontsize)
        self.curr = (w, h)
    
    def text(self, s, coord, color, surface=None):
        """
        draw text 's' to an existing 'surface' or screen (if no surface given) at
        'coord' with a named 'color' (see gfx.colors.keys())
        returns the width (pixel) of the rendered text
        """
        if surface is None: surface = self.screen
        sth = self.screen.get_height() // self.STATUS # zeilenhöhe
        tcol = gfx.colors[color]
        tbg = None
        if 'gfont' in gfx.colors: tcol = gfx.colors['gfont']
        fs = self.font.render(s, self.FONTAA, tcol)
        # center text vertically
        hi = fs.get_height()
        if hi < sth: coord = (coord[0], coord[1] + (sth-hi)//2 + (sth-hi)%2)
        
        surface.blit(fs, coord)
        return fs.get_width()
    
    def modal(self, txt):
        """display a modal dialog, wait for a key and return it"""
        b = self.font.get_linesize() # 1 textline border
        # calculate text-size
        lines = [l.strip() for l in txt.splitlines()]
        wi = he = 0
        for l in lines:
            wi = max(wi, self.font.size(l)[0])
            he += self.font.get_linesize()
        # create surface and blit text on it
        ms = pygame.Surface((wi + 2*b, he + 2*b), pygame.SRCALPHA)
        # transparent ---------------↓
        ms.fill(gfx.colors['b'] + (172,))
        he = 0
        for l in lines:
            ts = self.font.render(l, self.FONTAA, gfx.colors['w'])
            ms.blit(ts, (b, he + b))
            he += self.font.get_linesize()
        # blit centered to screen
        self.screen.blit(ms, ((self.screen.get_width() - ms.get_width()) // 2, (self.screen.get_height() - ms.get_height()) // 2))
        pygame.display.flip()
        
    def waitkey(self, waitkeys=None):
        # wait for keypress
        ev = None
        while not ev:
            ev = pygame.event.wait() # nicht soo gut, weil "gedrückt halten" nicht geht
            if ev.type != pygame.KEYDOWN or (waitkeys and ev.key not in waitkeys):
                ev = None
        return ev.key
    
    def plot(self, dim=(0,0), minfield=(20,17), border=2, floatzoom=False):
        """
        plot current playfield into a surface with given 'dim'ensions.
        If dim is (0,0) zoom = 1 (16x12 each block) will be used. 
        Resulting surface may exceed screen or dim,
        Draw a 'border' (scaled as well).
        Draw playfield with at least 'minsize' blocks size and center it in dim.
        If floatzoom is false, only integer zoomlevels are used and no 
        interpolation.
        
        returns a surface with all the blocks in place
        """
        # grid size
        gw = self.soko.currentgrid.width
        gh = self.soko.currentgrid.height
        # border offset left and top
        bleft = border - 6
        btop = border - 4
        off = border if border > 6 else border-bleft, border if border > 4 else border-btop
        # plot 1:1 with border
        targ = pygame.Surface((
            16*gw+6+(-bleft if bleft < 0 else 0)+border+max(bleft,0), 
            12*gh+4+(-bleft if btop  < 0 else 0)+border+max(btop,0)
        ), pygame.SRCALPHA)
        # draw border of playfield
        targ.fill(gfx.colors['border'], (-bleft if bleft < 0 else 0, -btop if btop < 0 else 0, gw*16+6+2*border, gh*12+2*border))
        # draw playfield items
        targ.fill(gfx.colors['bg2'], off + (gw*16+3, gh*12))
        for rc, row in enumerate(self.soko.currentgrid.grid):
            for cc, col in enumerate(row):
                if col == 0: continue
                if col & Grid.SOKO:
                    # TODO: richtungsabhängig
                    if self.lastdir == '<': spr = gfx.sprites['sokoleft']
                    elif self.lastdir == '>': spr = gfx.sprites['sokoright']
                    else: spr = gfx.sprites['sokovert']
                else:
                    spr = gfx.sprites[col]
                targ.blit(spr, (off[0]-5+16*cc, off[1]-4+12*rc))
        # resize and pad to target size
        if dim == (0,0): dim = (targ.get_width(), targ.get_height())
        zoom = min(float(dim[0]) / max(targ.get_width(), minfield[0]*16), float(dim[1]) / max(targ.get_height(), minfield[1]*12))
        if not floatzoom:
            zoom = int(zoom)
            if zoom > 1:
                targ = pygame.transform.scale(targ, (zoom * min(targ.get_width(), dim[0]), zoom * min(targ.get_height(), dim[1])))
        else:
            targ = pygame.transform.smoothscale(targ, (int(zoom * targ.get_width()), int(zoom * targ.get_height())))
        # extend in the other direction (probably)
        result = pygame.Surface((max(dim[0], targ.get_width()), max(dim[1], targ.get_height())), pygame.SRCALPHA)
        result.blit(targ, ((dim[0] - targ.get_width())//2, (dim[1] - targ.get_height())//2))
        return result
        
    def playfield(self, replay=False):
        """draw playfield and statusbar during normal play"""
        # screen size
        sw = self.screen.get_width()
        sh = self.screen.get_height()
        sth = sh // self.STATUS # line height
        sh -= 2*sth # reserve space for status lines (top and bottom)
        
        # draw entire screen
        self.screen.fill(gfx.colors['bg1'])
        
        field = self.plot((sw,sh), (20,17), self.BORDER, floatzoom=False)
        if field.get_width() > sw or field.get_height() > sh:
            zf = min(sw / float(field.get_width()), sh / float(field.get_height()))
            field = self.plot(dim=(max(field.get_width()*zf, sw), max(field.get_height()*zf, sh)), floatzoom=True)
        
        # Levelinfo
        ox = 1
        ox += self.text(self.soko.packinfo['title'], (1, 1), 'bg2')
        ox += self.text(' [', (ox, 1),'b')
        ox += self.text('%d' % self.soko.levelinfo['idx'], (ox, 1) ,'wall')
        ox += self.text('/', (ox, 1),'b')
        ox += self.text('%d' % (self.soko.packinfo['levels'] - 1), (ox, 1), 'wall')
        ox += self.text('] ', (ox, 1),'b')
        ox += self.text('%s' % self.soko.levelinfo['name'], (ox, 1), 'crat')
        
        self.screen.blit(field, (0, sth))
        
        if not replay:
            ox = self.text('MOVES,PUSHES: ', (1, sh+sth), 'bg2')
            ox += self.text('%d,%d' % (len(self.soko.undo), self.soko.pushes), (ox, sh+sth), 'w')
            
            if self.soko.currentgrid.isdead():
                self.text('DEADLOCK', (ox+sth, sh+sth), 'soko')
            else:
                btxt = 'unsolved' if self.currsol is None else 'Best: %d,%d' % self.currsol
                self.text(btxt, (ox+sth, sh+sth), 'bg2')
            
            ox = self.text('TIME: ', (sw*2//3, sh+sth), 'bg2')
            self.text('%s' % re.sub(',.*','',self.soko.curtime), (ox+sw*3//4, sh+sth), 'w')
        else:
            ox = self.text('REPLAY   ', (1, sh+sth), 'soko')
            ox += self.text('←→', (ox, sh+sth), 'w')
            ox += self.text(' Step [', (ox, sh+sth), 'bg2')
            ox += self.text('%d,%d' % (self.soko.revframe, self.soko.getsolution()[self.soko.revframe][1]), (ox, sh+sth), 'crat')
            ox += self.text('/', (ox, sh+sth), 'bg2')
            ox += self.text('%d,%d' % self.currsol, (ox, sh+sth), 'crat')
            ox += self.text(']   ', (ox, sh+sth), 'bg2')
            ox += self.text('P', (ox, sh+sth), 'w')
            ox += self.text(' [', (ox, sh+sth), 'bg2')
            ox += self.text('►' if self.replayauto else '║', (ox, sh+sth), 'crat' if self.replayauto else 'soko')
            ox += self.text(']   ', (ox, sh+sth), 'bg2')
            ox += self.text('↓↑', (ox, sh+sth), 'w')
            ox += self.text(' speed [', (ox, sh+sth), 'bg2')
            ox += self.text('%d' % (13 - self.replayspeed.bit_length()), (ox, sh+sth), 'crat')
            ox += self.text(']', (ox, sh+sth), 'bg2')
    
    def flipreplay(self, key=None):
        if key == pygame.K_F15:  self.soko.review(">")
        if key == pygame.K_RIGHT:self.soko.review(">")
        if key == pygame.K_LEFT: self.soko.review("<")
        
        if key == pygame.K_HOME:self.soko.review("r")
        if key == pygame.K_END: self.soko.review("f")

        if key == pygame.K_UP:   self.replayspeed //= 2
        if key == pygame.K_DOWN: self.replayspeed *= 2
        if self.replayspeed < 16: self.replayspeed = 16
        if self.replayspeed > 2048: self.replayspeed = 2048
        
        if key == pygame.K_p:
            self.replayauto = not self.replayauto
        if key in (pygame.K_p, pygame.K_F15):
            pygame.time.set_timer(pygame.REPLAY, self.replayauto * self.replayspeed)
            
        if self.soko.revframe >= len(self.soko.getsolution())-1:
            pygame.time.set_timer(pygame.REPLAY, 0)
            self.replayauto = False
        self.playfield(True)
    
    def dowin(self):
        self.playfield()
        
        # wen dies aufgerufen wird, ist das alte ergebnis schon weg.
        
        # fancy win screen
        solved = "Found a new Solution!"
        
        if self.currsol is not None:
            if self.currsol[0] <= len(self.soko.undo):
                solved = "Best solution so far: %d moves, %d pushes" % self.currsol
            else:
                solved = "Found a better solution! (less than %d moves)" % self.currsol[0]
                
        
        dlg = '''DONE!
            
            Pack:  [%d/%d] %s
            Level: [%d/%d] %s
            Moves: %d    Pushes: %d    Time: %s
            
            %s
            
            ''' % (
                self.soko.packinfo['idx'],  len(self.soko.packs)-1, 
                self.soko.packinfo['title'],
                self.soko.levelinfo['idx'], self.soko.packinfo['levels']-1, 
                self.soko.levelinfo['name'],
                len(self.soko.undo), self.soko.pushes, self.soko.curtime,
                solved
            )
        if solved[0] == "F": # this check feels filthy
            self.modal(dlg+"Saving solution...")
            self.soko.setsolution()
            self.playfield()
        self.modal(dlg+"Press a key to continue")
        self.waitkey()
        if self.soko.levelinfo['idx'] < self.soko.packinfo['levels']-1:
            # next level in pack
            self.loadlevel(self.soko.levelinfo['idx'] + 1)
        else:
            # next pack
            self.playfield()
            self.modal("\n\n    Pack Done.    \n\n    (Press a key)    \n\n")
            self.waitkey()
            if self.soko.packinfo['idx'] < len(self.soko.packs)-1:
                self.loadpack(self.soko.packinfo['idx'] + 1)
            else:
                self.playfield()
                self.modal("\n\n    Game Done.    \n\n    Starting Over.    \n\n    (Press a key)    \n\n")
                self.waitkey()
                self.loadpack(0)
    
    def confirmleave(self):
        leave = True
        if self.soko.levelinfo and len(self.soko.undo) > 0:
            self.modal(
                'Do you really want to leave the current level?\n\n'
                'All progress will be lost.\n\n'
                '(y/n)')
            leave = self.waitkey((pygame.K_y, pygame.K_z, pygame.K_n)) != pygame.K_n
            if not leave: self.flipmenu()
        return leave
    
    def rndlvl(self, dummy=None):
        """load a random level"""
        if self.confirmleave():
            self.soko.loadpack(random.randint(0, len(self.soko.packs)-1))
            self.soko.loadlevel(random.randint(0, self.soko.packinfo['levels']-1))
            return 4
        else:
            return self.state
    
    def loadpack(self, idx):
        if not self.soko.packinfo or self.soko.packinfo['idx'] != idx:
            self.soko.loadpack(idx)
        return 3

    def loadlevel(self, idx):
        self.soko.loadlevel(idx)
        cs = self.soko.getsolution()
        self.currsol = None
        if cs is not None:
            self.currsol = (len(cs)-1, cs[-1][1])
        return 4
    
    def resume(self, dummy=None):
        if not self.soko.packinfo: self.soko.loadpack(0)
        # fix startzeit (substract nonplayed time) This is a bit hacky :)
        if self.soko.starttime: # already started
            pt = self.soko.curtime.split(":")
            played = int(pt[0])*60*60 + int(pt[1])*60
            pt = pt[2].split(",")
            played += int(pt[0]) + int(pt[1]) / 1000.0
            self.soko.starttime = time.time() - played
        return 4

    def terminate(self, dummy=None):
        self.soko.savegame()
        return 0
    
    def gethelp(self, dummy=None):
        self.modal('''Keys in Menu:
        ·   [↓][↑]        -  navigate
        ·   [Return]      -  confirm selection
        ·   [S]           -  replay solution for selected level
        
        Keys in Game:
        ·   [←][↑][↓][→]  -  move sokoban
        ·   [R]           -  restart level
        ·   [U]           -  undo last move (unlimited)
        
        Keys in Replay:
        ·   [P]           -  play/pause
        ·   [↑][↓]        -  change speed
        ·   [←][→]        -  step
        
        Always:
        ·   [Q] or [ESC]  -  return to (previous) menu or quit
        ·   [F11]         -  toggle fullscreen
        
        Objective is to move all crates to targets.
        You can only push one crate at a time.
        
        ·                   Press a key to continue                   ·''')
        self.waitkey()
        self.flipmenu()
        return 1

    def mkmainmenu(self):
        def mainitem(s):
            srf = pygame.Surface((self.screen.get_width(), self.screen.get_height() // self.STATUS), pygame.SRCALPHA)
            self.text(s, (0,0), 'crat', srf)
            return srf
        # menulist is a list of tuples: (Surface, Function, Argument)
        # Function(Argument) should return an int representing next state.
        
        self.menulist = [
            (mainitem(' ►  Continue'         ), self.resume, None),
            (mainitem(' ►  Choose Level'     ), lambda x: self.confirmleave()+1, None),
            (mainitem(' ►  Play Random Level'), self.rndlvl, None),
            (mainitem(' ►  Help'             ), self.gethelp, None),
            (mainitem(' ►  Quit'             ), self.terminate, None)
        ]
    
    def mkpackmenu(self):
        # extend packs. first, get max horizontal width for each column
        idxlen = max(self.font.size(str(p))[0] for p in range(len(self.soko.packs)))
        levlen = max(self.font.size(str(len(p['levels'])))[0] for p in self.soko.packs)
        self.menulist = []
        for idx, pa in enumerate(self.soko.packs):
            # {'file', 'title', 'levels'}
            srf = pygame.Surface((self.screen.get_width(), self.screen.get_height() // self.STATUS), pygame.SRCALPHA)
            self.text(str(idx), (0,0), 'border', srf)
            self.text(pa['title'], (idxlen+self.STATUS,0), 'crat', srf)
            self.text(str(len(pa['levels'])), (self.screen.get_width()-(levlen), 0), 'w', srf)
            self.menulist.append((srf, self.loadpack, idx))
    
    def mklevelmenu(self):
        self.menulist = []
        idxlen = max(self.font.size(str(p))[0] for p in range(self.soko.packinfo['levels']))
        
        for idx, lvl in enumerate(self.soko.levellist()):
            srf = pygame.Surface((self.screen.get_width(), self.screen.get_height() // self.STATUS), pygame.SRCALPHA)
            self.text(str(idx), (0,0), 'border', srf)
            ox = self.text(lvl[0], (idxlen+self.STATUS, 0), 'crat', srf)
            cps = None
            if self.soko.packinfo['file'] in self.soko.solutions:
                if str(idx) in self.soko.solutions[self.soko.packinfo['file']]:
                    cps = self.soko.solutions[self.soko.packinfo['file']][str(idx)][1]
            if cps:
                self.text('%d moves' % len(cps), (idxlen+self.STATUS*2+ox, 0), 'soko', srf)
            else:
                self.text('unsolved', (idxlen+self.STATUS*2+ox, 0), 'border', srf)
            self.menulist.append((srf, self.loadlevel, idx))
    
    def flipmenu(self, key=None):
        if key == pygame.K_UP: self.menuselect -= 1
        if key == pygame.K_DOWN: self.menuselect += 1
        if key == pygame.K_PAGEUP: self.menuselect -= 10
        if key == pygame.K_PAGEDOWN: self.menuselect += 10
        if key == pygame.K_HOME: self.menuselect = 0
        if key == pygame.K_END: self.menuselect = len(self.menulist) - 1
        if key == pygame.K_RETURN: 
            fn = self.menulist[self.menuselect][1]
            self.state = fn(self.menulist[self.menuselect][2])
            # generate (unused) event to cycle main loop and redraw menu
            pygame.event.post(pygame.event.Event(pygame.USEREVENT + 3))
            return
        if key == pygame.K_s and self.state == 3:
            if self.soko.getsolution(self.menuselect):
                self.loadlevel(self.menuselect)
                self.replayauto = False
                self.replayspeed = 512
                self.state = 5
            return
        if self.menuselect >= len(self.menulist):
            self.menuselect = 0
        if self.menuselect < 0:
            self.menuselect = len(self.menulist)-1
        
        # display
        sh = self.screen.get_height()
        sw = self.screen.get_width()
        sth = sh // self.STATUS # zeilenhöhe
        sh -= 4*sth
        
        # clear screen
        self.screen.fill(gfx.colors['bg1'])
        # Obere Statuszeile
        tof = self.text('IKSOKOBAN 0.1  ', (0, 1), 'soko')
        if self.state == 1:
            self.text('%d levels in %d packs' % (self.soko.cumlevels, len(self.soko.packs)), (tof, 1), 'wall')
        if self.state == 2:
            self.text('Choose levelpack', (tof, 1), 'bg2')
        if self.state == 3:
            self.text(self.soko.packinfo['title'], (tof, 1), 'crat')
        # cursor
        cursorpos = self.menuselect
        if self.menuselect > self.STATUS//2 - 1:
            cursorpos = self.STATUS//2 - 1
        self.screen.fill(gfx.colors['wall'], (0, (2+cursorpos)*sth, sw, sth))
        # texte
        start = self.menuselect - self.STATUS//2 + 1
        if start < 0: start = 0
        stop = start + self.STATUS - 2
        if stop >= len(self.menulist): stop = len(self.menulist)
        
        toblit = [x[0] for x in self.menulist[start:stop]]
        for i in range(len(toblit)):
            self.screen.blit(toblit[i], (0, (2+i)*sth))
        
        # in main menu, display current level in bottom half
        if self.state == 1 and self.soko.packinfo:
            yof = (len(toblit)+3) * sth
            self.text('Current Level', (10, yof), 'w')
            yof += sth*3//2
            xof = self.text('Pack: ', (10, yof), 'bg2')+10
            xof += self.text('[', (xof, yof), 'b')
            xof += self.text(str(self.soko.packinfo['idx']), (xof, yof), 'wall')
            xof += self.text('/', (xof, yof), 'b')
            xof += self.text(str(len(self.soko.packs)-1), (xof, yof), 'wall')
            xof += self.text('] ', (xof, yof), 'b')
            xof += self.text(self.soko.packinfo['title'], (xof, yof), 'soko')
            yof += sth
            xof = self.text('Level: ', (10, yof), 'bg2')+10
            xof += self.text('[', (xof, yof), 'b')
            xof += self.text(str(self.soko.levelinfo['idx']), (xof, yof), 'wall')
            xof += self.text('/', (xof, yof), 'b')
            xof += self.text(str(self.soko.packinfo['levels']-1), (xof, yof), 'wall')
            xof += self.text('] ', (xof, yof), 'b')
            xof += self.text(self.soko.levelinfo['name'], (xof, yof), 'soko')
            yof += sth
            xof = self.text('Moves: ', (10, yof), 'bg2')+10
            xof += self.text(str(len(self.soko.undo)), (xof, yof), 'soko')
            xof += self.text('   Pushes: ', (xof, yof), 'bg2')
            xof += self.text(str(self.soko.pushes), (xof, yof), 'soko')
            xof += self.text('   Time: ', (xof, yof), 'bg2')
            xof += self.text(self.soko.curtime, (xof, yof), 'soko')
            yof += sth*3//2
            playdim = (sw-20, sh+4*sth-yof)
            # try 1:1 plot
            playf = self.plot(minfield=(0,0))
            if playf.get_width() > playdim[0] or playf.get_height() > playdim[1]:
                # calculate new dimensions
                zf = min(playdim[0] / float(playf.get_width()), playdim[1] / float(playf.get_height()))
                playf = self.plot(dim=(playf.get_width()*zf, playf.get_height()*zf), minfield=(0,0), floatzoom=True)
            self.screen.blit(playf, (10,yof))
        
        # in level-select, diplay preview in lower right corner
        if self.state == 3:
            # move current grid out of the way to generate preview
            cgrid = self.soko.currentgrid
            self.soko.currentgrid = self.soko.levellist()[self.menuselect][1]
            # try 1:1 plot
            playdim = (sw//2, sh//2)
            playf = self.plot(minfield=(0,0))
            if playf.get_width() > playdim[0] or playf.get_height() > playdim[1]:
                # calculate new dimensions
                zf = min(playdim[0] / float(playf.get_width()), playdim[1] / float(playf.get_height()))
                playf = self.plot(dim=(playf.get_width()*zf, playf.get_height()*zf), minfield=(0,0), floatzoom=True)
            self.screen.blit(playf, (sw-playf.get_width(),sth*1.75))
            # restore current grid
            self.soko.currentgrid = cgrid
    
    def main(self):
        trons = {
            pygame.K_UP:   '^', pygame.K_DOWN:  'v',
            pygame.K_LEFT: '<', pygame.K_RIGHT: '>',
            pygame.K_r:    'r', pygame.K_u:     'u'
        }
        
        self.state = 1 # 1=main menu 2=packselect 3=levelselect 4=play
        self.menuselect = 0
        self.lastdir = '↑' # orientation of player
        # timer-events & repeated keypress
        pygame.PLAYSECOND = pygame.USEREVENT + 1
        pygame.REPLAY = pygame.USEREVENT + 2
        self.mkmainmenu()
        self.flipmenu()
        pygame.display.flip()
        oldstate = self.state
        
        while self.state:
            # or for loop through the event queue?
            ev = pygame.event.wait()
            if ev.type == pygame.MOUSEMOTION: continue # ignore mouse
            if ev.type == pygame.KEYDOWN: # global keypresses first (local keypresses see below)
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    if self.state == 4:
                        self.soko.updatetime()
                        self.state = 1
                    elif self.state == 5:
                        pygame.time.set_timer(pygame.REPLAY, 0)
                        self.state = 3
                    elif self.state < 4:
                        self.state -= 1
                
                if ev.key == pygame.K_F11:
                    if self.curr[0] == self.disp[0] and self.curr[1] == self.disp[1]:
                        # is fullscreen, reset to default
                        self.resize()
                    else:
                        # is window, resize to screen res and make fullscreen
                        self.resize(*self.disp)
                        pygame.display.toggle_fullscreen()
                    # invalidate oldstate to force rerendering
                    oldstate = -1
            
            if ev.type == pygame.REPLAY and self.state == 5:
                self.flipreplay(pygame.K_F15)

            if ev.type == pygame.PLAYSECOND:
                self.soko.updatetime()
                self.playfield()
            
            if ev.type == pygame.VIDEORESIZE:
                self.resize(ev.w, ev.h)
                # invalidate oldstate to force rerendering
                oldstate = -1
            
            if ev.type == pygame.QUIT:
                self.state = 0
            
            if oldstate != self.state:
                oldstate = self.state
                # update menu
                if self.state == 1:
                    self.mkmainmenu()
                    self.menuselect = 0
                if self.state == 2:
                    self.mkpackmenu()
                    if self.soko.packinfo:
                        self.menuselect = self.soko.packinfo['idx']
                    else:
                        self.menuselect = 0
                if self.state == 3:
                    self.mklevelmenu()
                    if self.soko.levelinfo: 
                        self.menuselect = self.soko.levelinfo['idx']
                # plot menu
                if 0 < self.state < 4:
                    self.flipmenu()
                # playfield
                if self.state == 4:
                    pygame.time.set_timer(pygame.PLAYSECOND, 1000)
                    self.playfield()
                else:
                    pygame.time.set_timer(pygame.PLAYSECOND, 0)
                if self.state == 5: self.flipreplay()
            
            if ev.type == pygame.KEYDOWN: # local keypress (different depending on current state)
                if 0 < self.state < 4:
                    self.flipmenu(ev.key)
                if self.state == 4:
                    if ev.key in trons:
                        self.lastdir = trons[ev.key]
                        if self.soko.play(trons[ev.key]):
                             self.dowin()
                    self.playfield()
                if self.state == 5:
                    self.flipreplay(ev.key)
            
            pygame.display.flip()
        self.terminate()


def main(args):
    return 0

if __name__ == '__main__':
    g = Pygameban('levels.zip')
    g.main()


