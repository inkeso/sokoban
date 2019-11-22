#!/usr/bin/env python

# this ist fully python 2 & 3 compatible now.
import re, os, sys, time, json, gzip, zipfile, converda

class Grid:
    # [
    #   [n, n, n, ...],
    #   [...], 
    # ]
    TARGET = 0b0001
    CRATE  = 0b0010
    WALL   = 0b0100
    SOKO   = 0b1000
    def __init__(self, grid):
        # make it squre, save dimensions
        self.height = len(grid)
        self.width = max(len(row) for row in grid)
        self.grid = grid
        for r in range(len(grid)):
            if len(grid[r]) < self.width: 
                grid[r] += [0] * (self.width - len(grid[r]))

        # check level for validity
        # (1 Player, same number of crates & targets (et least 1), not solved)
        player = self.count(self.SOKO) + self.count(self.SOKO | self.TARGET)
        crates = self.count(self.CRATE)
        target = self.count(self.TARGET) + self.count(self.SOKO | self.TARGET)
        cratar = self.count(self.CRATE | self.TARGET)
        assert self.width * self.height > 2, "Level too small (%d x %d)" % (self.width, self.height)
        assert player == 1, "Level invalid: %d players" % player
        assert crates == target, "Level invalid: %d crates, %d targets" % (crates, target)
        assert crates + cratar > 0, "Level invalid: no crates at all"
    
    def copy(self): return [[x for x in y] for y in self.grid]
    
    def count(self, what):
        cnt = 0
        for row in self.grid:
            for col in row:
                if col == what: cnt += 1
        return cnt
    
    def iswin(self):
        """
        How to count if current grid is won?
          - crates == 0 AND targets == 0
          - but crates always equals targets so...
        """
        return self.count(self.CRATE) == 0
    
    def isdead(self):
        """
        Check whether a deadlock is present (the obvious ones):
        if a 2x2-square is fully occupied and at least 1 of the items is a crate
        not outside of a target, we have a deadlock.
        Also if 2 neighbors of a non-target-crate are walls.
        TODO: Detect more deadlocks
        """
        for r in range(self.height - 1):
            for c in range(self.width - 1):
                quad = self.grid[r][c:(c+2)] + self.grid[r+1][c:(c+2)]
                if any([q == self.CRATE for q in quad]):
                    if all([1 < q < 8 for q in quad]):
                        return True
                if quad[0] == self.CRATE and quad[1] == self.WALL and quad[2] == self.WALL: return True
                if quad[1] == self.CRATE and quad[0] == self.WALL and quad[3] == self.WALL: return True
                if quad[2] == self.CRATE and quad[0] == self.WALL and quad[3] == self.WALL: return True
                if quad[3] == self.CRATE and quad[1] == self.WALL and quad[2] == self.WALL: return True
        return False
    
    def findplayer(self):
        for row in enumerate(self.grid):
            for col in enumerate(row[1]):
                if col[1] & self.SOKO:
                    return (row[0], col[0])

    def move(self, d):
        """Move Player in given direction."""
        offset = {"^": (-1,0), "v": (1,0), "<": (0,-1), ">": (0,1)}[d]
        # get target fields (and bound check a bit)
        pushed = 0
        player = self.findplayer()
        tf = (player[0] + offset[0],   player[1] + offset[1]  )
        bf = (player[0] + offset[0]*2, player[1] + offset[1]*2)
        # boundary check for soko
        if tf[0] < 0 or tf[1] < 0 or tf[0] >= self.height or tf[1] >= self.width:
            return None
        # check collision
        if self.grid[tf[0]][tf[1]] & self.WALL: return None
        if self.grid[tf[0]][tf[1]] & self.CRATE: 
            # boundary-check for box
            if bf[0] < 0 or bf[1] < 0 or bf[0] >= self.height or bf[1] >= self.width:
                return None
            # check target field for crate
            if self.grid[bf[0]][bf[1]] & (self.WALL | self.CRATE):
                return None
            # fine, move box
            pushed = 1
            self.grid[bf[0]][bf[1]] += self.CRATE
            self.grid[tf[0]][tf[1]] -= self.CRATE
        # move soko
        self.grid[tf[0]][tf[1]] += self.SOKO
        self.grid[player[0]][player[1]] -= self.SOKO
        return pushed
    
    def __str__(self):
        return "\n".join(" ".join("%X" % y for y in x) for x in self.grid)


