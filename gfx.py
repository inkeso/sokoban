#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame, zlib, base64, io, time
from sokoban import Grid


colors = {
        'b'     : (  0,   0,   0),
        'w'     : (255, 255, 255),
        'bg1'   : ( 34,  34,  34),
        'bg2'   : ( 85,  85,  85),
        'border': ( 60,  60,  60),
        'wall'  : (142,  38,  38),
        'crat'  : ( 84, 183, 252),
        'targ'  : (  0,   2,   0),
        'crag'  : (252,  84,  84),
        'soko'  : (255,  84,  84),

}

if time.strftime("%m%d") == '0401': # gneeheehee
    for bg in ('bg1', 'bg2', 'border', 'crat'): colors[bg] = (0,253,253)
    for fg in ('wall', 'crag', 'soko'): colors[fg] = (253,0,253)
    colors['gfont'] = (0,0,0)

def str2img(dim, s):
    return pygame.image.fromstring(zlib.decompress(base64.b64decode(s)), dim, 'P')

def icon():
    # load directly from 32x32 bmp (needs to be ready before pygame.display.set_mode)
    # but the icon is still messed up when using py2exe. So we need it in sprites as well.
    BMP = b'eJyV0TEOwjAMBVC3olMniwsgXyE3qCIxsaDmFmzcoyeORF3/BERqkPorD8+JM7jTbenJsmg9tC6lOjrhQM/PI2og1HS9P+lgeqf30i+lRPOcKedMrJEaRhqL6JyV+KZicm3XERtoLBLfjtrYOarDFnV0HWp8h08842KZciygNWTvbVtw2Vhr5mqu+z1qwXO/zF9/z/GfrEwDTFw='
    w = io.BytesIO(zlib.decompress(base64.b64decode(BMP)))
    img = pygame.image.load(w, ".bmp")
    img.set_colorkey((255,0,255))
    w.close()
    return img

sprites = { # displaysize is [16, 12], imagesize may vary
    'icon':                    str2img((16, 16), b'eJxtzzESACEMAsBkhobK///2EPS0kEJdCo1jPALnYiunMFW8DWz7DoCMSaoQU8ydcg5JT5+i4yqryoa80nngd0a0s6yBloH7e/nhBxtOBxU='),
    'sokoleft' :               str2img((20, 16), b'eJx9zUsKACAMQ8Fk6Sr3v62VotgPfcuBEGlqnRLRikhvVSIx29v+dj+ieY2hbBNJsNNsakhobGwDzucOaQ=='),
    'sokoright':               str2img((20, 16), b'eJyFzzEOACAIQ9EyMnH/21qctCX6xxcNUPUqO6VgN25iByHCcLTp7zADmbYM4NZo+wEcDbmtUe+l6bNPC85ZDmk='),
    'sokovert' :               str2img((20, 14), b'eJyNzTsOACAIA1AYO/X+t/UDghJN7EL6Bko+oz0XqvhngBmAJMNxF1qxaDxLShOZIpI73TzbdBhPYzG6eWt/7gr7'),
    Grid.WALL  :               str2img((24, 16), b'eJxtkDEOACAIA7t05v+/1dBqUGDA5IALApIAeR4gMvBzVzpXYeLcBbRIlVvPiPxKP2fOTJxdbr/7ykKP/+H2N438UQYS2h/D18zLLW7WVYdtF/eLBMo='),
    Grid.CRATE :               str2img((20, 14), b'eJx9j0EKADEIA5OLV///20bXilLY0AiNQ6vumPIUjGA7U0W2rPD2rXkUNyqJ6OWlqgIUESoOf9x47+PWv80NK3r20CyaOlq8jpMr79AP+XcDOw=='),
    Grid.TARGET:               str2img((20, 16), b'eJzj56cKYGfHFAIjdCF0QXYUCpXNjl8Mm16sdmB1C1Y3kw4AYDUSIQ=='),
    Grid.CRATE | Grid.TARGET : str2img((20, 14), b'eJx9j0EOACEIA8vNG///7ZZ2MRgTDRgzjAqZmCu1sAKxU5QolEEQhq4ztNUZ9spcaBdVE/LVAvg9hzy8vPGevePf9mZ/RNccLLNr/dlZoZFPmB/QfwL2'),
}

def mapsprites():
    for k, v in sprites.items():
        if v.get_bitsize() == 8:
            v.set_palette([
                colors['b'], colors['w'], colors['bg1'], colors['bg2'], colors['border'],
                colors['wall'], colors['crat'], colors['targ'], colors['crag'], colors['soko'],
                (0,0,0),(0,0,0),(0,0,0),(0,0,0),(0,0,0),(255,0,255)
            ])
            v.set_colorkey((255,0,255))
        sprites[k] = v.convert()

def importsprites():
    import sys.stdout.write as wr
    pygame.init()
    x = open("sprites/icon.bmp")
    BMP = ''.join(base64.encodestring(zlib.compress(x.read())).split())
    x.close()
    wr("BMP = '%s'\n" % BMP)
    wr("sprites = {\n")
    for f in ('icon.gif', 'sokoleft.gif', 'sokoright.gif', 'sokovert.gif', 'wall.gif', 'crate.gif', 'target.gif', 'cratarg.gif'):
        img = pygame.image.load("sprites/"+f)
        b64 = ''.join(base64.encodestring(zlib.compress(img.get_buffer().raw)).split())
        wr("    '%s': str2img((%d, %d), '%s'),\n" % (f.replace("sprites/","").replace(".gif",""), img.get_width(), img.get_height(), b64))
    wr("}\n")
