Es ist ja nicht so, daß es nicht schon Drölfundneunzigmilliarden Sokoban-implementierungen gibt.
Aber im Grunde ist das nach "Hello World", "Fizzbuzz" und "Game of Life" so eine Standard-Fingerübung :)

Meine Version kann folgendes
============================

 - läuft unter python 2 und 3 unter Windows und Linux (also vermutlich auch Mac)
 - Zwei Ausgabemöglichkeiten:
   - ANSI-Terminal (`ansiban.py`)
   - Grafisch (`pygameban.py`) mit Originalgrafik in augenschonenderen Farben
 - Vollständiges Undo
 - Beim Beenden wird der aktuelle Spielstand gespeichert
 - Die grafische Variante speichert die beste Lösung pro Level, die gespeicherte Lösung kann man sich anzeigen lassen (replay)
 - Levels im Standard Sokoban-Format werden direkt aus der Zipdatei `levels.zip` geladen. Diese enthält alle Levels von http://www.sourcecode.se/sokoban/levels


Installation
============

Windows
-------

Die einfachste Variante ist, sich die `iksokoban-win32.7z` zu ziehen und zu entpacken. Das ist ein py2exe-Paket und enthält alles, was man braucht.
Sowohl die ANSI- also auf die grafische Version sind enthalten.

Alternativ: Python 2.7 installieren, die Pakete `pygame`, `win_unicode_console`, `colorama` per pip installieren, dann `ansiban.py` oder `pygameban.py` starten

Falls man die windows-binary selbst bauen möchte: siehe `build.bat`

Andere Systeme
--------------

man benötigt Python 2 oder 3 und ein passendes pygame. Jedenfalls wenn man grafisch spielen möchte. `ansiban.py` läuft auch ohne pygame.

Das Verzeichnis `sprites` benötigt man nur teilweise um das Windowsbinary zu erstellen, ansonsten sind darin sind nur die Vorlagen.
Die eigentlichen Grafiken sind in gfx.py hinterlegt. Dort sind auch die Farben anpassbar.


Spielstände / Lösungen
======================

Werden als gepackte JSON-Datei gespeichert (`sokoban.current.jgz`, `sokoban.solutions.hgz`) und zwar unter Windows in dem Verzeichnis, in dem das Binary abgelegt ist
(damit alles schön portable bleibt) und bei allen anderen Platformen im Home-Verzeichnis.

Wenn man das für sich anders möchte: siehe `sokoban.py`, `class Sokoban`

Screenshots
===========

Main Menu
---------
pygameban.py:
![pygameban menu](https://github.com/inkeso/showcase/raw/master/sokoban/screenshot01.png)

ansiban.py:
![ansiban menu](https://github.com/inkeso/showcase/raw/master/sokoban/ansiban3.png)

Level (Play)
------------
pygameban.py:
![pygameban play](https://github.com/inkeso/showcase/raw/master/sokoban/screenshot02.png)

ansiban.py:
![ansiban play 1](https://github.com/inkeso/showcase/raw/master/sokoban/ansiban1.png)
![ansiban play 2](https://github.com/inkeso/showcase/raw/master/sokoban/ansiban2.png)

Replay-Demo video
-----------------
https://github.com/inkeso/showcase/raw/master/sokoban/replay_level10.m4v