class Sokoban:
    """
    Load/manage levelpacks, solutions and resume. Play or review a single level.
    Soo... everything except frontend.
    """
    DECODE = {
        ' ' : 0,
        '#' : Grid.WALL,
        '@' : Grid.SOKO,
        '$' : Grid.CRATE,
        '.' : Grid.TARGET,
        '*' : Grid.CRATE | Grid.TARGET,
        '+' : Grid.SOKO | Grid.TARGET,
    }
    PREFIX = os.path.dirname(os.path.abspath(sys.argv[0]))
    # save in homedir on linux.
    # but in program-dir in windows to keep it portable
    prf = os.path.expanduser("~")
    if sys.platform == "win32": prf = PREFIX
    SAVEFILE = os.path.join(prf,"sokoban.current.jgz")
    SOLFILE = os.path.join(prf,"sokoban.solutions.hgz")
    
    def __init__(self, levelzip):
        # levels are stored in a zipfile. Be careful to get it zipped up in order.
        self.levelzip = zipfile.ZipFile(os.path.join(self.PREFIX, levelzip))
        # {'file': str, 'title': str, 'levels': [(str, Grid), ...]}
        self.packs = [self.fileinfo(fi) for fi in self.levelzip.infolist() if fi.filename.endswith(".txt")]
        # cummulated number of available levels
        self.cumlevels = sum(len(x['levels']) for x in self.packs)
        
        self.packinfo = None # {'idx': int, 'file': str, 'title': str, 'levels': int}
        self.levelinfo = None # {'idx': int, 'name': str}
        self.currentgrid = None # Instance of Grid
        self.starttime = None # Level started (first movement) (seconds since epoch)
        self.curtime = "--:--:--" # human readable playtime for current level
        self.pushes = 0 # number of pushes in this level. Number of moves == len(undo)
        self.undo = [] # store a stack of previous grid-arrays and number of pushes
        
        # load last state (if any)
        try:
            self.loadgame()
        except Exception as e:
            sys.stdout.write("Cannot load last game: %s\n" % e)
        
        # load solutions
        self.solutions = {} # dict {filename: {levelindex: undo[], }, }
        self.revidx = None # current review indizes
        self.revstack = None
        self.revframe = 0 # current review-frame
        try:
            fo = gzip.open(self.SOLFILE, 'r')
            self.solutions = json.load(fo)
            fo.close()
        except:
            # maybe not played yet.
            pass
    
    def canonicpath(self, pth):
        """
        take a valid path- or filename and return it's 'canonic' form:
        strip PREFIX and use a slash as path-separator
        """
        return "/".join(os.path.split(pth.replace(os.path.join(self.PREFIX, ""), "")))
    
    def realpath(self, pth):
        """
        take a 'canonical' path- or filename and return a valid path
        """
        return os.path.join(self.PREFIX, *pth.split("/"))
    
    def readfile(self, filename):
        """
        Read textfile with levelset (packfile).
        return {
            'file' : filename,
            'title' : title,
            'levels' : levels # list of tuples [(title, grid), ...]
        }
        """
        # read default sokoban-format 0.08
        levelfile = self.levelzip.open(filename)
        # 1. Row starts with semicolon: Title of Levelpack
        title = levelfile.readline().decode("utf-8").strip()
        assert len(title) > 0 and title[0] == ";", "File does not start with ;"
        name = re.compile("^;+\\s*(.*)")
        title = name.search(title).group(1)
        levels = []
        currentlevel = []
        levelname = ""
        rowcount = 1
        for line in levelfile:
            line = line.decode("utf-8", "ignore")
            rowcount += 1
            # Leere Zeilen ignorieren
            if len(line.strip()) == 0: continue
            if line.startswith(";"):
                if levelname and currentlevel:
                    try:
                        newg = Grid(currentlevel)
                        assert not newg.iswin(), "All crates on their targets. Nothing to do."
                        levels.append((levelname, newg))
                    except AssertionError as e:
                        sys.stderr.write("[%s : %d] '%s': %s\n" % (filename, rowcount, levelname, str(e)))
                    
                levelname = name.search(line).group(1).strip()
                currentlevel = []
            else:
                if levelname:
                    try:
                        currentlevel.append([self.DECODE[x] for x in line.rstrip()])
                    except KeyError as e:
                        sys.stderr.write("[%s : %d] Error decoding %s\n" % (filename, rowcount, str(e)))
                        levelname = ""
                        currentlevel = []
                else:
                    sys.stderr.write("[%s : %d] Warning: Reading (ignoring) level without name\n" % (filename, rowcount))
        # den letzten nicht vergessen
        if levelname and currentlevel:
            try:
                levels.append((levelname, Grid(currentlevel)))
            except AssertionError as e:
                sys.stderr.write("[%s : %d] '%s': %s\n" % (filename, rowcount, levelname, str(e)))
        levelfile.close()
        
        return {
            'file' : filename,
            'title' : title,
            'levels' : levels # list of tuples [(title, grid), ...]
        }

    def fileinfo(self, finfo):
        """read levelset, only return packtitle and number of levels"""
        fileobj = self.levelzip.open(finfo)
        title = fileobj.readline().decode("utf-8")
        assert len(title) > 0 and title.startswith(";"), "File does not start with ;"
        title = re.search("^;+\\s*(.*)", title).group(1)
        nums = sum(x.strip().startswith(b";") for x in fileobj)
        fileobj.close()
        return {'file': finfo.filename, 'title': title, 'levels': 'x'*nums}
        
    def loadpack(self, idx):
        pug = self.readfile(self.packs[idx]['file'])
        self.packs[idx] = pug
        self.packinfo = {
            'idx'  : idx,          'file'  : pug['file'], 
            'title': pug['title'], 'levels': len(pug['levels'])
        }
        self.loadlevel(0)
        
    def levellist(self): 
        assert self.packinfo is not None, "No current levelpack"
        return self.packs[self.packinfo['idx']]['levels']
    
    def loadlevel(self, idx):
        lvl = self.levellist()[idx]
        self.levelinfo = {'idx': idx, 'name': lvl[0]}
        self.currentgrid = Grid(lvl[1].copy())
        self.starttime = None
        self.curtime = "--:--:--"
        self.pushes = 0
        self.undo = []
        self.revframe = 0
        
    def updatetime(self):
        if self.starttime:
            delta = time.time() - self.starttime
            hmsh = (delta // 60 // 60, (delta // 60) % 60, delta % 60, int(delta % 1 * 1000))
            self.curtime = "%02d:%02d:%02d,%d" % hmsh
    
    def play(self, action="r"):
        """
        Start playing currentlevel from currentpack One call for each action. 
        return true if solved, false otherwise.
        < v ^ > move
        u undo
        r restart
        
        """
        assert self.levelinfo is not None, "No current level"
        if action == "r": self.loadlevel(self.levelinfo['idx'])
        if action in ("<","^", "v", ">"): 
            if not self.starttime: self.starttime = time.time()
            self.updatetime()
            self.undo.append((self.currentgrid.copy(), self.pushes))
            moved = self.currentgrid.move(action)
            if moved is not None:
                self.pushes += moved
                if self.currentgrid.iswin():
                    # self.setsolution()  # call this in frontend (may take a while)
                    return True
            else:
                self.undo.pop() # do not keep non-movements
        if action == "u": 
            if len(self.undo) > 0:
                laststep = self.undo.pop()
                self.currentgrid = Grid(laststep[0])
                self.pushes = laststep[1]
            else:
                self.loadlevel(self.levelinfo['idx'])
        return False
    
    def review(self, action="r"):
        """
        Start reviewing solution for currentlevel from currentpack.
        One call for each action.
        Be careful not to mix up play- and review-calls in the frontend. It will mess things up.
        (i.e. call loadlevel() bevor entering each 'mode')
        < > previous/next frame
        r restart (goto first frame)
        f finish (goto last frame)
        returns current frame (Grid, pushes)
        """
        cs = self.getsolution()
        assert cs is not None, "No solution for this level yet."
        if action == "r": self.revframe = 0
        if action == "f": self.revframe = len(cs) - 1
        if action == "<": self.revframe = max(0, self.revframe - 1)
        if action == ">": self.revframe = min(len(cs) - 1, self.revframe + 1)
        
        self.currentgrid = Grid(cs[self.revframe][0])
        self.pushes = cs[self.revframe][1]
    
    def savegame(self):
        if self.levelinfo is None:
            return
        obj = {
            'packfile' : self.packinfo['file'],
            'levelidx' : self.levelinfo['idx'],
            'curtime'  : self.curtime,
            'undo'     : self.undo + [(self.currentgrid.copy(), self.pushes)],
        }
        # pickle to file...
        fo = gzip.open(self.SAVEFILE, "wb")
        fo.write(json.dumps(obj).encode("ascii"))
        fo.close()
    
    def loadgame(self):
        fo = gzip.open(self.SAVEFILE, "rb")
        obj = json.load(fo)
        fo.close()
        try:
            self.loadpack([x['file'] for x in self.packs].index(obj['packfile']))
        except ValueError as e:
            pass
            #sys.stderr.write("Failed to find packfile %s\n" % obj['packfile'])
        else:
            self.loadlevel(obj['levelidx'])
            if obj['curtime'] != "--:--:--":
                pt = obj['curtime'].split(":")
                played = int(pt[0])*60*60 + int(pt[1])*60
                pt = pt[2].split(",")
                played += int(pt[0]) + int(pt[1]) / 1000.0
                self.starttime = time.time() - played
                self.updatetime()
            if obj['undo']:
                self.undo = obj['undo']
                uds = self.undo.pop()
                self.currentgrid = Grid(uds[0])
                self.pushes = uds[1]
    
    def getsolution(self, idx=None):
        """
        get solution for current level or idx level in current pack
        [(gridarray, pushes), (griddarray, pushes), ...]
        """
        assert self.levelinfo is not None or idx is not None, "No current or selected level"
        idx = str(idx if idx is not None else self.levelinfo['idx'])
        if (self.revidx is not None
            and self.revstack is not None
            and self.revidx[0] == self.packinfo['file']
            and self.revidx[1] == idx):
            return self.revstack

        if self.packinfo['file'] not in self.solutions: return None
        csp = self.solutions[self.packinfo['file']]
        if idx not in csp: return None
        self.revstack = converda.steps2stack(csp[idx])
        self.revidx = (self.packinfo['file'], idx)
        return self.revstack
    
    def setsolution(self):
        assert self.levelinfo is not None, "No current level"
        # copy undo-stack and add current position
        steps = [(x[0], x[1]) for x in self.undo]
        steps += [(self.currentgrid.copy(), self.pushes)]
        # is there already a better solution (less moves)?
        csm = self.getsolution()
        if csm is not None and len(steps) >= len(csm):
            return False
        if self.packinfo['file'] not in self.solutions:
            self.solutions[self.packinfo['file']] = {}
        self.solutions[self.packinfo['file']][str(self.levelinfo['idx'])] = converda.stack2steps(steps)
        # save to file
        fo = gzip.open(self.SOLFILE, 'w')
        fo.write(converda.prettyjson(self.solutions).encode("ascii"))
        fo.close()
        return True


if __name__ == '__main__':
    import random
    g = Sokoban("levels.zip")
    #g = sokoban.Sokoban("testlevels.zip")
    sys.stdout.write("Found %d levels in %d packs\n" % (g.cumlevels, len(g.packs)))
    #g.loadpack(random.randint(0, len(g.packs)-1))
    
    g.loadpack(429)
    sys.stdout.write("Loaded random pack: %s [%s]\n" % (g.packinfo['file'], g.packinfo['title']))
    g.loadlevel(random.randint(0, g.packinfo['levels']-1))
    sys.stdout.write("Loaded random level: %d [%s]\n" % (g.levelinfo['idx'], g.levelinfo['name']))
    sys.stdout.write(str(g.currentgrid))
    sys.stdout.write("\n")

