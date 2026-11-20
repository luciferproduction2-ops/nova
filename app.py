#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nova — application (interface + fonctions).
Ce fichier est celui qui se met à jour automatiquement : il est chargé par
nova.py (le lanceur), qui le télécharge depuis GitHub quand une nouvelle
version est publiée.
"""
import bisect
import hashlib
import json
import os
import random
import re
import sys
from array import array
from collections import deque
from pathlib import Path

from PySide6.QtCore import (QObject, Property, QSettings, QStandardPaths, QTimer,
                            QUrl, Signal, Slot, QPointF, QRectF, Qt)
from PySide6.QtGui import (QColor, QDesktopServices, QGuiApplication, QIcon,
                           QLinearGradient, QPainter, QPainterPath, QPixmap)
from PySide6.QtQml import QQmlApplicationEngine
from PySide6 import QtMultimedia, QtQuick  # noqa: F401  (embarque le moteur vidéo dans le .exe)
from PySide6.QtMultimedia import (QAudio, QAudioBufferOutput, QAudioFormat, QAudioOutput,
                                  QAudioSink, QMediaDevices, QMediaPlayer, QVideoFrame,
                                  QVideoSink)
from PySide6.QtQuickControls2 import QQuickStyle

APP_NAME = "Nova"
APP_VERSION = 2  # augmenter à chaque mise à jour publiée

VIDEO_EXT = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv", ".ts",
    ".m2ts", ".mts", ".mpg", ".mpeg", ".3gp", ".ogv", ".vob", ".divx",
}
SUB_EXT = {".srt", ".vtt"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_GAIN = 3.0

THEME = {
    "bg": "#0A0A0F",
    "panel": "#111118",
    "panel2": "#1B1B25",
    "text": "#F2F2F7",
    "muted": "#8B8B9E",
    "accent": "#8B5CF6",
    "accent2": "#EC4899",
}

SUB_STYLE_DEFAULT = {
    "size": 100,          # % de la taille de base
    "color": "#FFFFFF",
    "style": "outline",   # outline | shadow | box
    "boxOpacity": 0.55,
    "position": 7,        # % de la hauteur, depuis le bas
    "bold": True,
}

# Icônes vectorielles (viewBox 24x24) : [chemin plein, chemin trait]
_SPEAKER = "M3.5 9.5h3.5l5-4.5v14l-5-4.5H3.5z"
ICONS = {
    "play":    ["M8 5v14l11-7z", ""],
    "pause":   ["M6 5h4v14H6z M14 5h4v14h-4z", ""],
    "prev":    ["M6 5h2.5v14H6z M19 5v14L9.5 12z", ""],
    "next":    ["M15.5 5H18v14h-2.5z M5 5v14l9.5-7z", ""],
    "rew":     ["M11 6v12l-8.5-6z M21 6v12l-8.5-6z", ""],
    "fwd":     ["M3 6v12l8.5-6z M13 6v12l8.5-6z", ""],
    "vol":     [_SPEAKER, "M15.5 9a4 4 0 0 1 0 6 M18.5 6.2a8 8 0 0 1 0 11.6"],
    "vol_low": [_SPEAKER, "M15.5 9a4 4 0 0 1 0 6"],
    "vol_boost": [_SPEAKER, "M15.5 9a4 4 0 0 1 0 6 M18.5 6.2a8 8 0 0 1 0 11.6 M21.5 4a11 11 0 0 1 0 16"],
    "mute":    [_SPEAKER, "M16 9.5l5 5 M21 9.5l-5 5"],
    "full":    ["", "M4 9V4h5 M15 4h5v5 M20 15v5h-5 M9 20H4v-5"],
    "unfull":  ["", "M9 4v5H4 M20 9h-5V4 M15 20v-5h5 M4 15h5v5"],
    "list":    ["", "M9 6h11 M9 12h11 M9 18h7 M4.5 6h.01 M4.5 12h.01 M4.5 18h.01"],
    "subs":    ["", "M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z "
                    "M7 15h4 M14 15h3 M7 11h3 M13 11h4"],
    "camera":  ["", "M3.5 8.5a2 2 0 0 1 2-2h2l1.5-2.5h6l1.5 2.5h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-13"
                    "a2 2 0 0 1-2-2z M8.5 13a3.5 3.5 0 1 0 7 0a3.5 3.5 0 1 0-7 0"],
    "folder":  ["M3 6.5a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z", ""],
    "plus":    ["", "M12 5v14 M5 12h14"],
    "minus":   ["", "M5 12h14"],
    "close":   ["", "M6.5 6.5l11 11 M17.5 6.5l-11 11"],
    "check":   ["", "M5 12.5l4.5 4.5L19 7.5"],
    "trash":   ["", "M4 7h16 M10 11v6 M14 11v6 M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12 M9 7V4h6v3"],
    "film":    ["", "M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z "
                    "M8 4v16 M16 4v16 M4 9h4 M4 15h4 M16 9h4 M16 15h4"],
    "keys":    ["", "M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z "
                    "M7 10h.01 M11 10h.01 M15 10h.01 M8 14h8"],
    "clock":   ["", "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 7.5V12l3 2"],
    "brush":   ["", "M14.5 4.5l5 5L11 18H6v-5z M12 7l5 5"],
    "image":   ["", "M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z "
                    "M4 16l4.5-4.5 4 4 2.5-2.5 5 5 M15 8.5h.01"],
}


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def fmt_time(ms, sep=":"):
    s = max(0, int(ms // 1000))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}{sep}{m:02d}{sep}{s:02d}" if h else f"{m}{sep}{s:02d}"


# ---------------------------------------------------------------- sous-titres
_TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})\s*-->\s*(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})")
_ASS_TAG = re.compile(r"\{\\[^}]*\}")


def _ms(h, m, s, f):
    return ((int(h or 0) * 60 + int(m)) * 60 + int(s)) * 1000 + int(f.ljust(3, "0")[:3])


def to_styled(text):
    """Texte de sous-titre -> texte enrichi Qt (garde <i>, <b>, <u>, <font>)."""
    text = _ASS_TAG.sub("", text or "").strip()
    text = text.replace("&", "&amp;")
    text = re.sub(r"<(?!/?(i|b|u|font)\b)", "&lt;", text, flags=re.I)
    return text.replace("\r", "").replace("\n", "<br>")


def parse_subtitles(raw: bytes):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.split("\n")
        for i, line in enumerate(lines):
            m = _TS.search(line)
            if m:
                g = m.groups()
                start, end = _ms(*g[:4]), _ms(*g[4:])
                body = "\n".join(lines[i + 1:]).strip()
                if body and end > start:
                    cues.append((start, end, to_styled(body)))
                break
    cues.sort(key=lambda c: c[0])
    return cues


# ---------------------------------------------------------------- durées
class Prober(QObject):
    """Lit la durée des vidéos ajoutées, une par une, sans les lire (avec cache)."""
    durationReady = Signal(str, int)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._s = settings
        self._queue = deque()
        self._current = None
        self._p = QMediaPlayer(self)
        self._p.mediaStatusChanged.connect(self._on_status)
        self._p.durationChanged.connect(self._on_duration)
        self._timeout = QTimer(self, singleShot=True, interval=8000)
        self._timeout.timeout.connect(lambda: self._finish(-1))

    @staticmethod
    def _key(path):
        try:
            st = os.stat(path)
            sig = f"{path}|{st.st_size}|{int(st.st_mtime)}"
        except OSError:
            sig = path
        return "dur/" + hashlib.md5(sig.encode("utf-8")).hexdigest()

    def add(self, paths):
        for p in paths:
            cached = self._s.value(self._key(p))
            if cached is not None:
                try:
                    self.durationReady.emit(p, int(cached))
                    continue
                except (TypeError, ValueError):
                    pass
            self._queue.append(p)
        QTimer.singleShot(0, self._next)

    def _next(self):
        if self._current is not None:
            return
        if not self._queue:
            self._p.setSource(QUrl())   # libère le dernier fichier
            return
        self._current = self._queue.popleft()
        self._p.setSource(QUrl.fromLocalFile(self._current))
        self._timeout.start()

    def _on_status(self, st):
        if self._current is None:
            return
        if st in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia) and self._p.duration() > 0:
            self._finish(self._p.duration())
        elif st == QMediaPlayer.InvalidMedia:
            self._finish(-1)

    def _on_duration(self, d):
        if self._current is not None and d > 0:
            self._finish(d)

    def _finish(self, d):
        if self._current is None:
            return
        path, self._current = self._current, None
        self._timeout.stop()
        if d > 0:
            self._s.setValue(self._key(path), int(d))
        self.durationReady.emit(path, int(d))
        # ne jamais changer de fichier depuis un signal du moteur : on attend un peu
        QTimer.singleShot(30, self._next)


# ---------------------------------------------------------------- cœur
class Backend(QObject):
    recentsChanged = Signal()
    gainChanged = Signal()
    mutedChanged = Signal()
    subtitleTextChanged = Signal()
    subtitleSourceChanged = Signal()
    externalSubsChanged = Signal()
    subStyleChanged = Signal()
    subDelayChanged = Signal()
    postersChanged = Signal()
    durationReady = Signal(str, int)
    boostFailed = Signal()

    def __init__(self, initial_files):
        super().__init__()
        self._s = QSettings(APP_NAME, "NovaPlayer")
        self._initial = initial_files

        # lecteur
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self._relay = QVideoSink(self)          # reçoit les images du lecteur
        self.player.setVideoSink(self._relay)
        self._display = None                    # sink de l'affichage (VideoOutput)
        self._relay.videoFrameChanged.connect(self._on_frame)
        self._relay.subtitleTextChanged.connect(self._on_embedded_sub)
        self.player.positionChanged.connect(self._on_position)
        self.player.sourceChanged.connect(self._on_source)
        self.player.playbackStateChanged.connect(self._on_state)

        # volume / amplification
        try:
            saved = float(self._s.value("volume", 0.8))
        except (TypeError, ValueError):
            saved = 0.8
        self._gain = max(0.0, min(1.0, saved))   # jamais plus de 100 % au démarrage
        self._muted = False
        self._boost = None
        self._apply_volume()

        # sous-titres
        self._sub_text = ""
        self._sub_source = "embedded"     # embedded | external | off
        self._cues, self._starts = [], []
        self._ext_list = []
        self._ext_name = ""
        self._sub_delay = 0
        self._cue_idx = -1
        try:
            self._style = {**SUB_STYLE_DEFAULT, **json.loads(self._s.value("subStyle", "{}"))}
        except (TypeError, ValueError):
            self._style = dict(SUB_STYLE_DEFAULT)

        # durées
        self._prober = Prober(self._s, self)
        self._prober.durationReady.connect(self.durationReady)

        # affiches
        self._posters = []
        QTimer.singleShot(0, self._scan_posters)

    # ================================================================ vidéo
    @Slot(QObject)
    def setDisplaySink(self, sink):
        self._display = sink

    def _on_frame(self, frame):
        if self._display is None:
            return
        f = QVideoFrame(frame)
        if f.subtitleText():
            f.setSubtitleText("")   # on dessine nous-mêmes les sous-titres
        self._display.setVideoFrame(f)

    # ================================================================ fichiers
    @staticmethod
    def _to_path(u):
        if isinstance(u, QUrl):
            return u.toLocalFile() or u.toString()
        s = str(u)
        if s.startswith("file:"):
            return QUrl(s).toLocalFile()
        return s

    @Slot(list, result=list)
    def expandUrls(self, urls):
        out = []
        for u in urls:
            p = Path(self._to_path(u))
            try:
                if p.is_dir():
                    with os.scandir(p) as it:
                        files = [e.path for e in it
                                 if e.is_file() and os.path.splitext(e.name)[1].lower() in VIDEO_EXT]
                    files.sort(key=lambda f: natural_key(os.path.basename(f)))
                    out += files
                elif p.is_file():
                    out.append(str(p))
            except OSError:
                pass
        return out

    @Slot(list, result=list)
    def makeItems(self, paths):
        """Prépare d'un coup les éléments de la file (plus rapide qu'un par un)."""
        return [{"path": p, "name": Path(p).stem, "dur": -1} for p in paths]

    @Slot(list)
    def probeDurations(self, paths):
        self._prober.add(paths)

    @Slot(str, result=str)
    def toUrl(self, path):
        return QUrl.fromLocalFile(path).toString()

    @Slot(str, result=str)
    def displayName(self, path):
        return Path(path).stem

    def _get_initial(self):
        return self._initial

    initialFiles = Property("QVariantList", _get_initial, constant=True)

    # ================================================================ reprise
    @staticmethod
    def _key(path):
        return "resume/" + hashlib.md5(path.encode("utf-8")).hexdigest()

    @Slot(str, result=int)
    def getResume(self, path):
        try:
            return int(self._s.value(self._key(path), -1))
        except (TypeError, ValueError):
            return -1

    @Slot(str, int, int)
    def setResume(self, path, pos, dur):
        if not path:
            return
        if 10_000 < pos < dur - 15_000:
            self._s.setValue(self._key(path), int(pos))
        else:
            self._s.remove(self._key(path))

    @Slot(str)
    def clearResume(self, path):
        if path:
            self._s.remove(self._key(path))

    # ================================================================ récents
    def _raw_recents(self):
        r = self._s.value("recents", [])
        if isinstance(r, str):
            r = [r]
        return list(r or [])

    def _get_recents(self):
        return [p for p in self._raw_recents() if os.path.isfile(p)][:5]

    recents = Property("QVariantList", _get_recents, notify=recentsChanged)

    @Slot(str)
    def addRecent(self, path):
        r = [path] + [p for p in self._raw_recents() if p != path]
        self._s.setValue("recents", r[:12])
        self.recentsChanged.emit()

    # ================================================================ volume
    def _get_gain(self):
        return self._gain

    def _get_muted(self):
        return self._muted

    gain = Property(float, _get_gain, notify=gainChanged)
    muted = Property(bool, _get_muted, notify=mutedChanged)

    @Slot(float)
    def setGain(self, g):
        g = max(0.0, min(MAX_GAIN, round(float(g), 3)))
        if abs(g - self._gain) < 1e-4:
            return
        self._gain = g
        self._s.setValue("volume", g)
        self._apply_volume()
        self.gainChanged.emit()

    @Slot(bool)
    def setMuted(self, m):
        self._muted = bool(m)
        self._apply_volume()
        self.mutedChanged.emit()

    def _apply_volume(self):
        if self._gain > 1.0001 and not self._muted:
            if self._boost is None and not self._start_boost():
                self._gain = 1.0
                self.audio.setVolume(1.0)
                self.audio.setMuted(False)
                QTimer.singleShot(0, self.gainChanged.emit)
                QTimer.singleShot(0, self.boostFailed.emit)
                return
            self.audio.setVolume(0.0)      # le son passe par l'amplificateur
            self.audio.setMuted(False)
        else:
            self._stop_boost()
            self.audio.setVolume(min(1.0, self._gain))
            self.audio.setMuted(self._muted)

    # --- amplificateur (au-delà de 100 %)
    def _start_boost(self):
        try:
            fmt = QAudioFormat()
            fmt.setSampleRate(48000)
            fmt.setChannelCount(2)
            fmt.setSampleFormat(QAudioFormat.Int16)
            dev = QMediaDevices.defaultAudioOutput()
            if dev.isNull():
                return False
            sink = QAudioSink(dev, fmt, self)
            sink.setBufferSize(int(48000 * 4 * 0.15))   # ~150 ms
            io = sink.start()
            if io is None or sink.error() != QAudio.NoError:
                sink.deleteLater()
                return False
            out = QAudioBufferOutput(fmt, self)
            out.audioBufferReceived.connect(self._on_audio_buffer)
            self.player.setAudioBufferOutput(out)
            self._boost = {"sink": sink, "io": io, "out": out, "pending": bytearray(), "primed": False}
            sink.stateChanged.connect(self._on_boost_state)
            if self.player.playbackState() != QMediaPlayer.PlayingState:
                sink.suspend()
            return True
        except Exception as e:  # noqa: BLE001
            print("Amplification indisponible :", e, file=sys.stderr)
            return False

    def _stop_boost(self):
        b, self._boost = self._boost, None
        if not b:
            return
        try:
            self.player.setAudioBufferOutput(None)
        except Exception:  # noqa: BLE001
            pass
        try:
            b["out"].audioBufferReceived.disconnect(self._on_audio_buffer)
        except Exception:  # noqa: BLE001
            pass
        b["sink"].stop()
        b["sink"].deleteLater()
        b["out"].deleteLater()

    def _on_boost_state(self, state):
        b = self._boost
        if b and state == QAudio.StoppedState and b["sink"].error() not in (QAudio.NoError, QAudio.UnderrunError):
            self._stop_boost()
            self._gain = 1.0
            self._apply_volume()
            self.gainChanged.emit()
            self.boostFailed.emit()

    def _on_audio_buffer(self, buf):
        b = self._boost
        if b is None:
            return
        raw = buf.constData()
        try:
            data = bytes(raw)
        except TypeError:
            data = raw.tobytes() if hasattr(raw, "tobytes") else b""
        data = data[: buf.byteCount()]
        if not data:
            return
        g = self._gain
        samples = array("h")
        samples.frombytes(data[: len(data) - len(data) % 2])
        hi, lo = 32767, -32768
        samples = array("h", [hi if v > hi else lo if v < lo else v
                              for v in [int(x * g) for x in samples]])
        pend = b["pending"]
        pend += samples.tobytes()
        max_pending = 48000 * 4 // 3            # ~330 ms au maximum
        if len(pend) > max_pending:
            del pend[: len(pend) - max_pending]
        if not b["primed"]:
            if len(pend) < 48000 * 4 // 25:     # on attend ~40 ms avant de démarrer
                return
            b["primed"] = True
        free = b["sink"].bytesFree()
        if free > 0 and pend:
            n = min(free, len(pend))
            n -= n % 4
            if n:
                b["io"].write(bytes(pend[:n]))
                del pend[:n]

    @Slot()
    def flushAudio(self):
        """Après un saut dans la vidéo : vide le son en attente."""
        b = self._boost
        if not b:
            return
        b["pending"].clear()
        b["primed"] = False
        b["sink"].reset()
        b["io"] = b["sink"].start()
        if self.player.playbackState() != QMediaPlayer.PlayingState:
            b["sink"].suspend()

    def _on_state(self, state):
        b = self._boost
        if not b:
            return
        if state == QMediaPlayer.PlayingState:
            b["sink"].resume()
        elif state == QMediaPlayer.PausedState:
            b["sink"].suspend()
        else:
            self.flushAudio()

    # ================================================================ sous-titres
    def _set_sub(self, text):
        if text != self._sub_text:
            self._sub_text = text
            self.subtitleTextChanged.emit()

    def _on_embedded_sub(self, text):
        if self._sub_source == "embedded":
            self._set_sub(to_styled(text))

    def _on_position(self, pos):
        if self._sub_source != "external" or not self._cues:
            return
        t = pos - self._sub_delay
        i = bisect.bisect_right(self._starts, t) - 1
        if i >= 0 and t < self._cues[i][1]:
            if i != self._cue_idx:
                self._cue_idx = i
                self._set_sub(self._cues[i][2])
        elif self._cue_idx != -1:
            self._cue_idx = -1
            self._set_sub("")

    def _on_source(self, url):
        self._cues, self._starts, self._cue_idx = [], [], -1
        self._ext_name = ""
        self._sub_source = "embedded"
        self._set_sub("")
        self._ext_list = []
        path = url.toLocalFile() if isinstance(url, QUrl) else ""
        if path:
            folder, stem = os.path.dirname(path), Path(path).stem.lower()
            try:
                with os.scandir(folder) as it:
                    subs = [e.path for e in it if e.is_file()
                            and os.path.splitext(e.name)[1].lower() in SUB_EXT
                            and e.name.lower().startswith(stem)]
                subs.sort(key=lambda f: natural_key(os.path.basename(f)))
                self._ext_list = subs
            except OSError:
                pass
        self.externalSubsChanged.emit()
        self.subtitleSourceChanged.emit()
        if self._ext_list:
            # un .srt du même nom est chargé automatiquement
            QTimer.singleShot(0, lambda: self.loadExternal(self._ext_list[0]))

    def _get_sub_text(self):
        return self._sub_text

    def _get_sub_source(self):
        return self._sub_source

    def _get_ext_list(self):
        return [{"path": p, "name": os.path.basename(p)} for p in self._ext_list]

    def _get_ext_name(self):
        return self._ext_name

    subtitleText = Property(str, _get_sub_text, notify=subtitleTextChanged)
    subtitleSource = Property(str, _get_sub_source, notify=subtitleSourceChanged)
    externalSubs = Property("QVariantList", _get_ext_list, notify=externalSubsChanged)
    externalName = Property(str, _get_ext_name, notify=subtitleSourceChanged)

    @Slot(str, result=bool)
    def loadExternal(self, path):
        path = self._to_path(path)
        try:
            cues = parse_subtitles(Path(path).read_bytes())
        except OSError:
            cues = []
        if not cues:
            return False
        self._cues = cues
        self._starts = [c[0] for c in cues]
        self._cue_idx = -1
        self._ext_name = os.path.basename(path)
        if path not in self._ext_list:
            self._ext_list.append(path)
            self.externalSubsChanged.emit()
        self._sub_source = "external"
        self.player.setActiveSubtitleTrack(-1)
        self._set_sub("")
        self._on_position(self.player.position())
        self.subtitleSourceChanged.emit()
        return True

    @Slot(int)
    def useEmbedded(self, index):
        self._sub_source = "embedded" if index >= 0 else "off"
        self._cue_idx = -1
        self._set_sub("")
        self.player.setActiveSubtitleTrack(index)
        self.subtitleSourceChanged.emit()

    def _get_delay(self):
        return self._sub_delay

    subDelay = Property(int, _get_delay, notify=subDelayChanged)

    @Slot(int)
    def setSubDelay(self, ms):
        self._sub_delay = int(ms)
        self._cue_idx = -1
        self._on_position(self.player.position())
        self.subDelayChanged.emit()

    def _get_style(self):
        return self._style

    subStyle = Property("QVariantMap", _get_style, notify=subStyleChanged)

    @Slot(str, "QVariant")
    def setSubStyle(self, key, value):
        self._style = {**self._style, key: value}
        self._s.setValue("subStyle", json.dumps(self._style))
        self.subStyleChanged.emit()

    @Slot()
    def resetSubStyle(self):
        self._style = dict(SUB_STYLE_DEFAULT)
        self._s.setValue("subStyle", json.dumps(self._style))
        self.subStyleChanged.emit()

    # ================================================================ affiches
    def _poster_dir(self):
        d = self._s.value("posterDir", "")
        if not d:
            d = str(Path(QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)) / APP_NAME / "Affiches")
            try:
                Path(d).mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        return d

    def _scan_posters(self):
        files = []
        try:
            for root, _dirs, names in os.walk(self._poster_dir()):
                for n in names:
                    if os.path.splitext(n)[1].lower() in IMG_EXT:
                        files.append(os.path.join(root, n))
                if len(files) > 400:
                    break
        except OSError:
            pass
        random.shuffle(files)
        self._posters = [QUrl.fromLocalFile(f).toString() for f in files[:120]]
        self.postersChanged.emit()

    def _get_posters(self):
        return self._posters

    posters = Property("QVariantList", _get_posters, notify=postersChanged)

    @Slot("QVariant")
    def setPosterDir(self, url):
        self._s.setValue("posterDir", self._to_path(url))
        self._scan_posters()

    @Slot()
    def openPosterDir(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._poster_dir()))

    @Slot(result=str)
    def posterDirName(self):
        return self._poster_dir()

    # ================================================================ capture
    @Slot(str, int, result=str)
    def screenshot(self, name, pos):
        try:
            frame = self._relay.videoFrame()
            if not frame.isValid():
                return ""
            img = frame.toImage()
            if img.isNull():
                return ""
            folder = Path(QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)) / APP_NAME
            folder.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r'[\\/:*?"<>|]', "_", name)[:80] or "capture"
            base = f"{safe}_{fmt_time(pos, '-')}"
            f = folder / f"{base}.png"
            i = 2
            while f.exists():
                f = folder / f"{base}_{i}.png"
                i += 1
            return str(f) if img.save(str(f)) else ""
        except Exception as e:  # noqa: BLE001
            print("Capture impossible :", e, file=sys.stderr)
            return ""

    def shutdown(self):
        self._stop_boost()


def make_app_icon():
    size = 256
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor(THEME["accent"]))
    g.setColorAt(1, QColor(THEME["accent2"]))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(QRectF(8, 8, size - 16, size - 16), 64, 64)
    tri = QPainterPath(QPointF(100, 74))
    tri.lineTo(100, 182)
    tri.lineTo(186, 128)
    tri.closeSubpath()
    p.setBrush(QColor("white"))
    p.drawPath(tri)
    p.end()
    return QIcon(pm)


def dark_titlebar(window):
    """Barre de titre sombre sous Windows 10/11."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(window.winId())
        value = ctypes.c_int(1)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:  # noqa: BLE001
        pass


