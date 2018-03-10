@echo off

REM install Python 2.7
REM install py2exe (0.6.9 via installer from sourceforge, not pip)
REM install pygame, win_unicode_console, colorama via pip
REM
REM Stick to Python 2.7 (or 3.4). Python 3.6 is not supported by py2exe (as of 2017-11-14).
REM (Python 3.4 is untested)
REM
REM Since there is a bug with icon-embedding in py2exe, we also need ResoureceHacker (Angus Johnson)
REM 7zip is also handy

rmdir /Q /S iksokoban
C:\Python27\python.exe setup.py py2exe -q
C:\tools\reshacker\ResourceHacker -open dist\pygameban.exe -save dist/iksokoban_gfx.exe -action add -res sprites\exeicon.ico -mask ICONGROUP,MAINICON,
rename dist\ansiban.exe iksokoban_con.exe

echo Add font.ttf to libraray.zip
mkdir pygame
copy font.ttf pygame\freesansbold.ttf
C:\tools\7zip\7z a dist\library.zip pygame\freesansbold.ttf >nul
echo create source.7z
C:\tools\7zip\7z a dist\source.7z *.py testlevels.zip sprites font.ttf build.bat >nul

echo Cleanup
del dist\pygameban.exe
del dist\w9xpopen.exe
rmdir /Q /S pygame
rmdir /Q /S build

echo Create iksokoban-win32.7z
rename dist iksokoban
C:\tools\7zip\7z a iksokoban-win32.7z iksokoban >nul
