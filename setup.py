# create levels.zip:
# (all files in desired order)
# zip -9 ../levels.zip Original.txt Xsokoban.txt abedho/* belyae/* buchwe/* casami/* caussa/* cerjak/* clercq/* findus/* garcia/* grigor/* hofmar/* hollnd/* mantzo/* marqus/* murase/* nakami/* negova/* patelv/* peloux/* razorf/* reilly/* reinke/* skinnr/* tchong/* thrabb/* trifun/* others/*

# this file is only used for windows-exe-distribution.

from distutils.core import setup
import py2exe, os

opts = {"py2exe": {
    'bundle_files': 2,
    'optimize': 2,
    'ascii': True,
    'excludes': [
        '_gtkagg', '_tkagg', 'bsddb', 'curses', 'email', 'pywin.debugger', 'pywin.debugger.dbgcon', 'pywin.dialogs', 'tcl', 'Tkconstants',
        'Tkinter', '_ssl', '_hashlib', 'doctest', 'pdb', 'unittest', 'difflib', 'inspect', 'optparse', 'pickle', 'calendar', 'ssl', 'socket',
        'pyexpat', 'distutils', 'logging', 'tarfile', 'bz2', 'unicodedata', 'pkg_resources'],
    'dll_excludes': [
        'libgdk-win32-2.0-0.dll', 'libgobject-2.0-0.dll', 'tcl84.dll', 'tk84.dll', 'libmpg123-0.dll', 'libvorbis-0.dll', 'libvorbisfile-3.dll',
        'SDL_mixer.dll', 'libjpeg-8.dll', 'libpng16-16.dll', 'libtiff-5.dll', 'libwebp-5.dll'],
    'includes': ['encodings.utf_8', 'encodings.utf_16_le', 'encodings.ascii'],
    'compressed': True
}}
setup(
  windows = [{"script":"pygameban.py"}],
  console = [{"script":"ansiban.py"}],
  options=opts,
  data_files = [("", ["levels.zip"])],
)