QML = r"""
import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Shapes
import QtQuick.Dialogs
import QtMultimedia

ApplicationWindow {
    id: win
    width: 1280; height: 760
    minimumWidth: 800; minimumHeight: 480
    visible: true
    color: theme.bg
    title: hasMedia ? currentName + "  —  Nova" : "Nova"

    // ------------------------------------------------------------ état
    property int currentIndex: -1
    property string currentPath: ""
    property string currentName: ""
    property bool hasMedia: currentIndex >= 0
    property bool controlsVisible: true
    property bool playlistOpen: true
    property bool isFull: win.visibility === Window.FullScreen
    property bool wasMaximized: false
    property bool playing: player.playbackState === MediaPlayer.PlayingState
    property int pendingResume: -1
    property bool menuOpen: speedPop.opened || trackPop.opened || helpPop.opened || subPop.opened
    property bool showBars: hasMedia && (controlsVisible || !playing)
    property int durTick: 0
    readonly property var speeds: [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 3]
    readonly property var subColors: ["#FFFFFF", "#FFE45C", "#7DF9FF", "#9CFF8A", "#FF9BD2", "#C9B8FF"]

    // ------------------------------------------------------------ composants
    component Icon: Item {
        id: ic
        property string name: ""
        property color color: theme.text
        property real strokeW: 2
        readonly property var paths: icons[name] || ["", ""]
        implicitWidth: 24; implicitHeight: 24
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                scale: Qt.size(ic.width / 24, ic.height / 24)
                fillColor: ic.paths[0] !== "" ? ic.color : "transparent"
                strokeColor: ic.paths[0] !== "" ? ic.color : "transparent"
                strokeWidth: 1.5
                joinStyle: ShapePath.RoundJoin
                capStyle: ShapePath.RoundCap
                PathSvg { path: ic.paths[0] }
            }
            ShapePath {
                scale: Qt.size(ic.width / 24, ic.height / 24)
                fillColor: "transparent"
                strokeColor: ic.paths[1] !== "" ? ic.color : "transparent"
                strokeWidth: ic.strokeW
                joinStyle: ShapePath.RoundJoin
                capStyle: ShapePath.RoundCap
                PathSvg { path: ic.paths[1] }
            }
        }
    }

    component IconBtn: Item {
        id: b
        property string icon: ""
        property int size: 40
        property int iconSize: 22
        property string tip: ""
        property bool tipBelow: false
        property bool active: false
        property color tint: theme.text
        property bool showTip: false
        signal clicked()
        width: size; height: size
        z: ma.containsMouse ? 10 : 0
        Rectangle {
            anchors.fill: parent; radius: width / 2
            color: ma.pressed ? Qt.rgba(1, 1, 1, 0.18) : (ma.containsMouse ? Qt.rgba(1, 1, 1, 0.10) : "transparent")
            Behavior on color { ColorAnimation { duration: 120 } }
        }
        Icon {
            anchors.centerIn: parent
            width: b.iconSize; height: b.iconSize
            name: b.icon
            color: b.active ? theme.accent : b.tint
        }
        MouseArea {
            id: ma
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: { b.showTip = false; b.clicked() }
            onContainsMouseChanged: if (!containsMouse) b.showTip = false
        }
        Timer { interval: 550; running: ma.containsMouse && !b.showTip && b.tip !== ""; onTriggered: b.showTip = true }
        Rectangle {
            visible: b.showTip
            x: (b.width - width) / 2
            y: b.tipBelow ? b.height + 6 : -height - 6
            width: tipText.implicitWidth + 16; height: tipText.implicitHeight + 10
            radius: 7; color: theme.panel2; border.color: Qt.rgba(1, 1, 1, 0.08)
            Text { id: tipText; anchors.centerIn: parent; text: b.tip; color: theme.text; font.pixelSize: 12 }
        }
    }

    component TextBtn: Rectangle {
        id: tb
        property string text: ""
        property string icon: ""
        property bool primary: false
        property bool small: false
        signal clicked()
        height: small ? 36 : 46; radius: small ? 10 : 13
        width: tbRow.implicitWidth + (small ? 26 : 40)
        color: primary ? "transparent" : (tma.containsMouse ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(1, 1, 1, 0.06))
        border.color: primary ? "transparent" : Qt.rgba(1, 1, 1, 0.09)
        gradient: primary ? tbGrad : null
        scale: tma.pressed ? 0.97 : 1
        Behavior on scale { NumberAnimation { duration: 100 } }
        Gradient {
            id: tbGrad
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: theme.accent }
            GradientStop { position: 1; color: theme.accent2 }
        }
        Rectangle { anchors.fill: parent; radius: parent.radius; color: "white"; opacity: (tb.primary && tma.containsMouse) ? 0.08 : 0 }
        Row {
            id: tbRow
            anchors.centerIn: parent
            spacing: 8
            Icon { visible: tb.icon !== ""; name: tb.icon; width: tb.small ? 16 : 18; height: width; color: "white"; anchors.verticalCenter: parent.verticalCenter }
            Text { text: tb.text; color: "white"; font.pixelSize: tb.small ? 13 : 14; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
        }
        MouseArea { id: tma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: tb.clicked() }
    }

    component MenuRow: Rectangle {
        id: mr
        property string text: ""
        property bool checked: false
        property string icon: ""
        signal clicked()
        width: 250; height: 34; radius: 8
        color: mra.containsMouse ? Qt.rgba(0.545, 0.36, 0.965, 0.25) : "transparent"
        Icon {
            id: mrIcon; visible: mr.icon !== ""; name: mr.icon
            width: 16; height: 16; color: theme.muted
            anchors.left: parent.left; anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            anchors.left: mr.icon !== "" ? mrIcon.right : parent.left
            anchors.leftMargin: mr.icon !== "" ? 10 : 12
            anchors.right: chk.left; anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            text: mr.text; color: theme.text; font.pixelSize: 13; elide: Text.ElideRight
        }
        Icon {
            id: chk; name: "check"; visible: mr.checked
            width: 16; height: 16; color: theme.accent
            anchors.right: parent.right; anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
        }
        MouseArea { id: mra; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: mr.clicked() }
    }

    component MenuHeader: Text {
        color: theme.muted; font.pixelSize: 11; font.letterSpacing: 1.3; font.weight: Font.DemiBold
        leftPadding: 12; topPadding: 8; bottomPadding: 6
    }

    component MenuSep: Item {
        width: 250; height: 9
        Rectangle { anchors.centerIn: parent; width: parent.width - 16; height: 1; color: Qt.rgba(1, 1, 1, 0.07) }
    }

    component DarkPopup: Popup {
        padding: 6
        margins: 8
        background: Rectangle { color: theme.panel2; radius: 12; border.color: Qt.rgba(1, 1, 1, 0.08) }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 } }
        exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 } }
    }

    component NiceSlider: Slider {
        id: ns
        property color fill: theme.accent
        focusPolicy: Qt.NoFocus
        height: 28
        background: Item {
            x: ns.leftPadding
            y: ns.topPadding + ns.availableHeight / 2 - 2
            width: ns.availableWidth; height: 4
            Rectangle { anchors.fill: parent; radius: 2; color: Qt.rgba(1, 1, 1, 0.15) }
            Rectangle { width: ns.visualPosition * parent.width; height: 4; radius: 2; color: ns.fill }
        }
        handle: Rectangle {
            x: ns.leftPadding + ns.visualPosition * ns.availableWidth - 7
            y: ns.topPadding + ns.availableHeight / 2 - 7
            width: 14; height: 14; radius: 7; color: "white"
        }
    }

    component Chip: Rectangle {
        id: chip
        property string text: ""
        property bool selected: false
        signal clicked()
        height: 32; radius: 9
        width: chipText.implicitWidth + 26
        color: selected ? Qt.rgba(0.545, 0.36, 0.965, 0.35) : (chma.containsMouse ? Qt.rgba(1, 1, 1, 0.1) : Qt.rgba(1, 1, 1, 0.05))
        border.color: selected ? theme.accent : Qt.rgba(1, 1, 1, 0.08)
        Text { id: chipText; anchors.centerIn: parent; text: chip.text; color: theme.text; font.pixelSize: 13; font.weight: chip.selected ? Font.DemiBold : Font.Normal }
        MouseArea { id: chma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: chip.clicked() }
    }

    component SubtitleText: Item {
        id: st
        property string text: ""
        property real baseSize: 24
        readonly property var s: backend.subStyle
        implicitHeight: label.contentHeight + (s.style === "box" ? 12 : 0)
        Rectangle {
            visible: st.s.style === "box" && label.text !== ""
            anchors.centerIn: label
            width: label.contentWidth + 26; height: label.contentHeight + 12
            radius: 6
            color: Qt.rgba(0, 0, 0, st.s.boxOpacity)
        }
        Text {
            visible: st.s.style === "shadow"
            x: label.x + 2; y: label.y + 2
            width: label.width
            text: label.text; textFormat: Text.StyledText
            horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
            font: label.font; color: "#D0000000"
        }
        Text {
            id: label
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: st.s.style === "box" ? 6 : 0
            width: parent.width
            text: st.text
            textFormat: Text.StyledText
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: st.s.color
            font.pixelSize: Math.max(12, st.baseSize * st.s.size / 100)
            font.weight: st.s.bold ? Font.Bold : Font.Medium
            style: st.s.style === "outline" ? Text.Outline : Text.Normal
            styleColor: "black"
        }
    }

    component PosterCard: Rectangle {
        id: pc
        property int idx: 0
        readonly property var list: backend.posters
        readonly property var titles: ["MINUIT", "L'ÉCHO", "HORIZON", "NÉON", "LE DERNIER HIVER", "SABLE", "ORBITE", "VERTIGE", "LES OMBRES", "MIRAGE", "TEMPÊTE", "AURORE", "ÉCLIPSE", "LA FAILLE", "SILENCE", "FRONTIÈRE"]
        readonly property real hue: (idx * 0.137) % 1
        width: 150; height: 225; radius: 8
        clip: true
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.hsla(pc.hue, 0.55, 0.42, 1) }
            GradientStop { position: 1; color: Qt.hsla((pc.hue + 0.12) % 1, 0.6, 0.12, 1) }
        }
        // affiche générée (quand aucune image n'est fournie)
        Item {
            anchors.fill: parent
            visible: pc.list.length === 0
            Rectangle {
                width: pc.width * (0.55 + (pc.idx % 4) * 0.1); height: width; radius: width / 2
                x: pc.width * ((pc.idx * 37) % 60) / 100 - width / 3
                y: pc.height * (0.12 + (pc.idx % 5) * 0.06)
                color: Qt.hsla((pc.hue + 0.5) % 1, 0.7, 0.6, 0.35)
            }
            Rectangle { x: 12; width: pc.width - 24; height: 1; y: pc.height - 52; color: Qt.rgba(1, 1, 1, 0.35) }
            Text {
                x: 12; width: pc.width - 24; y: pc.height - 44
                text: pc.titles[pc.idx % pc.titles.length]
                color: "white"; font.pixelSize: 15; font.weight: Font.Black; font.letterSpacing: 1.5
                wrapMode: Text.WordWrap
            }
        }
        Image {
            anchors.fill: parent
            visible: pc.list.length > 0
            source: pc.list.length > 0 ? pc.list[pc.idx % pc.list.length] : ""
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            cache: true
            sourceSize: Qt.size(300, 450)
        }
    }

    // ------------------------------------------------------------ logique
    function fmt(ms) {
        if (!ms || ms < 0) ms = 0
        var s = Math.floor(ms / 1000)
        var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
        s = s % 60
        function p(n) { return n < 10 ? "0" + n : "" + n }
        return h > 0 ? h + ":" + p(m) + ":" + p(s) : m + ":" + p(s)
    }
    function fmtLong(ms) {
        var mins = Math.round(ms / 60000)
        if (mins < 1) return Math.round(ms / 1000) + " s"
        var h = Math.floor(mins / 60), m = mins % 60
        if (h === 0) return m + " min"
        return h + " h " + (m < 10 ? "0" + m : m)
    }
    function clock(ms) {
        var d = new Date(Date.now() + ms)
        var h = d.getHours(), m = d.getMinutes()
        return h + ":" + (m < 10 ? "0" + m : m)
    }
    function queueStats() {
        void durTick
        var total = 0, unknown = 0, after = 0
        for (var i = 0; i < queue.count; i++) {
            var d = queue.get(i).dur
            if (d > 0) { total += d; if (i > currentIndex) after += d } else unknown++
        }
        var curDur = (currentIndex >= 0 && currentIndex < queue.count) ? queue.get(currentIndex).dur : -1
        if (player.duration > 0) curDur = player.duration
        var remaining = after + (curDur > 0 ? Math.max(0, curDur - player.position) : 0)
        return { total: total, unknown: unknown, remaining: remaining }
    }
    function poke() { controlsVisible = true; hideTimer.restart() }
    function togglePlay() {
        if (!hasMedia) { openDlg.open(); return }
        if (playing) { player.pause(); flash.show("pause") }
        else { player.play(); flash.show("play") }
        poke()
    }
    function seekTo(ms) {
        player.setPosition(Math.max(0, Math.min(player.duration, ms)))
        backend.flushAudio()
    }
    function seekBy(ms) {
        if (!hasMedia) return
        seekTo(player.position + ms)
        flash.show(ms > 0 ? "fwd" : "rew")
        toast.show((ms > 0 ? "+" : "−") + Math.abs(ms / 1000) + " s")
        poke()
    }
    function volumeText() {
        var p = Math.round(backend.gain * 100)
        return "Volume " + p + " %" + (p > 100 ? "  ·  amplifié" : "")
    }
    function changeVolume(d) {
        if (backend.muted) backend.setMuted(false)
        var g = Math.round((backend.gain + d) * 100) / 100
        // petit arrêt à 100 % avant d'entrer dans l'amplification
        if (d > 0 && backend.gain < 1 && g > 1) g = 1
        backend.setGain(Math.max(0, Math.min(3, g)))
        toast.show(volumeText())
    }
    function toggleMute() {
        backend.setMuted(!backend.muted)
        toast.show(backend.muted ? "Son coupé" : "Son activé")
    }
    function toggleFull() {
        if (isFull) { if (wasMaximized) win.showMaximized(); else win.showNormal() }
        else { wasMaximized = (win.visibility === Window.Maximized); win.showFullScreen() }
    }
    function rateText(r) { return String(Math.round(r * 100) / 100).replace(".", ",") + "×" }
    function setSpeed(r) { player.playbackRate = r; toast.show("Vitesse " + rateText(r)) }
    function speedStep(dir) {
        var best = 0
        for (var i = 0; i < speeds.length; i++)
            if (Math.abs(speeds[i] - player.playbackRate) < Math.abs(speeds[best] - player.playbackRate)) best = i
        setSpeed(speeds[Math.max(0, Math.min(speeds.length - 1, best + dir))])
    }
    function frameStep(dir) {
        if (!hasMedia) return
        if (playing) player.pause()
        var fps = Number(player.metaData.value(MediaMetaData.VideoFrameRate)) || 30
        seekTo(player.position + dir * 1000 / fps)
        poke()
    }
    function addFiles(paths, playFirst) {
        if (!paths || paths.length === 0) { toast.show("Aucune vidéo trouvée"); return }
        var start = queue.count
        var items = []
        for (var i = 0; i < paths.length; i++) {
            var p = String(paths[i])
            items.push({ path: p, name: p.split(/[\\/]/).pop().replace(/\.[^.]+$/, ""), dur: -1 })
        }
        queue.append(items)
        backend.probeDurations(paths)
        if (playFirst) playIndex(start)
        else toast.show(paths.length + (paths.length > 1 ? " vidéos ajoutées" : " vidéo ajoutée"))
    }
    function playIndex(i) {
        if (i < 0 || i >= queue.count) return
        saveResume()
        var it = queue.get(i)
        currentIndex = i
        currentPath = it.path
        currentName = it.name
        pendingResume = backend.getResume(it.path)
        player.source = backend.toUrl(it.path)
        player.play()
        backend.addRecent(it.path)
        poke()
    }
    function playNext() { if (currentIndex + 1 < queue.count) playIndex(currentIndex + 1) }
    function playPrev() {
        if (player.position > 4000 || currentIndex <= 0) seekTo(0)
        else playIndex(currentIndex - 1)
    }
    function saveResume() {
        if (currentPath !== "" && player.duration > 0)
            backend.setResume(currentPath, player.position, player.duration)
    }
    function resetPlayer() {
        player.stop(); player.source = ""
        currentIndex = -1; currentPath = ""; currentName = ""
    }
    function removeAt(i) {
        if (i === currentIndex) {
            saveResume()
            player.stop()
            currentPath = ""
            queue.remove(i)
            if (queue.count === 0) resetPlayer()
            else { currentIndex = -1; playIndex(Math.min(i, queue.count - 1)) }
        } else {
            queue.remove(i)
            if (i < currentIndex) currentIndex--
        }
        durTick++
    }
    function clearQueue() { saveResume(); resetPlayer(); queue.clear(); durTick++ }
    function screenshot() {
        if (!hasMedia) return
        var p = backend.screenshot(currentName, player.position)
        if (p !== "") { flash.show("camera"); toast.show("Capture enregistrée dans Images/Nova") }
        else toast.show("Capture impossible")
    }
    function trackName(md, i) {
        var t = md.stringValue(MediaMetaData.Title)
        var l = md.stringValue(MediaMetaData.Language)
        var parts = []
        if (t) parts.push(t)
        if (l && l !== t) parts.push(l)
        return parts.length ? parts.join(" · ") : "Piste " + (i + 1)
    }
    function infoLine() {
        var parts = []
        if (queue.count > 1) parts.push("Vidéo " + (currentIndex + 1) + " sur " + queue.count)
        var res = player.metaData.value(MediaMetaData.Resolution)
        if (res && res.width > 0) parts.push(res.width + " × " + res.height)
        return parts.join("   ·   ")
    }
    function delayText(ms) { return (ms > 0 ? "+" : ms < 0 ? "−" : "") + (Math.abs(ms) / 1000).toFixed(1).replace(".", ",") + " s" }

    // ------------------------------------------------------------ média
    ListModel { id: queue }

    Connections {
        target: player
        function onMediaStatusChanged() {
            var st = player.mediaStatus
            if ((st === MediaPlayer.LoadedMedia || st === MediaPlayer.BufferedMedia) && win.pendingResume > 0) {
                var r = win.pendingResume
                win.pendingResume = -1
                if (r < player.duration - 15000) {
                    win.seekTo(r)
                    toast.show("Reprise à " + win.fmt(r))
                }
            } else if (st === MediaPlayer.EndOfMedia) {
                backend.clearResume(win.currentPath)
                if (win.currentIndex + 1 < queue.count) win.playNext()
                else win.poke()
            }
        }
        function onErrorOccurred(error, errorString) { toast.show("Lecture impossible : " + errorString) }
        function onPlaybackStateChanged() {
            if (!win.playing) win.controlsVisible = true
            else hideTimer.restart()
        }
        function onDurationChanged() {
            if (win.currentIndex >= 0 && player.duration > 0 && queue.get(win.currentIndex).dur <= 0) {
                queue.setProperty(win.currentIndex, "dur", player.duration)
                win.durTick++
            }
        }
    }
    Connections {
        target: backend
        function onDurationReady(path, ms) {
            for (var i = 0; i < queue.count; i++)
                if (queue.get(i).path === path && queue.get(i).dur <= 0) queue.setProperty(i, "dur", ms)
            win.durTick++
        }
        function onBoostFailed() { toast.show("Amplification indisponible sur cet appareil", 3000) }
    }

    Timer {
        id: hideTimer
        interval: 2600
        onTriggered: {
            var overBar = stageHover.hovered && stageHover.point.position.y > stage.height - bottomBar.height - 12
            if (win.playing && !barHover.hovered && !overBar && !win.menuOpen) win.controlsVisible = false
            else restart()
        }
    }
    Timer { interval: 5000; repeat: true; running: win.playing; onTriggered: win.saveResume() }
    onClosing: saveResume()

    FileDialog {
        id: openDlg
        title: "Ouvrir des vidéos"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Vidéos (*.mp4 *.mkv *.avi *.mov *.webm *.m4v *.wmv *.flv *.ts *.m2ts *.mts *.mpg *.mpeg *.3gp *.ogv *.vob)", "Tous les fichiers (*)"]
        onAccepted: win.addFiles(backend.expandUrls(selectedFiles), true)
    }
    FolderDialog {
        id: folderDlg
        title: "Ouvrir un dossier"
        onAccepted: win.addFiles(backend.expandUrls([selectedFolder]), true)
    }
    FileDialog {
        id: subDlg
        title: "Charger des sous-titres"
        nameFilters: ["Sous-titres (*.srt *.vtt)", "Tous les fichiers (*)"]
        onAccepted: {
            if (backend.loadExternal(selectedFile)) toast.show("Sous-titres chargés")
            else toast.show("Fichier de sous-titres illisible")
        }
    }
    FolderDialog {
        id: posterDlg
        title: "Choisir le dossier de tes affiches"
        onAccepted: { backend.setPosterDir(selectedFolder); toast.show("Affiches mises à jour") }
    }

    // ------------------------------------------------------------ raccourcis
    Shortcut { sequences: ["Space", "K"]; onActivated: win.togglePlay() }
    Shortcut { sequence: "Left"; onActivated: win.seekBy(-5000) }
    Shortcut { sequence: "Right"; onActivated: win.seekBy(5000) }
    Shortcut { sequence: "J"; onActivated: win.seekBy(-10000) }
    Shortcut { sequence: "L"; onActivated: win.seekBy(10000) }
    Shortcut { sequence: "Up"; onActivated: win.changeVolume(0.05) }
    Shortcut { sequence: "Down"; onActivated: win.changeVolume(-0.05) }
    Shortcut { sequence: "M"; onActivated: win.toggleMute() }
    Shortcut { sequence: "F"; onActivated: win.toggleFull() }
    Shortcut { sequence: "Escape"; enabled: win.isFull; onActivated: win.toggleFull() }
    Shortcut { sequences: [",", "Ctrl+Left"]; onActivated: win.frameStep(-1) }
    Shortcut { sequences: [";", ".", "Ctrl+Right"]; onActivated: win.frameStep(1) }
    Shortcut { sequences: ["-", "Ctrl+Down"]; onActivated: win.speedStep(-1) }
    Shortcut { sequences: ["+", "=", "Ctrl+Up"]; onActivated: win.speedStep(1) }
    Shortcut { sequence: "S"; onActivated: win.screenshot() }
    Shortcut { sequence: "P"; onActivated: win.playlistOpen = !win.playlistOpen }
    Shortcut { sequence: "N"; onActivated: win.playNext() }
    Shortcut { sequence: "B"; onActivated: win.playPrev() }
    Shortcut { sequence: "C"; onActivated: subPop.opened ? subPop.close() : subPop.open() }
    Shortcut { sequence: "G"; onActivated: { backend.setSubDelay(backend.subDelay - 100); toast.show("Décalage sous-titres " + win.delayText(backend.subDelay)) } }
    Shortcut { sequence: "H"; onActivated: helpPop.opened ? helpPop.close() : helpPop.open() }
    Shortcut { sequence: "Ctrl+O"; onActivated: openDlg.open() }

    // ------------------------------------------------------------ interface
    Item {
        id: root
        anchors.fill: parent

        // ---------- file d'attente ----------
        Rectangle {
            id: panel
            anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.right: parent.right
            width: (win.playlistOpen && !win.isFull && win.hasMedia) ? 330 : 0
            Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
            clip: true
            color: theme.panel
            Rectangle { width: 1; anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; color: Qt.rgba(1, 1, 1, 0.06) }

            Item {
                width: 330
                anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.left: parent.left

                Item {
                    id: plHeader
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    height: 68
                    Column {
                        anchors.left: parent.left; anchors.leftMargin: 20
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Text { text: "File d'attente"; color: theme.text; font.pixelSize: 16; font.weight: Font.DemiBold }
                        Text { text: queue.count + (queue.count > 1 ? " vidéos" : " vidéo"); color: theme.muted; font.pixelSize: 12 }
                    }
                    Row {
                        anchors.right: parent.right; anchors.rightMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        IconBtn { icon: "plus"; size: 34; iconSize: 18; tip: "Ajouter"; tipBelow: true; onClicked: openDlg.open() }
                        IconBtn { icon: "trash"; size: 34; iconSize: 18; tip: "Vider"; tipBelow: true; onClicked: win.clearQueue() }
                    }
                }

                // compteur de durée
                Rectangle {
                    id: durCard
                    anchors.top: plHeader.bottom
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.leftMargin: 14; anchors.rightMargin: 14
                    height: 74; radius: 12
                    property var stats: win.queueStats()
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: Qt.rgba(0.545, 0.36, 0.965, 0.22) }
                        GradientStop { position: 1; color: Qt.rgba(0.925, 0.28, 0.6, 0.14) }
                    }
                    border.color: Qt.rgba(1, 1, 1, 0.07)
                    Icon { id: clockIcon; name: "clock"; width: 22; height: 22; color: "white"; anchors.left: parent.left; anchors.leftMargin: 16; anchors.verticalCenter: parent.verticalCenter }
                    Column {
                        anchors.left: clockIcon.right; anchors.leftMargin: 14
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3
                        Text {
                            text: (durCard.stats.total > 0 ? win.fmtLong(durCard.stats.total) : "…") + (durCard.stats.unknown > 0 && durCard.stats.total > 0 ? " +" : "")
                            color: "white"; font.pixelSize: 20; font.weight: Font.Bold
                        }
                        Text {
                            text: durCard.stats.remaining > 0
                                  ? "Reste " + win.fmtLong(durCard.stats.remaining) + "  ·  fin vers " + win.clock(durCard.stats.remaining / Math.max(0.25, player.playbackRate))
                                  : "Durée totale de la file"
                            color: Qt.rgba(1, 1, 1, 0.7); font.pixelSize: 12
                        }
                    }
                }

                ListView {
                    id: plView
                    anchors.top: durCard.bottom; anchors.topMargin: 8
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.leftMargin: 8; anchors.rightMargin: 8; anchors.bottomMargin: 8
                    clip: true
                    spacing: 2
                    model: queue
                    reuseItems: true
                    cacheBuffer: 400
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {
                        policy: plView.contentHeight > plView.height ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                        contentItem: Rectangle { implicitWidth: 5; radius: 3; color: Qt.rgba(1, 1, 1, 0.2) }
                    }
                    delegate: Rectangle {
                        id: row
                        required property int index
                        required property string name
                        required property string path
                        required property int dur
                        property bool current: index === win.currentIndex
                        width: plView.width; height: 54; radius: 10
                        color: current ? Qt.rgba(0.545, 0.36, 0.965, 0.18)
                                       : (rowHover.hovered ? Qt.rgba(1, 1, 1, 0.05) : "transparent")
                        HoverHandler { id: rowHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: win.playIndex(row.index) }

                        Item {
                            id: lead
                            width: 28; height: 28
                            anchors.left: parent.left; anchors.leftMargin: 10
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                anchors.centerIn: parent; visible: !row.current
                                text: row.index + 1; color: theme.muted; font.pixelSize: 13
                            }
                            Row {
                                anchors.centerIn: parent; visible: row.current
                                spacing: 3; height: 16
                                Repeater {
                                    model: 3
                                    Rectangle {
                                        required property int index
                                        width: 3; radius: 1.5; height: 6
                                        anchors.bottom: parent.bottom
                                        color: theme.accent
                                        SequentialAnimation on height {
                                            running: row.current && win.playing
                                            loops: Animation.Infinite
                                            NumberAnimation { to: 16; duration: 280 + index * 110; easing.type: Easing.InOutSine }
                                            NumberAnimation { to: 5; duration: 280 + index * 110; easing.type: Easing.InOutSine }
                                        }
                                    }
                                }
                            }
                        }
                        Text {
                            anchors.left: lead.right; anchors.leftMargin: 10
                            anchors.right: rowEnd.left; anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: row.name; elide: Text.ElideRight
                            color: row.current ? "white" : theme.text
                            font.pixelSize: 13
                            font.weight: row.current ? Font.DemiBold : Font.Normal
                        }
                        Item {
                            id: rowEnd
                            width: 46; height: 28
                            anchors.right: parent.right; anchors.rightMargin: 6
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                anchors.right: parent.right; anchors.rightMargin: 4
                                anchors.verticalCenter: parent.verticalCenter
                                visible: !rowHover.hovered
                                text: row.dur > 0 ? win.fmt(row.dur) : ""
                                color: theme.muted; font.pixelSize: 12
                            }
                            IconBtn {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                icon: "close"; size: 28; iconSize: 14
                                visible: rowHover.hovered
                                onClicked: win.removeAt(row.index)
                            }
                        }
                    }
                }
            }
        }

        // ---------- scène vidéo ----------
        Item {
            id: stage
            anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
            anchors.right: panel.left

            Rectangle { anchors.fill: parent; color: "black" }
            VideoOutput {
                id: videoOut
                anchors.fill: parent
                fillMode: VideoOutput.PreserveAspectFit
                Component.onCompleted: backend.setDisplaySink(videoSink)
            }

            // détecte la souris partout sur la scène, même au-dessus des boutons
            HoverHandler {
                id: stageHover
                onPointChanged: if (win.hasMedia) win.poke()
            }

            MouseArea {
                id: stageMouse
                anchors.fill: parent
                enabled: win.hasMedia
                hoverEnabled: true
                cursorShape: win.showBars ? Qt.ArrowCursor : Qt.BlankCursor
                onClicked: clickTimer.restart()
                onDoubleClicked: { clickTimer.stop(); win.toggleFull() }
                onWheel: (wheel) => win.changeVolume(wheel.angleDelta.y > 0 ? 0.05 : -0.05)
            }
            Timer { id: clickTimer; interval: 220; onTriggered: win.togglePlay() }

            // sous-titres (dessinés par Nova pour être personnalisables)
            SubtitleText {
                id: subLayer
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: stage.height * backend.subStyle.position / 100 + (win.showBars ? bottomBar.height * 0.55 : 0)
                Behavior on anchors.bottomMargin { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                width: stage.width * 0.84
                baseSize: Math.max(18, stage.height * 0.045)
                text: backend.subtitleText
                visible: win.hasMedia
            }

            // barre du haut
            Item {
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                height: 96
                opacity: win.showBars ? 1 : 0
                visible: opacity > 0
                Behavior on opacity { NumberAnimation { duration: 250 } }
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#B3000000" }
                        GradientStop { position: 1; color: "#00000000" }
                    }
                }
                Text {
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.leftMargin: 24; anchors.rightMargin: 24
                    y: 20
                    text: win.currentName; elide: Text.ElideRight
                    color: "white"; font.pixelSize: 17; font.weight: Font.DemiBold
                }
                Text {
                    x: 24; y: 46
                    text: win.infoLine()
                    color: Qt.rgba(1, 1, 1, 0.6); font.pixelSize: 12
                }
            }

            // barre du bas
            Item {
                id: bottomBar
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                height: 124
                opacity: win.showBars ? 1 : 0
                visible: opacity > 0
                Behavior on opacity { NumberAnimation { duration: 250 } }
                HoverHandler { id: barHover }

                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#00000000" }
                        GradientStop { position: 1; color: "#E0000000" }
                    }
                }

                Slider {
                    id: seek
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.leftMargin: 18; anchors.rightMargin: 18
                    anchors.bottom: ctlRow.top; anchors.bottomMargin: 2
                    height: 26
                    from: 0; to: Math.max(1, player.duration)
                    focusPolicy: Qt.NoFocus
                    hoverEnabled: true
                    onMoved: win.seekTo(value)
                    Connections {
                        target: player
                        function onPositionChanged() { if (!seek.pressed) seek.value = player.position }
                    }
                    HoverHandler { id: seekHover; cursorShape: Qt.PointingHandCursor }
                    property bool hot: seek.hovered || seek.pressed
                    background: Item {
                        x: seek.leftPadding
                        y: seek.topPadding + seek.availableHeight / 2 - height / 2
                        width: seek.availableWidth
                        height: seek.hot ? 6 : 4
                        Behavior on height { NumberAnimation { duration: 120 } }
                        Rectangle { anchors.fill: parent; radius: height / 2; color: Qt.rgba(1, 1, 1, 0.2) }
                        Rectangle {
                            width: seek.visualPosition * parent.width; height: parent.height; radius: height / 2
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: theme.accent }
                                GradientStop { position: 1; color: theme.accent2 }
                            }
                        }
                    }
                    handle: Rectangle {
                        x: seek.leftPadding + seek.visualPosition * seek.availableWidth - width / 2
                        y: seek.topPadding + seek.availableHeight / 2 - height / 2
                        width: 15; height: 15; radius: 7.5
                        color: "white"
                        scale: seek.hot ? 1 : 0
                        Behavior on scale { NumberAnimation { duration: 120 } }
                    }
                    Rectangle {
                        visible: seekHover.hovered && player.duration > 0
                        property real frac: Math.max(0, Math.min(1, (seekHover.point.position.x - seek.leftPadding) / seek.availableWidth))
                        x: Math.max(0, Math.min(seek.width - width, seekHover.point.position.x - width / 2))
                        y: -height - 2
                        width: bubbleText.implicitWidth + 16; height: 26; radius: 7
                        color: theme.panel2; border.color: Qt.rgba(1, 1, 1, 0.08)
                        Text { id: bubbleText; anchors.centerIn: parent; text: win.fmt(parent.frac * player.duration); color: theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                    }
                }

                Item {
                    id: ctlRow
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.leftMargin: 14; anchors.rightMargin: 14
                    anchors.bottom: parent.bottom; anchors.bottomMargin: 12
                    height: 50

                    Row {
                        anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                        spacing: 4
                        IconBtn { icon: "prev"; tip: "Précédent (B)"; anchors.verticalCenter: parent.verticalCenter; onClicked: win.playPrev() }
                        Item {
                            width: 50; height: 50
                            anchors.verticalCenter: parent.verticalCenter
                            Rectangle {
                                anchors.fill: parent; radius: 25
                                scale: pma.pressed ? 0.92 : (pma.containsMouse ? 1.06 : 1)
                                Behavior on scale { NumberAnimation { duration: 120 } }
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0; color: theme.accent }
                                    GradientStop { position: 1; color: theme.accent2 }
                                }
                            }
                            Icon {
                                anchors.centerIn: parent
                                anchors.horizontalCenterOffset: win.playing ? 0 : 1.5
                                width: 22; height: 22
                                name: win.playing ? "pause" : "play"; color: "white"
                            }
                            MouseArea { id: pma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: win.togglePlay() }
                        }
                        IconBtn { icon: "next"; tip: "Suivant (N)"; anchors.verticalCenter: parent.verticalCenter; opacity: win.currentIndex + 1 < queue.count ? 1 : 0.35; onClicked: win.playNext() }
                        Item { width: 8; height: 1 }
                        IconBtn {
                            anchors.verticalCenter: parent.verticalCenter
                            icon: (backend.muted || backend.gain === 0) ? "mute" : (backend.gain > 1 ? "vol_boost" : (backend.gain < 0.5 ? "vol_low" : "vol"))
                            tint: backend.gain > 1 && !backend.muted ? theme.accent2 : theme.text
                            tip: "Couper le son (M)"
                            onClicked: win.toggleMute()
                        }
                        // volume 0 → 300 %
                        Slider {
                            id: volSlider
                            width: 130; height: 30
                            anchors.verticalCenter: parent.verticalCenter
                            from: 0; to: 3; stepSize: 0.05
                            wheelEnabled: true
                            value: backend.muted ? 0 : backend.gain
                            focusPolicy: Qt.NoFocus
                            onMoved: { if (backend.muted) backend.setMuted(false); backend.setGain(value); toast.show(win.volumeText()) }
                            background: Item {
                                x: volSlider.leftPadding
                                y: volSlider.topPadding + volSlider.availableHeight / 2 - 2
                                width: volSlider.availableWidth; height: 4
                                Rectangle { anchors.fill: parent; radius: 2; color: Qt.rgba(1, 1, 1, 0.2) }
                                Rectangle {
                                    width: Math.min(volSlider.visualPosition, 1 / 3) * parent.width
                                    height: 4; radius: 2; color: "white"
                                }
                                Rectangle {
                                    x: parent.width / 3
                                    width: Math.max(0, volSlider.visualPosition - 1 / 3) * parent.width
                                    height: 4; radius: 2
                                    gradient: Gradient {
                                        orientation: Gradient.Horizontal
                                        GradientStop { position: 0; color: theme.accent }
                                        GradientStop { position: 1; color: theme.accent2 }
                                    }
                                }
                                Rectangle { x: parent.width / 3 - 1; y: -3; width: 2; height: 10; radius: 1; color: Qt.rgba(1, 1, 1, 0.55) }
                            }
                            handle: Rectangle {
                                x: volSlider.leftPadding + volSlider.visualPosition * volSlider.availableWidth - 6
                                y: volSlider.topPadding + volSlider.availableHeight / 2 - 6
                                width: 12; height: 12; radius: 6
                                color: backend.gain > 1 ? theme.accent2 : "white"
                            }
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 42
                            text: backend.muted ? "" : Math.round(backend.gain * 100) + "%"
                            color: backend.gain > 1 ? theme.accent2 : theme.muted
                            font.pixelSize: 12; font.weight: Font.DemiBold
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: win.fmt(player.position) + "  /  " + win.fmt(player.duration)
                            color: theme.text; font.pixelSize: 13; font.weight: Font.Medium
                        }
                    }

                    Row {
                        anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                        spacing: 4
                        Rectangle {
                            id: speedPill
                            anchors.verticalCenter: parent.verticalCenter
                            width: speedText.implicitWidth + 22; height: 30; radius: 15
                            color: spma.containsMouse ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.08)
                            Text { id: speedText; anchors.centerIn: parent; text: win.rateText(player.playbackRate); color: theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                            MouseArea { id: spma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: speedPop.open() }
                            DarkPopup {
                                id: speedPop
                                x: (parent.width - width) / 2
                                y: -height - 12
                                contentItem: Column {
                                    MenuHeader { text: "VITESSE" }
                                    Repeater {
                                        model: win.speeds
                                        delegate: MenuRow {
                                            required property var modelData
                                            width: 150
                                            text: modelData === 1 ? "Normale" : win.rateText(modelData)
                                            checked: Math.abs(player.playbackRate - modelData) < 0.01
                                            onClicked: { win.setSpeed(modelData); speedPop.close() }
                                        }
                                    }
                                }
                            }
                        }
                        Item { width: 4; height: 1 }
                        IconBtn {
                            id: trackBtn
                            anchors.verticalCenter: parent.verticalCenter
                            icon: "subs"; tip: "Audio et sous-titres"
                            active: backend.subtitleSource === "external" || player.activeSubtitleTrack >= 0
                            onClicked: trackPop.open()
                            DarkPopup {
                                id: trackPop
                                x: Math.min(0, (parent.width - width) / 2)
                                y: -height - 12
                                contentItem: Column {
                                    MenuHeader { text: "AUDIO" }
                                    Repeater {
                                        model: player.audioTracks
                                        delegate: MenuRow {
                                            required property var modelData
                                            required property int index
                                            text: win.trackName(modelData, index)
                                            checked: player.activeAudioTrack === index
                                            onClicked: { player.activeAudioTrack = index; backend.flushAudio(); trackPop.close() }
                                        }
                                    }
                                    Text {
                                        visible: player.audioTracks.length === 0
                                        text: "Aucune piste"; color: theme.muted; font.pixelSize: 13
                                        leftPadding: 12; topPadding: 4; bottomPadding: 6
                                    }
                                    MenuSep {}
                                    MenuHeader { text: "SOUS-TITRES" }
                                    MenuRow {
                                        text: "Désactivés"
                                        checked: backend.subtitleSource === "off" || (backend.subtitleSource === "embedded" && player.activeSubtitleTrack === -1)
                                        onClicked: { backend.useEmbedded(-1); trackPop.close() }
                                    }
                                    Repeater {
                                        model: player.subtitleTracks
                                        delegate: MenuRow {
                                            required property var modelData
                                            required property int index
                                            text: win.trackName(modelData, index)
                                            checked: backend.subtitleSource === "embedded" && player.activeSubtitleTrack === index
                                            onClicked: { backend.useEmbedded(index); trackPop.close() }
                                        }
                                    }
                                    Repeater {
                                        model: backend.externalSubs
                                        delegate: MenuRow {
                                            required property var modelData
                                            icon: "film"
                                            text: modelData.name
                                            checked: backend.subtitleSource === "external" && backend.externalName === modelData.name
                                            onClicked: { backend.loadExternal(modelData.path); trackPop.close() }
                                        }
                                    }
                                    MenuSep {}
                                    MenuRow { icon: "folder"; text: "Charger un fichier .srt…"; onClicked: { trackPop.close(); subDlg.open() } }
                                    MenuRow { icon: "brush"; text: "Personnaliser les sous-titres…"; onClicked: { trackPop.close(); subPop.open() } }
                                }
                            }
                        }
                        IconBtn { anchors.verticalCenter: parent.verticalCenter; icon: "camera"; tip: "Capture d'écran (S)"; onClicked: win.screenshot() }
                        IconBtn { anchors.verticalCenter: parent.verticalCenter; icon: "folder"; iconSize: 20; tip: "Ouvrir (Ctrl+O)"; onClicked: openDlg.open() }
                        IconBtn { anchors.verticalCenter: parent.verticalCenter; icon: "list"; active: win.playlistOpen; tip: "File d'attente (P)"; onClicked: win.playlistOpen = !win.playlistOpen }
                        IconBtn { anchors.verticalCenter: parent.verticalCenter; icon: win.isFull ? "unfull" : "full"; tip: "Plein écran (F)"; onClicked: win.toggleFull() }
                    }
                }
            }

            // animation centrale (play / pause / avance…)
            Rectangle {
                id: flash
                width: 84; height: 84; radius: 42
                anchors.centerIn: parent
                color: "#99000000"
                opacity: 0
                visible: opacity > 0
                property string icon: "play"
                Icon { anchors.centerIn: parent; width: 34; height: 34; name: flash.icon; color: "white" }
                function show(n) { icon = n; flashAnim.restart() }
                ParallelAnimation {
                    id: flashAnim
                    NumberAnimation { target: flash; property: "opacity"; from: 1; to: 0; duration: 650; easing.type: Easing.InQuad }
                    NumberAnimation { target: flash; property: "scale"; from: 0.85; to: 1.25; duration: 650; easing.type: Easing.OutCubic }
                }
            }
        }

        // ---------- écran d'accueil ----------
        Item {
            id: empty
            anchors.fill: stage
            visible: !win.hasMedia
            clip: true
            Rectangle { anchors.fill: parent; color: theme.bg }

            // mur d'affiches qui défile
            Item {
                id: wall
                anchors.centerIn: parent
                width: Math.max(parent.width, parent.height) * 1.7
                height: width
                rotation: -12
                opacity: 0.55
                readonly property int cols: Math.ceil(width / 164)
                readonly property int perCol: 7
                readonly property real cardStep: 225 + 14
                Row {
                    anchors.centerIn: parent
                    spacing: 14
                    Repeater {
                        model: wall.cols
                        delegate: Item {
                            id: col
                            required property int index
                            width: 150; height: wall.height
                            readonly property real loopH: wall.perCol * wall.cardStep
                            Column {
                                id: colContent
                                spacing: 14
                                Repeater {
                                    model: wall.perCol * 2 + Math.ceil(wall.height / wall.cardStep)
                                    delegate: PosterCard {
                                        required property int index
                                        idx: col.index * 5 + (index % wall.perCol) * 3 + col.index * col.index
                                    }
                                }
                            }
                            NumberAnimation {
                                target: colContent; property: "y"
                                from: col.index % 2 ? -col.loopH : 0
                                to: col.index % 2 ? 0 : -col.loopH
                                duration: col.loopH / (14 + (col.index % 3) * 5) * 1000
                                loops: Animation.Infinite
                                running: empty.visible && !splash.visible
                            }
                        }
                    }
                }
            }
            // voile pour garder le texte lisible
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#990A0A0F" }
                    GradientStop { position: 0.5; color: "#D90A0A0F" }
                    GradientStop { position: 1.0; color: "#F20A0A0F" }
                }
            }
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeColor: "transparent"
                    fillGradient: RadialGradient {
                        centerX: empty.width * 0.5; centerY: empty.height * 0.38
                        focalX: centerX; focalY: centerY
                        centerRadius: Math.max(empty.width, empty.height) * 0.55
                        GradientStop { position: 0.0; color: "#3A8B5CF6" }
                        GradientStop { position: 0.5; color: "#10EC4899" }
                        GradientStop { position: 1.0; color: "#000A0A0F" }
                    }
                    startX: 0; startY: 0
                    PathLine { x: empty.width; y: 0 }
                    PathLine { x: empty.width; y: empty.height }
                    PathLine { x: 0; y: empty.height }
                    PathLine { x: 0; y: 0 }
                }
            }
            Rectangle {
                anchors.fill: parent; anchors.margins: 22; radius: 24
                color: "transparent"; border.width: 2; border.color: theme.accent
                opacity: dropArea.containsDrag ? 0.9 : 0
                Behavior on opacity { NumberAnimation { duration: 150 } }
            }

            Column {
                id: homeContent
                anchors.centerIn: parent
                width: 470
                Rectangle {
                    width: 108; height: 108; radius: 34
                    anchors.horizontalCenter: parent.horizontalCenter
                    gradient: Gradient {
                        GradientStop { position: 0; color: theme.accent }
                        GradientStop { position: 1; color: theme.accent2 }
                    }
                    Icon { anchors.centerIn: parent; anchors.horizontalCenterOffset: 3; width: 46; height: 46; name: "play"; color: "white" }
                }
                Item { width: 1; height: 30 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Glisse une vidéo ici"; color: theme.text; font.pixelSize: 30; font.weight: Font.Bold }
                Item { width: 1; height: 8 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "MP4, MKV, AVI, MOV, WEBM… ou un dossier entier"; color: Qt.rgba(1, 1, 1, 0.7); font.pixelSize: 14 }
                Item { width: 1; height: 30 }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 12
                    TextBtn { primary: true; icon: "folder"; text: "Ouvrir des vidéos"; onClicked: openDlg.open() }
                    TextBtn { text: "Ouvrir un dossier"; onClicked: folderDlg.open() }
                }
                Item { width: 1; height: 38 }
                Rectangle {
                    width: parent.width
                    height: recCol.implicitHeight + 16
                    radius: 14
                    visible: backend.recents.length > 0
                    color: Qt.rgba(0.04, 0.04, 0.06, 0.7)
                    border.color: Qt.rgba(1, 1, 1, 0.06)
                    Column {
                        id: recCol
                        anchors.left: parent.left; anchors.right: parent.right
                        anchors.top: parent.top; anchors.margins: 8
                        spacing: 2
                        Text { text: "RÉCENTS"; color: theme.muted; font.pixelSize: 11; font.letterSpacing: 1.4; font.weight: Font.DemiBold; leftPadding: 12; topPadding: 4; bottomPadding: 6 }
                        Repeater {
                            model: backend.recents
                            delegate: Rectangle {
                                id: rd
                                required property string modelData
                                width: parent.width; height: 40; radius: 10
                                color: rh.hovered ? Qt.rgba(1, 1, 1, 0.07) : "transparent"
                                HoverHandler { id: rh; cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: win.addFiles([rd.modelData], true) }
                                Icon { id: ri; name: "film"; width: 18; height: 18; strokeW: 1.7; color: theme.muted; anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter }
                                Text {
                                    anchors.left: ri.right; anchors.leftMargin: 12
                                    anchors.right: parent.right; anchors.rightMargin: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: backend.displayName(rd.modelData); color: theme.text; font.pixelSize: 13; elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
                Item { width: 1; height: 22 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Appuie sur H pour voir les raccourcis clavier   ·   Nova v" + appVersion; color: theme.muted; font.pixelSize: 12 }
            }

            // affiches : choisir le dossier
            Row {
                anchors.right: parent.right; anchors.bottom: parent.bottom
                anchors.margins: 18
                spacing: 8
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: backend.posters.length === 0
                    text: "Mets tes propres affiches en fond →"
                    color: theme.muted; font.pixelSize: 12
                }
                TextBtn { small: true; icon: "image"; text: "Affiches"; onClicked: posterPop.open() }
            }
            DarkPopup {
                id: posterPop
                x: empty.width - width - 18
                y: empty.height - height - 64
                contentItem: Column {
                    MenuHeader { text: "AFFICHES DE FOND" }
                    Text {
                        width: 270; leftPadding: 12; rightPadding: 12; bottomPadding: 8
                        wrapMode: Text.WordWrap
                        text: backend.posters.length > 0
                              ? backend.posters.length + " affiche(s) trouvée(s) dans ton dossier."
                              : "Ajoute des images (JPG, PNG, WEBP) dans ton dossier d'affiches : elles défileront ici."
                        color: theme.muted; font.pixelSize: 12
                    }
                    MenuRow { width: 270; icon: "folder"; text: "Ouvrir mon dossier d'affiches"; onClicked: { posterPop.close(); backend.openPosterDir() } }
                    MenuRow { width: 270; icon: "image"; text: "Choisir un autre dossier…"; onClicked: { posterPop.close(); posterDlg.open() } }
                    MenuRow { width: 270; icon: "check"; text: "Actualiser"; onClicked: { posterPop.close(); backend.setPosterDir(backend.posterDirName()) } }
                }
            }
        }

        // ---------- dépôt de fichiers pendant la lecture ----------
        Rectangle {
            anchors.fill: stage
            visible: dropArea.containsDrag && win.hasMedia
            color: "#B30A0A0F"
            border.width: 2; border.color: theme.accent
            Text { anchors.centerIn: parent; text: "Dépose pour ajouter à la file"; color: "white"; font.pixelSize: 22; font.weight: Font.DemiBold }
        }

        // ---------- notification ----------
        Rectangle {
            id: toast
            anchors.horizontalCenter: stage.horizontalCenter
            y: 84
            width: toastText.implicitWidth + 34; height: 38; radius: 19
            color: "#E6181822"; border.color: Qt.rgba(1, 1, 1, 0.08)
            opacity: 0
            visible: opacity > 0
            z: 50
            Behavior on opacity { NumberAnimation { duration: 180 } }
            Text { id: toastText; anchors.centerIn: parent; color: theme.text; font.pixelSize: 13; font.weight: Font.Medium }
            Timer { id: toastTimer; interval: 1600; onTriggered: toast.opacity = 0 }
            function show(msg, ms) { toastText.text = msg; opacity = 1; toastTimer.interval = ms || 1600; toastTimer.restart() }
        }

        DropArea {
            id: dropArea
            anchors.fill: parent
            onEntered: (drag) => drag.accept(Qt.CopyAction)
            onDropped: (drop) => {
                var urls = drop.urls
                var subs = [], others = []
                for (var i = 0; i < urls.length; i++) {
                    var u = String(urls[i]).toLowerCase()
                    if (u.endsWith(".srt") || u.endsWith(".vtt")) subs.push(urls[i]); else others.push(urls[i])
                }
                if (subs.length > 0 && win.hasMedia) {
                    if (backend.loadExternal(subs[0])) toast.show("Sous-titres chargés")
                }
                if (others.length > 0) win.addFiles(backend.expandUrls(others), true)
                drop.accept(Qt.CopyAction)
            }
        }

        // ---------- animation d'ouverture ----------
        Rectangle {
            id: splash
            anchors.fill: parent
            z: 100
            color: theme.bg
            visible: true
            MouseArea { anchors.fill: parent; onClicked: splashAnim.complete() }
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeColor: "transparent"
                    fillGradient: RadialGradient {
                        centerX: splash.width / 2; centerY: splash.height / 2
                        focalX: centerX; focalY: centerY
                        centerRadius: Math.max(splash.width, splash.height) * 0.5
                        GradientStop { position: 0; color: "#408B5CF6" }
                        GradientStop { position: 1; color: "#000A0A0F" }
                    }
                    startX: 0; startY: 0
                    PathLine { x: splash.width; y: 0 }
                    PathLine { x: splash.width; y: splash.height }
                    PathLine { x: 0; y: splash.height }
                    PathLine { x: 0; y: 0 }
                }
            }
            Rectangle {
                id: ring
                anchors.centerIn: logo
                width: 140; height: 140; radius: 70
                color: "transparent"
                border.width: 3; border.color: theme.accent2
                opacity: 0; scale: 1
            }
            Rectangle {
                id: logo
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -24
                width: 120; height: 120; radius: 38
                scale: 0.4; opacity: 0
                gradient: Gradient {
                    GradientStop { position: 0; color: theme.accent }
                    GradientStop { position: 1; color: theme.accent2 }
                }
                Icon { anchors.centerIn: parent; anchors.horizontalCenterOffset: 4; width: 52; height: 52; name: "play"; color: "white" }
            }
            Text {
                id: splashTitle
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: logo.bottom; anchors.topMargin: 26
                text: "NOVA"
                color: "white"; font.pixelSize: 34; font.weight: Font.Black
                font.letterSpacing: 14
                opacity: 0
            }
            SequentialAnimation {
                id: splashAnim
                running: true
                ParallelAnimation {
                    NumberAnimation { target: logo; property: "scale"; to: 1; duration: 650; easing.type: Easing.OutBack; easing.overshoot: 2.2 }
                    NumberAnimation { target: logo; property: "opacity"; to: 1; duration: 300 }
                    SequentialAnimation {
                        PauseAnimation { duration: 250 }
                        ParallelAnimation {
                            NumberAnimation { target: ring; property: "opacity"; from: 0.8; to: 0; duration: 800; easing.type: Easing.OutQuad }
                            NumberAnimation { target: ring; property: "scale"; from: 0.9; to: 2.6; duration: 800; easing.type: Easing.OutCubic }
                        }
                    }
                    SequentialAnimation {
                        PauseAnimation { duration: 300 }
                        ParallelAnimation {
                            NumberAnimation { target: splashTitle; property: "opacity"; to: 1; duration: 400 }
                            NumberAnimation { target: splashTitle; property: "font.letterSpacing"; from: 30; to: 14; duration: 600; easing.type: Easing.OutCubic }
                        }
                    }
                }
                PauseAnimation { duration: 350 }
                ParallelAnimation {
                    NumberAnimation { target: splash; property: "opacity"; to: 0; duration: 450; easing.type: Easing.InOutQuad }
                    NumberAnimation { target: logo; property: "scale"; to: 1.4; duration: 450; easing.type: Easing.InQuad }
                }
                onFinished: { splash.visible = false; if (startupMessage !== "") toast.show(startupMessage, 4000) }
            }
        }
    }

    // ------------------------------------------------------------ personnalisation des sous-titres
    DarkPopup {
        id: subPop
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        padding: 24
        Overlay.modal: Rectangle { color: "#99000000" }
        readonly property var s: backend.subStyle
        contentItem: Row {
            spacing: 26
            // aperçu
            Column {
                spacing: 10
                Text { text: "Sous-titres"; color: theme.text; font.pixelSize: 19; font.weight: Font.Bold }
                Text { text: "Aperçu en direct"; color: theme.muted; font.pixelSize: 12 }
                Rectangle {
                    width: 380; height: 240; radius: 12
                    clip: true
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#3B4A6B" }
                        GradientStop { position: 0.55; color: "#7A5A6E" }
                        GradientStop { position: 1; color: "#1E1A24" }
                    }
                    Rectangle { x: 230; y: 34; width: 80; height: 80; radius: 40; color: "#F5C98B"; opacity: 0.85 }
                    Rectangle { x: -40; y: 150; width: 260; height: 140; radius: 70; color: "#15121B" }
                    Rectangle { x: 180; y: 170; width: 300; height: 140; radius: 70; color: "#0F0D14" }
                    SubtitleText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: parent.height * subPop.s.position / 100
                        width: parent.width * 0.9
                        baseSize: 17
                        text: "Voici à quoi ressembleront<br>tes <i>sous-titres</i>."
                    }
                }
                Text {
                    width: 380; wrapMode: Text.WordWrap
                    text: "Astuce : un fichier .srt du même nom que la vidéo est chargé automatiquement. Tu peux aussi glisser un .srt sur la vidéo."
                    color: theme.muted; font.pixelSize: 12
                }
            }
            // réglages
            Column {
                spacing: 14
                width: 300
                Item { width: 1; height: 26 }
                Text { text: "Taille  ·  " + subPop.s.size + " %"; color: theme.text; font.pixelSize: 13 }
                NiceSlider {
                    width: parent.width; from: 50; to: 200; stepSize: 5
                    value: subPop.s.size
                    onMoved: backend.setSubStyle("size", Math.round(value))
                }
                Text { text: "Couleur"; color: theme.text; font.pixelSize: 13 }
                Row {
                    spacing: 10
                    Repeater {
                        model: win.subColors
                        delegate: Rectangle {
                            required property string modelData
                            width: 30; height: 30; radius: 15
                            color: modelData
                            border.width: subPop.s.color === modelData ? 3 : 1
                            border.color: subPop.s.color === modelData ? theme.accent : Qt.rgba(1, 1, 1, 0.2)
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: backend.setSubStyle("color", parent.modelData) }
                        }
                    }
                }
                Text { text: "Style"; color: theme.text; font.pixelSize: 13 }
                Row {
                    spacing: 8
                    Chip { text: "Contour"; selected: subPop.s.style === "outline"; onClicked: backend.setSubStyle("style", "outline") }
                    Chip { text: "Ombre"; selected: subPop.s.style === "shadow"; onClicked: backend.setSubStyle("style", "shadow") }
                    Chip { text: "Fond"; selected: subPop.s.style === "box"; onClicked: backend.setSubStyle("style", "box") }
                    Chip { text: "Gras"; selected: subPop.s.bold; onClicked: backend.setSubStyle("bold", !subPop.s.bold) }
                }
                Text { visible: subPop.s.style === "box"; text: "Opacité du fond  ·  " + Math.round(subPop.s.boxOpacity * 100) + " %"; color: theme.text; font.pixelSize: 13 }
                NiceSlider {
                    visible: subPop.s.style === "box"
                    width: parent.width; from: 0.1; to: 1; stepSize: 0.05
                    value: subPop.s.boxOpacity
                    onMoved: backend.setSubStyle("boxOpacity", value)
                }
                Text { text: "Hauteur  ·  " + subPop.s.position + " %"; color: theme.text; font.pixelSize: 13 }
                NiceSlider {
                    width: parent.width; from: 2; to: 40; stepSize: 1
                    value: subPop.s.position
                    onMoved: backend.setSubStyle("position", Math.round(value))
                }
                Text { text: "Décalage (fichiers .srt)"; color: theme.text; font.pixelSize: 13 }
                Row {
                    spacing: 8
                    IconBtn { icon: "minus"; size: 32; iconSize: 16; onClicked: backend.setSubDelay(backend.subDelay - 100) }
                    Rectangle {
                        width: 90; height: 32; radius: 8; color: Qt.rgba(1, 1, 1, 0.06)
                        Text { anchors.centerIn: parent; text: win.delayText(backend.subDelay); color: theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                    }
                    IconBtn { icon: "plus"; size: 32; iconSize: 16; onClicked: backend.setSubDelay(backend.subDelay + 100) }
                    Chip { text: "0"; onClicked: backend.setSubDelay(0) }
                }
                Item { width: 1; height: 4 }
                Row {
                    spacing: 10
                    TextBtn { small: true; text: "Réinitialiser"; onClicked: backend.resetSubStyle() }
                    TextBtn { small: true; primary: true; text: "Terminé"; onClicked: subPop.close() }
                }
            }
        }
    }

    // ------------------------------------------------------------ aide
    DarkPopup {
        id: helpPop
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        padding: 26
        Overlay.modal: Rectangle { color: "#99000000" }
        contentItem: Column {
            spacing: 18
            Row {
                spacing: 10
                Icon { name: "keys"; width: 22; height: 22; color: theme.accent; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Raccourcis clavier"; color: theme.text; font.pixelSize: 19; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
            }
            Grid {
                columns: 2; columnSpacing: 34; rowSpacing: 11
                Repeater {
                    model: [
                        ["Espace / K", "Lecture / pause"],
                        ["F / double-clic", "Plein écran"],
                        ["← / →", "Reculer / avancer 5 s"],
                        ["J / L", "Reculer / avancer 10 s"],
                        ["↑ / ↓ / molette", "Volume (jusqu'à 300 %)"],
                        ["M", "Couper le son"],
                        [", / ;", "Image par image"],
                        ["− / +", "Vitesse de lecture"],
                        ["S", "Capture d'écran"],
                        ["P", "File d'attente"],
                        ["N / B", "Vidéo suivante / précédente"],
                        ["C", "Personnaliser les sous-titres"],
                        ["Ctrl + O", "Ouvrir des vidéos"],
                        ["H", "Cette aide"]
                    ]
                    delegate: Row {
                        required property var modelData
                        spacing: 12
                        Rectangle {
                            width: 128; height: 28; radius: 7
                            color: Qt.rgba(1, 1, 1, 0.07); border.color: Qt.rgba(1, 1, 1, 0.08)
                            Text { anchors.centerIn: parent; text: modelData[0]; color: theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                        }
                        Text { width: 200; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]; color: theme.muted; font.pixelSize: 13 }
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        var init = backend.initialFiles
        if (init.length > 0) addFiles(backend.expandUrls(init), true)
    }
}
"""


def main(startup_message=""):
    os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setWindowIcon(make_app_icon())

    backend = Backend([a for a in sys.argv[1:] if os.path.exists(a)])
    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("backend", backend)
    ctx.setContextProperty("player", backend.player)
    ctx.setContextProperty("theme", THEME)
    ctx.setContextProperty("icons", ICONS)
    ctx.setContextProperty("appVersion", APP_VERSION)
    ctx.setContextProperty("startupMessage", startup_message or "")
    engine.loadData(QML.encode("utf-8"),
                    QUrl.fromLocalFile(str(Path(__file__).resolve().with_name("Main.qml"))))
    if not engine.rootObjects():
        raise RuntimeError("Impossible de charger l'interface de Nova")
    window = engine.rootObjects()[0]
    dark_titlebar(window)
    app.aboutToQuit.connect(backend.shutdown)
    code = app.exec()
    backend.player.stop()
    return code


if __name__ == "__main__":
    sys.exit(main())
