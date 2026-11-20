#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nova — application (interface + fonctions).
Ce fichier est celui qui se met à jour automatiquement : il est chargé par
nova.py (le lanceur), qui le télécharge depuis GitHub quand une nouvelle
version est publiée.
"""
import base64
import bisect
import gc
import math
import hashlib
import json
import os
import random
import re
import sys
from array import array
from collections import deque
from pathlib import Path

from PySide6.QtCore import (QObject, Property, QSettings, QSize, QStandardPaths, QTimer,
                            QUrl, Signal, Slot, QPointF, QRectF, Qt)
from PySide6.QtGui import (QColor, QCursor, QDesktopServices, QGuiApplication, QIcon, QImage,
                           QLinearGradient, QPainter, QPainterPath, QPixmap)
from PySide6.QtQml import QQmlApplicationEngine
from PySide6 import QtMultimedia, QtQuick  # noqa: F401  (embarque le moteur vidéo dans le .exe)
from PySide6.QtMultimedia import (QAudio, QAudioBufferOutput, QAudioFormat, QAudioOutput,
                                  QAudioSink, QMediaDevices, QMediaPlayer, QVideoFrame,
                                  QVideoFrameFormat, QVideoSink)
from PySide6.QtQuickControls2 import QQuickStyle

APP_NAME = "Nova"
APP_VERSION = 16  # augmenter à chaque mise à jour publiée

VIDEO_EXT = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv", ".ts",
    ".m2ts", ".mts", ".mpg", ".mpeg", ".3gp", ".ogv", ".vob", ".divx",
}
SUB_EXT = {".srt", ".vtt"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_GAIN = 3.0


def _ev(x):
    """Valeur entière d'une énumération Qt (QAudio et QtAudio sont deux classes différentes)."""
    return getattr(x, "value", x)


AUDIO_NO_ERROR, AUDIO_UNDERRUN = 0, 3   # QtAudio.Error.NoError / UnderrunError
AUDIO_STOPPED = 2                        # QtAudio.State.StoppedState


def log(msg):
    try:
        root = os.environ.get("LOCALAPPDATA") or os.path.join(Path.home(), ".local", "share")
        d = Path(root) / "Nova" / "app"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "nova.log", "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except OSError:
        pass

# Shader de conversion HDR -> écran normal (tone mapping), compilé pour DirectX/OpenGL/Metal
TONEMAP_QSB = (
    "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"
)
STATS_QSB = (
    "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"
    "7XqsTX3x9//mhFaS"
)
CLEAN_QSB = (
    "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"
)
PROBE_QSB = (
    "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"
    "RP6KBPRzUO7/71yTH/rFadz/6nkbMf4E2NG8Eg=="
)

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
    "audio":   ["", "M9 17.5V6l11-2v11.5 M9 17.5a2.5 2.5 0 1 1-5 0a2.5 2.5 0 1 1 5 0 "
                    "M20 15.5a2.5 2.5 0 1 1-5 0a2.5 2.5 0 1 1 5 0 M9 9.5l11-2"],
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


# ---------------------------------------------------------------- calibrage HDR
CAL_W, CAL_H = 96, 16
CAL_GRAYS = [0.7518, 0.5081, 0.40]     # gris PQ : 1000 nits, 100 nits, 30 nits
PQ_M1, PQ_M2, PQ_C1, PQ_C2, PQ_C3 = 0.1593017578125, 78.84375, 0.8359375, 18.8515625, 18.6875


def pq_to_nits(e):
    e = min(max(e, 0.0), 1.0)
    p = e ** (1 / PQ_M2)
    return (max(p - PQ_C1, 0.0) / max(PQ_C2 - PQ_C3 * p, 1e-9)) ** (1 / PQ_M1) * 10000.0


def nits_to_pq(n):
    y = max(n, 0.0) / 10000.0
    yp = y ** PQ_M1
    return ((PQ_C1 + PQ_C2 * yp) / (1 + PQ_C3 * yp)) ** PQ_M2


QT_PQ_ML = 0.5081                  # paramètre fixe de Qt pour le PQ
QT_HLG_DEFAULT = (0.836, 0.975)    # paramètres mesurés de Qt pour le HLG


def hlg_to_linear(e):
    a, b, c = 0.17883277, 0.28466892, 0.55991073
    e = min(max(e, 0.0), 1.5)
    return e * e / 3 if e < 0.5 else (math.exp((e - c) / a) + b) / 12


def qt_expected(e, mw, ml=QT_PQ_ML, tr="pq"):
    """Ce que le shader HDR de Qt (P010) produit pour un gris e (modèle mesuré, Qt 6.12)."""
    ks = 1.5 * ml - 0.5
    p = e / mw
    s = 1.0
    if p >= ks and ks < 0.999:
        t = (p - ks) / (1 - ks)
        t2, t3 = t * t, t * t * t
        pn = (2 * t3 - 3 * t2 + 1) * ks + (t3 - 2 * t2 + t) * (1 - ks) + (-2 * t3 + 3 * t2) * ml
        s = pn * mw / e
    if tr == "hlg":
        v = hlg_to_linear(e * s)
        x = v * max(v, 1e-9) ** 0.2 * ml
    else:
        x = pq_to_nits(e * s) / 100.0
    x = max(x, 0.0)
    return x * 12.92 if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def make_calibration_frame(kind):
    frame = _make_calibration_frame(kind)
    if frame is not None and kind == "p010hlg":
        fmt = frame.surfaceFormat()
        fmt.setColorTransfer(QVideoFrameFormat.ColorTransfer.ColorTransfer_STD_B67)
        f2 = QVideoFrame(fmt)
        if f2.map(QVideoFrame.MapMode.WriteOnly) and frame.map(QVideoFrame.MapMode.ReadOnly):
            for pl in range(2):
                f2.bits(pl)[:] = frame.bits(pl)[:]
            f2.unmap()
            frame.unmap()
            return f2
        return None
    return frame


