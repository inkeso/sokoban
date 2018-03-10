#!/usr/bin/env python
# -*- coding: utf-8 -*-

# converter: konvertiert "savegames" oder "replays" oder wie wir das nennen von
# "frame für frame" nach "startframe und bewegungen" um platz, ladezeit und RAM
# zu sparen.
# und auch in die Gegenrichtung.

import os, sys, json, gzip, sokoban

def stack2steps(grid):
    startframe = grid[0][0]
    moves = "" # < v ^ >
    for i in range(1, len(grid)):
        # compare current frame with last one, find movement of gunther. We don't care for anthing else.
        ty,tx = sokoban.Grid(grid[i][0]).findplayer()
        oy,ox = sokoban.Grid(grid[i-1][0]).findplayer()
        if tx < ox: moves += "<"
        if tx > ox: moves += ">"
        if ty < oy: moves += "^"
        if ty > oy: moves += "v"
    return (startframe, moves)

def steps2stack(steps):
    targ = [[steps[0],0]]
    tg = sokoban.Grid(sokoban.Grid(steps[0]).copy())
    lp = 0 # puhed-counter
    for s in steps[1]:
        lp += tg.move(s)
        targ.append([tg.copy(), lp])
    return targ

def prettyjson(sol):
    # pretty print for human beings <3
    ws = json.dumps(sol)
    ws = ws.replace('}, "', '},\n\n"') # new pack
    ws = ws.replace('": {"','": {\n    "') # first level
    ws = ws.replace('": [[[', '": [[\n        [') # startframe
    ws = ws.replace('], [', '],\n        [') # rows of startframe
    ws = ws.replace(']], "', ']\n        ],"') # solution (steps)
    ws = ws.replace('"], "', '"],\n    "') # next level
    return ws

def main():
    if len(sys.argv) < 3: 
        sys.stderr.write("Usage: %s <sokoban.solutions.jgz> <sokoban.solutions.hgz>\n" % sys.argv[0])
    
    fo = gzip.open(sys.argv[1], 'r')
    solutions = json.load(fo)
    fo.close()
    
    solnu = {}
    for kk in solutions.keys():
        pack = solutions[kk]
        sys.stdout.write("%s: " % kk)
        solnu[kk] = {}
        for pp in pack.keys():
            solnu[kk][pp] = stack2steps(pack[pp])
            sys.stdout.write("%s | " % pp)
            sys.stdout.flush()
        sys.stdout.write("\n")
    fo = gzip.open(sys.argv[2], 'w')
    fo.write(prettyjson(solnu).encode("ascii"))
    fo.close()

if __name__ == '__main__':
    main()