def _make_calibration_frame(kind):
    """Image HDR10 de test (gris PQ connus), au format du décodage carte graphique (P010)
    ou logiciel (YUV420P10)."""
    PF = QVideoFrameFormat.PixelFormat
    hw = kind in ("p010", "p010hlg")
    pf = PF.Format_P010 if hw else PF.Format_YUV420P10
    fmt = QVideoFrameFormat(QSize(CAL_W, CAL_H), pf)
    fmt.setColorTransfer(QVideoFrameFormat.ColorTransfer.ColorTransfer_ST2084)
    fmt.setColorSpace(QVideoFrameFormat.ColorSpace.ColorSpace_BT2020)
    fmt.setColorRange(QVideoFrameFormat.ColorRange.ColorRange_Video)
    frame = QVideoFrame(fmt)
    if not frame.map(QVideoFrame.MapMode.WriteOnly):
        return None
    zone = CAL_W // len(CAL_GRAYS)
    ys = [round(64 + 876 * g) for g in CAL_GRAYS]
    shift = 6 if hw else 0

    def put(buf, off, v):
        buf[off] = v & 0xFF
        buf[off + 1] = (v >> 8) & 0xFF

    yb, ybpl = frame.bits(0), frame.bytesPerLine(0)
    for row in range(CAL_H):
        for x in range(CAL_W):
            put(yb, row * ybpl + x * 2, ys[min(x // zone, len(ys) - 1)] << shift)
    if hw:
        cb, cbpl = frame.bits(1), frame.bytesPerLine(1)
        for row in range(CAL_H // 2):
            for x in range(CAL_W // 2):
                put(cb, row * cbpl + x * 4, 512 << 6)
                put(cb, row * cbpl + x * 4 + 2, 512 << 6)
    else:
        for pl in (1, 2):
            b, bpl = frame.bits(pl), frame.bytesPerLine(pl)
            for row in range(CAL_H // 2):
                for x in range(CAL_W // 2):
                    put(b, row * bpl + x * 2, 512)
    frame.unmap()
    return frame


def make_sized_calibration_frame(width, height, max_lum, hlg=False):
    """Image de test P010 aux dimensions de la vidéo (rempli ligne par ligne, rapide même en 4K)."""
    width -= width % 2
    height -= height % 2
    fmt = QVideoFrameFormat(QSize(width, height), QVideoFrameFormat.PixelFormat.Format_P010)
    fmt.setColorTransfer(QVideoFrameFormat.ColorTransfer.ColorTransfer_STD_B67 if hlg
                         else QVideoFrameFormat.ColorTransfer.ColorTransfer_ST2084)
    fmt.setColorSpace(QVideoFrameFormat.ColorSpace.ColorSpace_BT2020)
    fmt.setColorRange(QVideoFrameFormat.ColorRange.ColorRange_Video)
    if max_lum and max_lum > 0:
        fmt.setMaxLuminance(max_lum)
    frame = QVideoFrame(fmt)
    if not frame.map(QVideoFrame.MapMode.WriteOnly):
        return None
    n = len(CAL_GRAYS)
    bounds = [width * i // n for i in range(n + 1)]
    yrow = bytearray()
    for i, g in enumerate(CAL_GRAYS):
        v = round(64 + 876 * g) << 6
        yrow += bytes((v & 0xFF, v >> 8)) * (bounds[i + 1] - bounds[i])
    c = 512 << 6
    crow = bytes((c & 0xFF, c >> 8)) * width
    yb, ybpl = frame.bits(0), frame.bytesPerLine(0)
    cb, cbpl = frame.bits(1), frame.bytesPerLine(1)
    for r in range(height):
        yb[r * ybpl: r * ybpl + len(yrow)] = yrow
    for r in range(height // 2):
        cb[r * cbpl: r * cbpl + len(crow)] = crow
    frame.unmap()
    return frame


def solve_pq(measured):
    """Retrouve les deux réglages de Qt (mw, ml) pour sa formule PQ."""
    def err(mw, ml):
        return sum((qt_expected(g, mw, ml) - m) ** 2 for g, m in zip(CAL_GRAYS, measured))
    best = None
    for i in range(300, 1001, 5):
        for j in range(440, 600, 5):
            e = err(i / 1000, j / 1000)
            if best is None or e < best[0]:
                best = (e, i / 1000, j / 1000)
    _, mw0, ml0 = best
    for i in range(-6, 7):
        for j in range(-6, 7):
            mw, ml = mw0 + i / 1000, ml0 + j / 1000
            if 0.2 < mw <= 1.0:
                e = err(mw, ml)
                if e < best[0]:
                    best = (e, mw, ml)
    return best[1], best[2], (best[0] / len(CAL_GRAYS)) ** 0.5


def solve_mastering_white(measured):
    mw, _ml, rms = solve_pq(measured)
    return mw, rms


def solve_hlg(measured):
    """Retrouve les deux réglages de Qt (mw, ml) pour le HLG."""
    def err(mw, ml):
        return sum((qt_expected(g, mw, ml, "hlg") - m) ** 2 for g, m in zip(CAL_GRAYS, measured))
    best = None
    for i in range(30, 101, 2):
        for j in range(30, 151, 2):
            e = err(i / 100, j / 100)
            if best is None or e < best[0]:
                best = (e, i / 100, j / 100)
    _, mw0, ml0 = best
    for i in range(-20, 21):
        for j in range(-20, 21):
            mw, ml = mw0 + i / 1000, ml0 + j / 1000
            if 0.2 < mw <= 1.0 and ml > 0.2:
                e = err(mw, ml)
                if e < best[0]:
                    best = (e, mw, ml)
    return best[1], best[2], (best[0] / len(CAL_GRAYS)) ** 0.5


def probe_value(color):
    """Décode la valeur mesurée par la sonde (codée sur deux canaux : précision ~0,0001)."""
    t = color.red() + color.green() / 255.0
    return t / 255.0 * 5.0 - 1.25


def calibration_matches(kind, raw):
    """Compare la mesure au modèle attendu pour ce chemin de décodage."""
    if kind == "p010":
        expected = [qt_expected(g, 1.0) for g in CAL_GRAYS]
    elif kind == "p010hlg":
        mw, ml, rms = solve_hlg([sum(c) / 3 for c in raw])
        expected = [qt_expected(g, mw, ml, "hlg") for g in CAL_GRAYS]
    else:
        expected = list(CAL_GRAYS)
    got = [sum(c) / 3 for c in raw]
    return all(abs(a - b) < 0.03 for a, b in zip(got, expected)), expected


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
    hdrChanged = Signal()
    calibrationRequest = Signal(bool)
    mainProbeRequest = Signal()
    hdrMismatch = Signal()

    def __init__(self, initial_files):
        super().__init__()
        self._s = QSettings(APP_NAME, "NovaPlayer")
        self._initial = initial_files

        # lecteur
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        # les images vont directement du décodeur à l'affichage (sans passer par Python)
        self._display = None                    # sink de l'affichage (VideoOutput)
        self._clearing_sub = False
        self._hdr_timer = QTimer(self, interval=250)
        self._hdr_timer.timeout.connect(self._check_hdr)
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

        # HDR
        self._hdr_mode = 0            # 0 = SDR, 1 = PQ (HDR10/HDR10+/Dolby Vision), 2 = HLG
        self._hdr_checked = False
        self._hdr_enabled = str(self._s.value("hdrTonemap", "true")).lower() != "false"
        try:
            self._hdr_brightness = float(self._s.value("hdrBrightness", 1.0))
        except (TypeError, ValueError):
            self._hdr_brightness = 1.0
        try:
            self._hdr_saturation = float(self._s.value("hdrSaturation", 1.0))
        except (TypeError, ValueError):
            self._hdr_saturation = 1.0
        self._hdr_dynamic = str(self._s.value("hdrDynamic", "true")).lower() != "false"
        try:
            self._hdr_toe = float(self._s.value("hdrToe", 0.85))
        except (TypeError, ValueError):
            self._hdr_toe = 0.85
        self._tone_url = self._write_shader("tonemap", TONEMAP_QSB)
        self._stats_url = self._write_shader("stats", STATS_QSB)
        self._probe_url = self._write_shader("probe", PROBE_QSB)
        self._clean_url = self._write_shader("clean", CLEAN_QSB)
        # calibrage : mesuré au démarrage sur la carte graphique de l'utilisateur
        self._cal_sink = None
        self._cal_frame = None
        self._cal_status = "en cours"      # en cours | ok | impossible (pour la vidéo en cours)
        self._cal_ok = {}                  # "p010" / "sw" -> bool, mesuré au démarrage
        self._cal_queue = []
        self._hdr_kind, self._hdr_scale, self._hdr_gamut2020 = 0, 1.0, 1
        self._hdr_ml = QT_PQ_ML
        self._hdr_tex_float = True
        self._hdr_path = ""
        self._measuring = False
        self._measure_ctx = None
        self._measure_frame = None
        self._measuring = False
        self._measure_ctx = None
        self._measure_frame = None

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
        self.player.setVideoSink(sink)
        sink.subtitleTextChanged.connect(self._on_embedded_sub)

    def _check_hdr(self):
        if self._display is None or self._hdr_checked or self._measuring:
            self._hdr_timer.stop()
            return
        frame = self._display.videoFrame()
        if frame.isValid():
            self._hdr_checked = True
            self._hdr_timer.stop()
            sf = frame.surfaceFormat()
            tr = _ev(sf.colorTransfer())
            mode = 1 if tr == _ev(QVideoFrameFormat.ColorTransfer_ST2084) else \
                   2 if tr == _ev(QVideoFrameFormat.ColorTransfer_STD_B67) else 0
            pf = _ev(sf.pixelFormat())
            hw = pf in (_ev(QVideoFrameFormat.PixelFormat.Format_P010), _ev(QVideoFrameFormat.PixelFormat.Format_P016))
            self._hdr_path = ""
            if mode == 1 and hw:
                # Qt a déjà converti l'image : on annule sa conversion (luminosité de mastering du fichier)
                ml = sf.maxLuminance()
                if ml is None or ml <= 200:
                    ml = 10000.0
                self._hdr_kind, self._hdr_scale, self._hdr_gamut2020 = 2, nits_to_pq(ml), 1
                self._hdr_ml = QT_PQ_ML
                self._hdr_path = "p010"
                if True:
                    QTimer.singleShot(0, lambda fs=sf.frameSize(), m=sf.maxLuminance(): self._measure_main(fs, m, False))
            elif mode == 2 and hw:
                self._hdr_kind, self._hdr_gamut2020 = 3, 1
                self._hdr_scale, self._hdr_ml = QT_HLG_DEFAULT
                self._hdr_path = "p010hlg"
                if True:
                    QTimer.singleShot(0, lambda fs=sf.frameSize(), m=sf.maxLuminance(): self._measure_main(fs, m, True))
            elif mode and not hw:
                self._hdr_kind, self._hdr_scale, self._hdr_gamut2020 = 0, 1.0, 1
                self._hdr_path = "sw"
            self._hdr_tex_float = True
            log(f"vidéo HDR : mode={mode} format={sf.pixelFormat()} mastering={sf.maxLuminance()} nits "
                f"-> chemin={self._hdr_path or 'aucun'} calibré={self._cal_ok.get(self._hdr_path)}")
            self._hdr_mode = mode
            self.hdrChanged.emit()

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
            dev = QMediaDevices.defaultAudioOutput()
            if dev.isNull():
                log("amplification : aucune sortie audio par défaut")
                return False
            fmt = QAudioFormat()
            fmt.setSampleRate(48000)
            fmt.setChannelCount(2)
            fmt.setSampleFormat(QAudioFormat.Int16)
            if not dev.isFormatSupported(fmt):
                pref = dev.preferredFormat()
                fmt.setSampleRate(pref.sampleRate() or 48000)
                fmt.setChannelCount(min(2, max(1, pref.channelCount())) if pref.channelCount() else 2)
                for sf in (QAudioFormat.Int16, QAudioFormat.Float, QAudioFormat.Int32):
                    fmt.setSampleFormat(sf)
                    if dev.isFormatSupported(fmt):
                        break
                else:
                    fmt = pref
            sf = _ev(fmt.sampleFormat())
            kind = {_ev(QAudioFormat.Int16): "h", _ev(QAudioFormat.Int32): "i", _ev(QAudioFormat.Float): "f"}.get(sf)
            if kind is None:
                log(f"amplification : format audio non géré ({fmt.sampleFormat()})")
                return False
            bps = fmt.bytesPerFrame() * fmt.sampleRate()
            sink = QAudioSink(dev, fmt, self)
            sink.setBufferSize(int(bps * 0.15))   # ~150 ms
            io = sink.start()
            if io is None or _ev(sink.error()) != AUDIO_NO_ERROR:
                log(f"amplification : la sortie audio refuse de démarrer ({sink.error()}) format={fmt}")
                sink.deleteLater()
                return False
            out = QAudioBufferOutput(fmt, self)
            out.audioBufferReceived.connect(self._on_audio_buffer)
            self.player.setAudioBufferOutput(out)
            self._boost = {"sink": sink, "io": io, "out": out, "pending": bytearray(), "primed": False,
                           "kind": kind, "bps": bps, "frame": fmt.bytesPerFrame()}
            sink.stateChanged.connect(self._on_boost_state)
            if self.player.playbackState() != QMediaPlayer.PlayingState:
                sink.suspend()
            log(f"amplification active : {dev.description()} · {fmt.sampleRate()} Hz · {kind}")
            return True
        except Exception as e:  # noqa: BLE001
            log(f"amplification indisponible : {e!r}")
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
        if b and _ev(state) == AUDIO_STOPPED and _ev(b["sink"].error()) not in (AUDIO_NO_ERROR, AUDIO_UNDERRUN):
            log(f"amplification arrêtée : {b['sink'].error()}")
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
        kind = b["kind"]
        size = array(kind).itemsize
        samples = array(kind)
        samples.frombytes(data[: len(data) - len(data) % size])
        if kind == "f":
            samples = array("f", [1.0 if v > 1.0 else -1.0 if v < -1.0 else v
                                  for v in [x * g for x in samples]])
        else:
            hi = 32767 if kind == "h" else 2147483647
            lo = -hi - 1
            samples = array(kind, [hi if v > hi else lo if v < lo else v
                                   for v in [int(x * g) for x in samples]])
        pend = b["pending"]
        pend += samples.tobytes()
        bps, frame = b["bps"], b["frame"]
        max_pending = bps // 3                   # ~330 ms au maximum
        if len(pend) > max_pending:
            cut = len(pend) - max_pending
            del pend[: cut - cut % frame]
        if not b["primed"]:
            if len(pend) < bps // 25:            # on attend ~40 ms avant de démarrer
                return
            b["primed"] = True
        free = b["sink"].bytesFree()
        if free > 0 and pend:
            n = min(free, len(pend))
            n -= n % frame
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
        if self._clearing_sub:
            return
        if text and self._display is not None:
            # on efface le texte du moteur (sinon il le dessinerait aussi) : Nova le dessine lui-même
            self._clearing_sub = True
            self._display.setSubtitleText("")
            self._clearing_sub = False
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
        self._hdr_checked = False
        self._hdr_timer.start()
        if self._hdr_mode:
            self._hdr_mode = 0
            self.hdrChanged.emit()
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
    def _capture_path(self, name, pos):
        folder = Path(QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)) / APP_NAME
        folder.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', "_", name)[:80] or "capture"
        base = f"{safe}_{fmt_time(pos, '-')}"
        f = folder / f"{base}.png"
        i = 2
        while f.exists():
            f = folder / f"{base}_{i}.png"
            i += 1
        return f

    @Slot("QVariant", str, int, float, float, float, float, float, result=str)
    def saveCaptureImage(self, img, name, pos, cx, cy, cw, ch, item_w):
        try:
            if not isinstance(img, QImage):
                img = QImage(img)
            if img.isNull():
                return ""
            if cw > 0 and ch > 0 and item_w > 0:
                k = img.width() / item_w            # écran haute densité : l'image peut être plus grande
                img = img.copy(round(cx * k), round(cy * k), round(cw * k), round(ch * k))
            f = self._capture_path(name, pos)
            return str(f) if img.save(str(f)) else ""
        except Exception as e:  # noqa: BLE001
            log(f"capture impossible : {e!r}")
            return ""

    @Slot(str, int, result=str)
    def screenshot(self, name, pos):
        try:
            if self._display is None:
                return ""
            frame = self._display.videoFrame()
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

    # ================================================================ HDR
    def _write_shader(self, name, chunks):
        try:
            root = os.environ.get("LOCALAPPDATA") or os.path.join(Path.home(), ".local", "share")
            d = Path(root) / "Nova" / "app"
            d.mkdir(parents=True, exist_ok=True)
            data = base64.b64decode("".join(chunks))
            f = d / ("%s-%s.frag.qsb" % (name, hashlib.md5(data).hexdigest()[:8]))
            if not f.exists():
                f.write_bytes(data)
            return QUrl.fromLocalFile(str(f)).toString()
        except Exception as e:  # noqa: BLE001
            log(f"shader HDR indisponible : {e!r}")
            return ""

    def _get_hdr_mode(self):
        return self._hdr_mode

    def _get_hdr_enabled(self):
        return self._hdr_enabled and bool(self._tone_url) and self._hdr_supported()

    def _hdr_supported(self):
        # P010 : validé par la mesure faite au début de la vidéo ; logiciel : validé au démarrage
        return bool(self._hdr_path) and self._cal_ok.get(self._hdr_path, False)

    def _get_hdr_brightness(self):
        return self._hdr_brightness

    def _get_tone_url(self):
        return self._tone_url

    def _get_stats_url(self):
        return self._stats_url

    def _get_clean_url(self):
        return self._clean_url

    def _get_hdr_saturation(self):
        return self._hdr_saturation

    def _get_hdr_dynamic(self):
        return self._hdr_dynamic

    hdrMode = Property(int, _get_hdr_mode, notify=hdrChanged)
    hdrEnabled = Property(bool, _get_hdr_enabled, notify=hdrChanged)
    hdrBrightness = Property(float, _get_hdr_brightness, notify=hdrChanged)
    toneShader = Property(str, _get_tone_url, constant=True)
    statsShader = Property(str, _get_stats_url, constant=True)
    cleanShader = Property(str, _get_clean_url, constant=True)
    hdrSaturation = Property(float, _get_hdr_saturation, notify=hdrChanged)
    hdrDynamic = Property(bool, _get_hdr_dynamic, notify=hdrChanged)

    # --- calibrage automatique
    @Slot(QObject)
    def setCalibrationSink(self, sink):
        self._cal_sink = sink

    @Slot()
    def startCalibration(self):
        if self._cal_sink is None or not self._probe_url:
            log("calibrage HDR impossible (pas de shader)")
            self.hdrChanged.emit()
            return
        # Seul le décodage logiciel est testé au démarrage : Qt garde pour toute la session la formule
        # de la 1re image P010 qu'il voit. C'est donc la vidéo elle-même qui la choisit, puis on la mesure.
        self._cal_queue = ["sw"]
        self._next_calibration()

    def _next_calibration(self):
        while self._cal_queue:
            kind = self._cal_queue[0]
            try:
                self._cal_frame = make_calibration_frame(kind)
            except Exception as e:  # noqa: BLE001
                self._cal_frame = None
                log(f"calibrage HDR ({kind}) : image de test impossible ({e!r})")
            if self._cal_frame is not None:
                self._cal_sink.setVideoFrame(self._cal_frame)
                self.calibrationRequest.emit(True)
                return
            self._cal_ok[kind] = False
            self._cal_queue.pop(0)
        # terminé
        self._cal_frame = None
        if self._cal_sink is not None:
            self._cal_sink.setVideoFrame(QVideoFrame())
        self._cal_status = "ok" if any(self._cal_ok.values()) else "impossible"
        self.hdrChanged.emit()

    @Slot("QVariant", bool)
    def calibrationResult(self, img, tex_float):
        kind = self._cal_queue.pop(0) if self._cal_queue else "?"
        raw = []
        try:
            if not isinstance(img, QImage):
                img = QImage(img)
            zone = CAL_W // len(CAL_GRAYS)
            for i in range(len(CAL_GRAYS)):
                v = round(probe_value(img.pixelColor(i * zone + zone // 2, CAL_H // 2)), 4)
                raw.append((v, v, v))
        except Exception as e:  # noqa: BLE001
            log(f"calibrage HDR : lecture impossible ({e!r})")
        ok, expected = calibration_matches(kind, raw) if len(raw) == len(CAL_GRAYS) else (False, [])
        self._cal_ok[kind] = ok
        log(f"calibrage HDR [{kind}] mesuré={raw} attendu={[round(x, 3) for x in expected]} -> {'OK' if ok else 'ÉCART'}")
        self._next_calibration()

    # --- mesure sur l'affichage principal (au début de chaque vidéo HDR décodée par la carte graphique)
    def _measure_main(self, size, max_lum, hlg=False):
        if self._display is None or self._measuring:
            return
        self._measure_hlg = hlg
        try:
            frame = make_sized_calibration_frame(size.width(), size.height(), max_lum, hlg)
        except Exception as e:  # noqa: BLE001
            log(f"mesure HDR impossible : {e!r}")
            frame = None
        if frame is None:
            return
        was_playing = self.player.playbackState() == QMediaPlayer.PlayingState
        self._measure_ctx = (self.player.position(), was_playing)
        self._measuring = True
        self.hdrChanged.emit()
        self.player.pause()
        self._measure_frame = frame
        self._display.setVideoFrame(frame)
        self.mainProbeRequest.emit()

    @Slot("QVariant")
    def mainProbeResult(self, img):
        measured = []
        try:
            if not isinstance(img, QImage):
                img = QImage(img)
            zone = CAL_W // len(CAL_GRAYS)
            for i in range(len(CAL_GRAYS)):
                measured.append(probe_value(img.pixelColor(i * zone + zone // 2, CAL_H // 2)))
        except Exception as e:  # noqa: BLE001
            log(f"mesure HDR : lecture impossible ({e!r})")
        if len(measured) == len(CAL_GRAYS):
            # Qt peut appliquer sa formule PQ ou HLG (il garde celle de la 1re vidéo) : on teste les deux
            mw_pq, ml_pq, rms_pq = solve_pq(measured)
            mw_h, ml_h, rms_h = solve_hlg(measured)
            if rms_pq <= rms_h:
                curve, mw, ml, rms, kind = "PQ", mw_pq, ml_pq, rms_pq, 2
            else:
                curve, mw, ml, rms, kind = "HLG", mw_h, ml_h, rms_h, 3
            ok = rms < 0.02
            log(f"mesure HDR sur l'affichage : gris={[round(m, 4) for m in measured]} -> formule Qt {curve} "
                f"mw={mw:.3f} ml={ml:.3f} (écart {rms:.3f}, signal {'HLG' if self._hdr_mode == 2 else 'PQ'}) {'OK' if ok else 'REFUSÉ'}")
            self._cal_ok[self._hdr_path] = ok
            if ok:
                self._hdr_scale, self._hdr_ml, self._hdr_kind = mw, ml, kind
                if (kind == 2) != (self._hdr_mode == 1):
                    # Qt applique la formule de la vidéo HDR précédente (autre type) : rendu un peu moins fidèle
                    QTimer.singleShot(1500, self.hdrMismatch.emit)
            else:
                self._hdr_path = ""          # incohérent : on laisse l'image de Qt telle quelle
        self._measure_frame = None
        self._measuring = False
        pos, was_playing = self._measure_ctx or (0, True)
        self._measure_ctx = None
        self._hdr_checked = True
        self.player.setPosition(pos)          # réaffiche l'image de la vidéo
        if was_playing:
            self.player.play()
        self.hdrChanged.emit()

    def _get_measuring(self):
        return self._measuring

    hdrMeasuring = Property(bool, _get_measuring, notify=hdrChanged)

    def _get_probe_url(self):
        return self._probe_url

    def _get_kind(self):
        return self._hdr_kind

    def _get_scale(self):
        return self._hdr_scale

    def _get_gamut(self):
        return self._hdr_gamut2020

    def _get_ml(self):
        return self._hdr_ml

    def _get_tex_float(self):
        return self._hdr_tex_float

    def _get_cal_status(self):
        if self._cal_queue or self._measuring:
            return "en cours"
        if self._hdr_mode and not self._hdr_supported():
            return "impossible"
        return "ok" if self._cal_ok else "en cours"

    probeShader = Property(str, _get_probe_url, constant=True)
    hdrKind = Property(int, _get_kind, notify=hdrChanged)
    hdrScale = Property(float, _get_scale, notify=hdrChanged)
    hdrGamut2020 = Property(int, _get_gamut, notify=hdrChanged)
    hdrMl = Property(float, _get_ml, notify=hdrChanged)
    hdrTexFloat = Property(bool, _get_tex_float, notify=hdrChanged)
    hdrCalibration = Property(str, _get_cal_status, notify=hdrChanged)

    @Slot(float)
    def setHdrSaturation(self, v):
        self._hdr_saturation = max(0.5, min(1.5, float(v)))
        self._s.setValue("hdrSaturation", self._hdr_saturation)
        self.hdrChanged.emit()

    def _get_toe(self):
        return self._hdr_toe

    hdrToe = Property(float, _get_toe, notify=hdrChanged)

    @Slot(float)
    def setHdrToe(self, v):
        self._hdr_toe = max(0.6, min(1.0, float(v)))
        self._s.setValue("hdrToe", self._hdr_toe)
        self.hdrChanged.emit()

    @Slot(bool)
    def setHdrDynamic(self, on):
        self._hdr_dynamic = bool(on)
        self._s.setValue("hdrDynamic", "true" if on else "false")
        self.hdrChanged.emit()

    @Slot(bool)
    def setHdrEnabled(self, on):
        self._hdr_enabled = bool(on)
        self._s.setValue("hdrTonemap", "true" if on else "false")
        self.hdrChanged.emit()

    @Slot(float)
    def setHdrBrightness(self, v):
        self._hdr_brightness = max(0.4, min(2.5, float(v)))
        self._s.setValue("hdrBrightness", self._hdr_brightness)
        self.hdrChanged.emit()

    @Slot(result="QPointF")
    def cursorPos(self):
        """Position réelle de la souris à l'écran (ne dépend pas du survol)."""
        return QPointF(QCursor.pos())

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
    property bool menuOpen: speedPop.opened || trackPop.opened || audioPop.opened || hdrPop.opened || helpPop.opened || subPop.opened
    property bool showBars: hasMedia && (controlsVisible || !playing)
    property int durTick: 0
    property bool hdrActive: backend.hdrMode > 0 && backend.hdrEnabled
    property bool hdrShown: false
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
        var name = currentName, pos = player.position
        function done(p) {
            if (p !== "") { flash.show("camera"); toast.show("Capture enregistrée dans Images/Nova") }
            else toast.show("Capture impossible")
        }
        if (hdrActive) {
            // vidéo HDR : on enregistre l'image telle qu'elle est affichée (après la conversion de Nova)
            var cr = videoOut.contentRect
            toneFx.grabToImage(function(r) { done(backend.saveCaptureImage(r.image, name, pos, cr.x, cr.y, cr.width, cr.height, toneFx.width)) })
        } else {
            done(backend.screenshot(name, pos))
        }
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
        if (backend.hdrMode === 1) parts.push("HDR")
        else if (backend.hdrMode === 2) parts.push("HDR · HLG")
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
        function onHdrMismatch() { toast.show("HDR10 et HLG dans la même session : relance Nova pour un rendu parfait", 6000) }
        function onHdrChanged() {
            if (backend.hdrMode > 0 && !win.hdrShown) {
                win.hdrShown = true
                toast.show(backend.hdrEnabled ? "Vidéo HDR détectée · image adaptée à ton écran" : "Vidéo HDR détectée · conversion désactivée", 3000)
            }
            if (backend.hdrMode === 0) win.hdrShown = false
        }
    }

    Timer {
        id: hideTimer
        interval: 2600
        onTriggered: {
            var c = backend.cursorPos()
            var pb = bottomBar.mapFromGlobal(c.x, c.y)
            var pt = topBar.mapFromGlobal(c.x, c.y)
            var overBar = (pb.x >= 0 && pb.x <= bottomBar.width && pb.y >= -12 && pb.y <= bottomBar.height)
                       || (pt.x >= 0 && pt.x <= topBar.width && pt.y >= 0 && pt.y <= topBar.height)
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

        // ---------- calibrage HDR (invisible, caché sous l'interface) ----------
        Item {
            id: calib
            x: 0; y: 0; width: 96; height: 16
            property bool texFloat: true
            VideoOutput {
                id: calOut
                anchors.fill: parent
                fillMode: VideoOutput.Stretch
                Component.onCompleted: backend.setCalibrationSink(videoSink)
            }
            ShaderEffectSource {
                id: calTex
                anchors.fill: parent
                sourceItem: calOut
                hideSource: true
                live: true
                visible: false
                smooth: false
                textureSize: Qt.size(96, 16)
                format: calib.texFloat ? ShaderEffectSource.RGBA16F : ShaderEffectSource.RGBA8
            }
            ShaderEffect {
                id: probe
                anchors.fill: parent
                property variant source: calTex
                fragmentShader: backend.probeShader
            }
            Timer {
                id: calTimer
                interval: 450
                onTriggered: probe.grabToImage(function(r) { backend.calibrationResult(r.image, calib.texFloat) }, Qt.size(96, 16))
            }
            Connections {
                target: backend
                function onCalibrationRequest(texFloat) { calib.texFloat = texFloat; calTimer.restart() }
            }
            Timer { interval: 150; running: true; onTriggered: backend.startCalibration() }
        }

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
            // conversion HDR -> écran normal (tone mapping sur la carte graphique)
            // 1) image brute de Qt, pixel par pixel (sans flou, pour ne pas étaler les pixels invalides)
            ShaderEffectSource {
                id: rawTex
                anchors.fill: videoOut
                sourceItem: (win.hdrActive || backend.hdrMeasuring) ? videoOut : null
                hideSource: win.hdrActive || backend.hdrMeasuring
                live: true
                visible: false
                smooth: false
                format: backend.hdrTexFloat ? ShaderEffectSource.RGBA16F : ShaderEffectSource.RGBA8
            }
            // 2) réparation des pixels invalides des zones sombres (comme VLC)
            ShaderEffect {
                id: cleanFx
                anchors.fill: videoOut
                visible: win.hdrActive || backend.hdrMeasuring
                property variant source: rawTex
                property point texel: Qt.point(1 / Math.max(1, width * Screen.devicePixelRatio),
                                               1 / Math.max(1, height * Screen.devicePixelRatio))
                fragmentShader: backend.cleanShader
            }
            ShaderEffectSource {
                id: videoTex
                anchors.fill: videoOut
                sourceItem: (win.hdrActive || backend.hdrMeasuring) ? cleanFx : null
                hideSource: true
                live: true
                visible: false
                smooth: true
                mipmap: true
                // format choisi par le calibrage automatique
                format: backend.hdrTexFloat ? ShaderEffectSource.RGBA16F : ShaderEffectSource.RGBA8
            }
            // mesure du réglage réel de Qt sur l'affichage principal
            ShaderEffect {
                id: mainProbe
                x: 0; y: 0; width: 96; height: 16
                z: -1
                property variant source: videoTex
                fragmentShader: backend.probeShader
            }
            Timer {
                id: mainProbeTimer
                interval: 400
                onTriggered: mainProbe.grabToImage(function(r) { backend.mainProbeResult(r.image) }, Qt.size(96, 16))
            }
            Connections {
                target: backend
                function onMainProbeRequest() { mainProbeTimer.restart() }
            }
            // mesure de la luminosité de la scène (1 pixel, lissée dans le temps)
            ShaderEffect {
                id: statsFx
                width: 1; height: 1
                property variant source: videoTex
                property variant prev: statsSrc
                property real mode: backend.hdrMode
                property real rate: 0.05
                property real kind: backend.hdrKind
                property real kscale: backend.hdrScale
                property real gamut2020: backend.hdrGamut2020
                property real kml: backend.hdrMl
                fragmentShader: backend.statsShader
            }
            ShaderEffectSource {
                id: statsSrc
                width: 1; height: 1
                visible: false
                sourceItem: (win.hdrActive && backend.hdrDynamic) ? statsFx : null
                hideSource: true
                recursive: true
                live: true
                textureSize: Qt.size(1, 1)
                format: ShaderEffectSource.RGBA16F
            }
            ShaderEffect {
                id: toneFx
                anchors.fill: videoOut
                visible: win.hdrActive
                property variant source: videoTex
                property variant stats: statsSrc
                property real mode: backend.hdrMode
                property real brightness: backend.hdrBrightness
                property real saturation: backend.hdrSaturation
                property real dynamic: backend.hdrDynamic ? 1 : 0
                property real toe: backend.hdrToe
                property real kind: backend.hdrKind
                property real kscale: backend.hdrScale
                property real gamut2020: backend.hdrGamut2020
                property real kml: backend.hdrMl
                fragmentShader: backend.toneShader
            }

            // cache noir pendant la mesure HDR (une fraction de seconde)
            Rectangle {
                anchors.fill: parent
                color: "black"
                visible: backend.hdrMeasuring
                Text { anchors.centerIn: parent; text: "Réglage de l'image HDR…"; color: theme.muted; font.pixelSize: 14 }
            }

            // détecte la souris partout sur la scène, même au-dessus des boutons
            HoverHandler {
                id: stageHover
                property real lastX: -1
                property real lastY: -1
                // Qt renvoie un « survol » à chaque image de la vidéo même si la souris
                // ne bouge pas : on ne réagit qu'à un vrai déplacement
                onPointChanged: {
                    var p = point.scenePosition
                    if (Math.abs(p.x - lastX) + Math.abs(p.y - lastY) < 3) return
                    lastX = p.x; lastY = p.y
                    if (win.hasMedia) win.poke()
                }
            }

            MouseArea {
                id: stageMouse
                anchors.fill: parent
                enabled: win.hasMedia
                hoverEnabled: true
                // le curseur ne se cache qu'en plein écran, jamais en mode fenêtré
                cursorShape: (win.showBars || !win.isFull) ? Qt.ArrowCursor : Qt.BlankCursor
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
                id: topBar
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
                        // ---- piste audio
                        IconBtn {
                            id: audioBtn
                            anchors.verticalCenter: parent.verticalCenter
                            icon: "audio"; tip: "Piste audio"
                            onClicked: audioPop.open()
                            DarkPopup {
                                id: audioPop
                                x: Math.min(0, (parent.width - width) / 2)
                                y: -height - 12
                                contentItem: Column {
                                    MenuHeader { text: "PISTE AUDIO" }
                                    Repeater {
                                        model: player.audioTracks
                                        delegate: MenuRow {
                                            required property var modelData
                                            required property int index
                                            text: win.trackName(modelData, index)
                                            checked: player.activeAudioTrack === index
                                            onClicked: { player.activeAudioTrack = index; backend.flushAudio(); audioPop.close() }
                                        }
                                    }
                                    Text {
                                        visible: player.audioTracks.length === 0
                                        text: "Aucune piste"; color: theme.muted; font.pixelSize: 13
                                        leftPadding: 12; topPadding: 4; bottomPadding: 6
                                    }
                                }
                            }
                        }
                        // ---- sous-titres
                        IconBtn {
                            id: trackBtn
                            anchors.verticalCenter: parent.verticalCenter
                            icon: "subs"; tip: "Sous-titres (C pour le style)"
                            active: backend.subtitleSource === "external" || (backend.subtitleSource === "embedded" && player.activeSubtitleTrack >= 0)
                            onClicked: trackPop.open()
                            DarkPopup {
                                id: trackPop
                                x: Math.min(0, (parent.width - width) / 2)
                                y: -height - 12
                                contentItem: Column {
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
                                    MenuRow { icon: "brush"; text: "Personnaliser l'apparence…"; onClicked: { trackPop.close(); subPop.open() } }
                                }
                            }
                        }
                        // ---- HDR (seulement pour les vidéos HDR)
                        Rectangle {
                            id: hdrPill
                            visible: backend.hdrMode > 0
                            anchors.verticalCenter: parent.verticalCenter
                            width: hdrText.implicitWidth + 20; height: 28; radius: 8
                            color: hdma.containsMouse ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.08)
                            border.width: 1
                            border.color: backend.hdrEnabled ? theme.accent : Qt.rgba(1, 1, 1, 0.2)
                            Text {
                                id: hdrText
                                anchors.centerIn: parent
                                text: "HDR"
                                color: backend.hdrEnabled ? "white" : theme.muted
                                font.pixelSize: 12; font.weight: Font.Black; font.letterSpacing: 1
                            }
                            MouseArea { id: hdma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: hdrPop.open() }
                            DarkPopup {
                                id: hdrPop
                                x: Math.min(0, (parent.width - width) / 2)
                                y: -height - 12
                                contentItem: Column {
                                    MenuHeader { text: backend.hdrMode === 2 ? "IMAGE HDR (HLG)" : "IMAGE HDR" }
                                    Text {
                                        visible: true
                                        text: backend.hdrCalibration === "ok" ? "Calibré pour ta carte graphique ✓"
                                              : backend.hdrCalibration === "impossible" ? "Calibrage impossible : image d'origine affichée"
                                              : "Calibrage en cours…"
                                        color: backend.hdrCalibration === "impossible" ? theme.accent2 : theme.muted
                                        font.pixelSize: 11; leftPadding: 12; bottomPadding: 4
                                    }
                                    MenuRow {
                                        width: 300
                                        visible: true
                                        icon: "image"
                                        text: "Adapter le HDR à mon écran"
                                        checked: backend.hdrEnabled
                                        onClicked: backend.setHdrEnabled(!backend.hdrEnabled)
                                    }
                                    MenuRow {
                                        width: 300
                                        visible: backend.hdrEnabled
                                        icon: "brush"
                                        text: "Adaptation dynamique (par scène)"
                                        checked: backend.hdrDynamic
                                        onClicked: backend.setHdrDynamic(!backend.hdrDynamic)
                                    }
                                    Text { visible: backend.hdrEnabled; text: "Couleurs"; color: theme.muted; font.pixelSize: 12; leftPadding: 12; topPadding: 4 }
                                    Row {
                                        visible: backend.hdrEnabled
                                        leftPadding: 12; topPadding: 4; bottomPadding: 4
                                        spacing: 6
                                        Chip { text: "Douces"; selected: backend.hdrSaturation < 0.95; onClicked: backend.setHdrSaturation(0.85) }
                                        Chip { text: "Normales"; selected: backend.hdrSaturation >= 0.95 && backend.hdrSaturation <= 1.05; onClicked: backend.setHdrSaturation(1.0) }
                                        Chip { text: "Vives"; selected: backend.hdrSaturation > 1.05; onClicked: backend.setHdrSaturation(1.15) }
                                    }
                                    Text { visible: backend.hdrEnabled; text: "Ombres"; color: theme.muted; font.pixelSize: 12; leftPadding: 12; topPadding: 4 }
                                    Row {
                                        visible: backend.hdrEnabled
                                        leftPadding: 12; topPadding: 4; bottomPadding: 4
                                        spacing: 6
                                        Chip { text: "Profondes"; selected: backend.hdrToe > 0.95; onClicked: backend.setHdrToe(1.0) }
                                        Chip { text: "Détaillées"; selected: backend.hdrToe <= 0.95 && backend.hdrToe > 0.8; onClicked: backend.setHdrToe(0.85) }
                                        Chip { text: "Très claires"; selected: backend.hdrToe <= 0.8; onClicked: backend.setHdrToe(0.75) }
                                    }
                                    Text { visible: backend.hdrEnabled; text: "Luminosité"; color: theme.muted; font.pixelSize: 12; leftPadding: 12; topPadding: 4 }
                                    Row {
                                        visible: backend.hdrEnabled
                                        leftPadding: 12; topPadding: 4; bottomPadding: 4
                                        spacing: 6
                                        Chip { text: "Plus sombre"; selected: backend.hdrBrightness < 0.9; onClicked: backend.setHdrBrightness(0.75) }
                                        Chip { text: "Normal"; selected: backend.hdrBrightness >= 0.9 && backend.hdrBrightness <= 1.1; onClicked: backend.setHdrBrightness(1.0) }
                                        Chip { text: "Plus clair"; selected: backend.hdrBrightness > 1.1; onClicked: backend.setHdrBrightness(1.4) }
                                    }
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
    # moins de pauses du ramasse-miettes Python pendant la lecture
    gc.collect()
    gc.freeze()
    gc.set_threshold(20000, 50, 100)
    code = app.exec()
    backend.player.stop()
    return code


if __name__ == "__main__":
    sys.exit(main())
