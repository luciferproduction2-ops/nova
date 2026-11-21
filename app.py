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

from PySide6.QtCore import (QObject, Property, QProcess, QSettings, QSize, QStandardPaths, QTimer,
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
APP_VERSION = 18  # augmenter à chaque mise à jour publiée

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
    "cV6A+Dlmhp9Xv57mvyPYPPc6mueWsFhQM5Gu1mlrTKTxO4JrzeDe3xoWdyZNvCO4lvFOMd5J0m1Km5uPJd2OZOuXo9ge9Gj2fSn7"
    "fgzpv4zNi2dq8+rZWvpcbR59l5Z/kZa+RNtLnm6iPspf1plIU3vJM5i/QN5bTSFpoOdbWV+dZWIboV9B57OY75xjYjvlXSsT0yrv"
    "PBPbDXnQlvPMYK91vol7SZAH5c4le59P9Z/B8claO95uIk3tCd7J2gF57zCFpIGcd7B2XMjaAba8kNVxMWsH2PVilncpawfY+FLW"
    "jnebuGcEeVDuEmrHu6n+d7L6L6f6If9yza+K5FfL2ZrvOOb/x7PvJzDfO5H52BvY9zey7yvY95PY95OZnDcx+gD7fgr57Ur+OxSa"
    "372XpUG/GzW//Zi2nrxNK3+Xlr5bk/eglv+wlv9dLf09Lf0zLf0rTb8ntfQ/tfSzWnqO9rsW22vpV2npV2u/G/EaLb2rlra18ntq"
    "+Xtr6ddq6YRWfoGWv6+WdrV0Siuf0/ILWrpPS/dr5Q+Mhc+WrzLRb/3zXxP9zz//NZHnappLwN+uYePxfSb6qH/+a6KfqvT7TfRR"
    "hSv4gBngOqEs8AOPeib5QVp7fIDqA3/+IKvvQyb6uMIpXWciTc27H2bxB/KuN4Wkwbi5no3/G6jdMP5voPwPUz6s/W42w3f2byHa"
    "zWzdJ+9Tm5in5N5KciEPxtqt1I7b2H7j41Tfx2ndf7spxCfZuv8Oyr+DrVfuNHGsqv3G/5lI+xSt+yH9CdgXUNlPsLKfprJqzfwZ"
    "E2mgF4z3zzD73mNi7FJz870m/pbXPWyN+Dmi3cvK3Wdi7FDl7jeR7z62Dv+8ifHIP9/UyjxgIu2LbA/wJRPp54tgrf5lE2V9idoA"
    "MenLtLYGOQ+ZuG55kMn+ionnaw+xdnyVaF9hfF8zUfevkmyIf19jbXhEa8M3tTZ8y0Tao6wN3zbx982+xfYb3zFR1repHoib32Ft"
    "eIza8F0m+3ETfzftMSoDsfdxpsv3TYzHag31A7b/+j7j+6HG9yO2//oh0/vHJsr4ESv7ExPnBLXf+qmJfD8hnSDe/5TZ6+cmzgEq"
    "/QsT50y1F/uliTy/oPIwPwBNYbd+Q+U5vuu3JtIVRvB3JtJUmT9QGY4b+6OJdNW2P5lY7o9Mtz9ruv3FRL4/k24wV/2F7Yf/auK6"
    "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"
    "sBCGcvZi20s2nUFGRbSoNSk73+20JC3Z/Wyt12oNGvBL5dimteVhDmuJq1rSvN5mYz8VblPU2NbapbNkIpbbQfuWHhPXx7z6kkmE"
    "C+mN1BfaGAYqY316nznNfTYi1/sQLTTtoZjvCbxss5VQRjALucls1sk4jpMuZAquk03jSVWvvcBJul46K4N4NldIF7xCxkmrkyyZ"
    "77h5OuNK551U3iu4hZTr0iygxsMCJ5nJ5zJ4mpTxnFzGLZAIN+mmvDxOcm4+k3K8HE0gULnjyELZXDqTyWdTBbVZC4l2cl4el2wF"
    "z82k3Gwu59HhCqro5HGeyuecVAaOXrJuKuP506CbdN18DgTk0tmMWjDCfOP3iR3a8FGg8XPX+f0Go5Z7aNRYG8iGPRPXpLgQDK8f"
    "BrJNhy1TdVqT1zfCmjzwlXgdDqUpsE7Vp7sB7LCgBhOnkwUv6zr5VBbW0Rnq/Q7BgBkzFzYmqsumHuKSVRWSsqpMxnVU70ecCXfH"
    "xfTGRTCT4YJIW0K3nK5ewNmJLeKmM0Gt07VsP65TrfWMmG3azTQhPacx0YTPa9hZ8qpifZXrxfFhnjI78ZVrxcFGPOMlC+CdsINV"
    "Dg4Po2QmBBo8RvRg0ZTNua6TyTr5VDrt5PJONlXI4gmcjChOJp/KuelCwc07uUIql/U8J0dOw5c++Kh3WWV4Og8geyk+VoZ9Z2rU"
    "SmPDjVUq3VhVc6bhdCRoZGK0eIKiDhVrq5dUeerwinacqsIt1C/LhvYPa/Fw3V5g10er1cYquSBWUlFerz2VCCb2tfB8MuLxFvVJ"
    "vTKsPQr17DIcVwyPDBxaKw7LZ9TJySm2N4Bcv1jofN+V5/v9ttfmfL9cYU83Q3OS54+98iDuFrx4uWLPs3NJp5c9qQlk1eSRfibp"
    "wA48I4/cVV/hA075/BS2CsCAR9/koPR0OFIDOcgDHdwU1C81cXMRWsDj2mzSy6fcfCad9xwvAxOj9FKtPn8v6Nc3hI8Lo57O1jTW"
    "Kmg1JB/V6jmekrJgKDnVaw8lJxPNfCm76EY+H6662pNfZPYimBe0Yk5FS/YimdPRkiOZg7Aajxdde75d9GArWZSPWYrp8GqUPYv2"
    "Wh6sD1bHGpWxCRYY10VVCS0quq2Da3AnJSq2tgm9WS30akuLohddLN+2zkL7Ol2ndaUueEUx1aKg17ZaN9Wh3nSbeuWtlnSLgtn2"
    "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"
)
STATS_QSB = (
    "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"
)
SDR_QSB = (
    "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"
    "exPxryP6NRJ5sM86Rwb7LOCfLYXiQbtnM9+dS+3o/PVaGp9ZVPZZav91EsvOY+2/nviw99C64d9/iLmq/Hyyp49kzyYfnW/klRz5"
    "KEU+gnefaXqG9zIZ9pwl3+XZvH+TkQcuNOjLjDzwLkbD3c7lBv1+Q/4jhr6bDPoug/4eyzOQc98ssT/6Xv8tEvt0Mt09v02iDPBX"
    "Ul6+gPhvk8E7BYtiEfp7ARvDiyT6QJ07JdJ5ir+LJcbghSxO3i6RD3FyCYsT4L8DchSN5TtYG5dSGzB+l1L5JdTmZSzvgW/13Rb4"
    "9X7am15BdeBfuM+6UgpxlQzus95D5e+RwZn4aolj80nqy/sk8uAdFdgL9LulULqg7rvJHhg/fY/2ASr7ALX7QSnEtazdD1H5h1i7"
    "10mMAX2Pdr1E3oepXaCvkULpgrrXsLofpbo1yiEfk8jTOfFGibwbyFaIrRtlECsfN2LlExQr/h2TxHiE+arumGi+7kRl/j2TIXcz"
    "ye1IZavondItEnXczPrwGfK77sOtEnkXUJ3PSqx3K3tXeJvEufl6krldotxtMnh/dYfE/kCZjv3PSezzHSz27yT+5yJiH+benSwu"
    "Py9xPkIZzMPPs9j/AsX+XSz2vyiRD7H/ZRb7wP+SFIoHY/ol1sZXqA1Nf1ViTtH7tbsl8r7C5sPdbCzukZhz9LnvaxJ5p7E58zXK"
    "o7r9LxN9LdHXsvH5OsWYviu6VyJP3xVB2b0yHP8fZPbcR/boe4RvSOSdSmf0bzG/QNk3pVA80PNN0qvn3LeIvoroq5id36Y40nZ+"
    "RyLvfpYfviPD+eFKZucDhp3flcjTdv6A2Qll35dC/JT0fJ+N1w9pvLTeH5Feve/4sUSe/ul9x08k1v0xjSvk9Z+QvT+gdn7Kyhoi"
    "XPYDZsODEtcFyJ8PyvC7i8W0/i1i61w/rXMDLBf8UiJf7yF/I5H3EJvnv6V53kPlOu/8TiLG6rdM9vdM9ndk2++NtXkp2baE7V8O"
    "Y/v8w9nzEez5SLJ/GVsX/9dYV/9m0P8w1tEnjPKnDFpawTqr7sck2qPj5c8SeX+i+f4wixco+wtg8Wis/sLG6q8S+6jwCRJp/w5M"
    "Yj8VRkEircv+KbHfCqcgkdb7xUck7nlBH9T7B/n7EWr/Yabn30Y/HpXI+wXF/eOsH1D2mBSKB3oeY/14kvUDfPkka0NYQT+eogSr"
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
try:
    import audioop  # module C rapide (inclus dans Python 3.12)
except Exception:  # noqa: BLE001
    audioop = None


def boost_curve(g):
    """Curseur 100 %..300 % -> gain maximal réel (300 % = x10, soit +20 dB)."""
    return 1.0 if g <= 1.0 else g ** 2.1


class Limiter:
    """Amplificateur intelligent : monte fort le son (voix, scènes calmes) et
    abaisse le gain juste avant les pics pour ne jamais saturer.
    Traitement par blocs de 2 ms avec 8 ms d'anticipation."""
    CEIL = 0.93          # plafond (-0,6 dB)
    LOOK = 4             # blocs d'anticipation

    def __init__(self, kind, channels, rate):
        self.kind = kind
        self.width = {"h": 2, "i": 4, "f": 4}[kind]
        self.full = {"h": 32768.0, "i": 2147483648.0, "f": 1.0}[kind]
        self.blk = max(1, rate // 500) * channels * self.width     # 2 ms
        # remontée lente du gain après un pic : ~+8 dB par seconde
        self.up = 10 ** (8.0 / 20 / 500)
        self.reset()

    def reset(self):
        self.inbuf = bytearray()
        self.chunks = []
        self.reqs = []
        self.mins = []
        self.prev = 1000.0   # démarre directement au bon gain

    def _peak(self, chunk):
        if audioop is not None and self.kind != "f":
            return audioop.max(chunk, self.width) / self.full
        a = array(self.kind)
        a.frombytes(chunk)
        return (max(max(a), -min(a)) / self.full) if len(a) else 0.0

    def _apply(self, chunk, g):
        if audioop is not None and self.kind != "f":
            return audioop.mul(chunk, self.width, g)          # écrêtage sûr intégré
        a = array(self.kind)
        a.frombytes(chunk)
        if self.kind == "f":
            return array("f", [min(1.0, max(-1.0, v * g)) for v in a]).tobytes()
        hi = 32767 if self.kind == "h" else 2147483647
        return array(self.kind, [min(hi, max(-hi - 1, int(v * g))) for v in a]).tobytes()

    def process(self, data, target):
        self.inbuf += data
        blk, L = self.blk, self.LOOK
        out = bytearray()
        while len(self.inbuf) >= blk:
            chunk = bytes(self.inbuf[:blk])
            del self.inbuf[:blk]
            pk = self._peak(chunk)
            req = target if pk <= 1e-6 else min(target, self.CEIL / pk)
            req = min(req, self.prev * self.up)           # remontée progressive
            self.prev = req
            self.chunks.append(chunk)
            self.reqs.append(req)
            if len(self.reqs) >= L:
                # minimum sur la fenêtre d'anticipation, puis moyenne glissante :
                # le gain baisse en douceur AVANT le pic, sans clic ni saturation
                self.mins.append(min(self.reqs[-L:]))
                if len(self.mins) > L:
                    del self.mins[0]
                g = sum(self.mins) / len(self.mins)
                c = self.chunks.pop(0)
                del self.reqs[0]
                out += self._apply(c, g)
        return bytes(out)



# ====================================================================== générique
# Détection du générique : on compare la « signature » du son des premières
# minutes de l'épisode avec celle d'un autre épisode du même dossier. La musique
# du générique est identique d'un épisode à l'autre, le reste non.
FP_RATE = 8000             # Hz, mono
FP_WIN = 1600              # fenêtre de 0,2 s
FP_HOP = 400               # une mesure toutes les 0,05 s
FP_SECONDS = 1200          # on analyse les 20 premières minutes
EPISODE_RE = re.compile(r"(s\d{1,2}\s*[ex]\s*\d{1,3}|\b\d{1,2}x\d{1,3}\b|[ée]p(isode)?\s*\.?\s*\d{1,3}|\be\d{1,3}\b)", re.I)


def fp_features(pcm):
    """PCM 16 bits mono 8 kHz -> (octets de signature, masque son présent)."""
    try:
        import audioop as ao
    except Exception:  # noqa: BLE001
        ao = None
    feats = []
    n = (len(pcm) // 2 - FP_WIN) // FP_HOP
    for k in range(max(0, n)):
        f = pcm[k * FP_HOP * 2:(k * FP_HOP + FP_WIN) * 2]
        if ao is not None:
            e0 = ao.rms(f, 2)
            d1 = ao.add(f[2:], ao.mul(f[:-2], 2, -1), 2)
            e1 = ao.rms(d1, 2)
            d2 = ao.add(d1[2:], ao.mul(d1[:-2], 2, -1), 2)
            e2 = ao.rms(d2, 2)
            e3 = ao.rms(ao.ratecv(f, 2, 1, FP_RATE, 800, None)[0], 2)
            z = ao.cross(f, 2)
        else:
            a = array("h"); a.frombytes(f)
            a = a[::4]
            e0 = math.sqrt(sum(v * v for v in a) / len(a))
            d = [a[i + 1] - a[i] for i in range(len(a) - 1)]
            e1 = math.sqrt(sum(v * v for v in d) / len(d))
            dd = [d[i + 1] - d[i] for i in range(len(d) - 1)]
            e2 = math.sqrt(sum(v * v for v in dd) / len(dd))
            e3 = abs(sum(a)) / len(a)
            z = sum(1 for i in range(len(a) - 1) if (a[i] < 0) != (a[i + 1] < 0))
        feats.append((e0, e1, e2, e3, z, e1 / (e0 + 1.0), e3 / (e0 + 1.0), e2 / (e1 + 1.0)))
    bits = bytearray(len(feats))
    mask = bytearray(len(feats))
    for t in range(2, len(feats)):
        a, b = feats[t], feats[t - 2]
        v = 0
        for i in range(8):
            if a[i] > b[i]:
                v |= 1 << i
        bits[t] = v
        mask[t] = 1 if a[0] > 60 else 0
    return bytes(bits), bytes(mask)


def fp_match(fa, fb):
    """Cherche le passage commun le plus long. Renvoie (débutA, finA, débutB, finB) en s."""
    ba, ma = fa
    bb, mb = fb
    STEP = 2
    index = {}
    for t in range(0, len(ba) - 2 * STEP):
        if ma[t] and ma[t + STEP] and ma[t + 2 * STEP]:
            h = ba[t] | (ba[t + STEP] << 8) | (ba[t + 2 * STEP] << 16)
            if h in (0, 0xFFFFFF):
                continue
            index.setdefault(h, []).append(t)
    votes = {}
    for t in range(0, len(bb) - 2 * STEP):
        if mb[t] and mb[t + STEP] and mb[t + 2 * STEP]:
            h = bb[t] | (bb[t + STEP] << 8) | (bb[t + 2 * STEP] << 16)
            lst = index.get(h)
            if lst and len(lst) < 40:
                for i in lst:
                    votes[i - t] = votes.get(i - t, 0) + 1
    if not votes:
        return None
    # regroupe les décalages voisins (±1 mesure)
    best, bestv = None, 0
    for d, v in votes.items():
        tot = v + votes.get(d - 1, 0) + votes.get(d + 1, 0)
        if tot > bestv:
            best, bestv = d, tot
    if bestv < 12:
        return None
    pop = [bin(i).count("1") for i in range(256)]
    lo, hi = max(0, best), min(len(ba), len(bb) + best)
    agree = []
    for t in range(lo, hi):
        u = t - best
        if not (ma[t] or mb[u]):
            agree.append(0.5)
            continue
        m = 0
        for dd in (-1, 0, 1):
            if 0 <= u + dd < len(bb):
                m = max(m, 8 - pop[ba[t] ^ bb[u + dd]])
        agree.append(m / 8.0)
    W = 60                                 # lissage sur 3 s
    acc = sum(agree[:W])
    smooth = []
    for i in range(len(agree)):
        smooth.append(acc / W)
        if i + W < len(agree):
            acc += agree[i + W] - agree[i]
    run_s, run_l, cur = 0, 0, None
    for i, v in enumerate(smooth):
        if v > 0.80:
            if cur is None:
                cur = i
            if i - cur + 1 > run_l:
                run_s, run_l = cur, i - cur + 1
        else:
            cur = None
    sec = FP_HOP / FP_RATE
    # la moyenne glissante déborde : on recale les bords (début +40 % de fenêtre,
    # fin +60 %), puis on affine avec la concordance brute
    a0 = run_s + int(0.4 * W)
    a1 = run_s + run_l - 1 + int(0.6 * W)
    while a0 < a1 and sum(agree[a0:a0 + 10]) / 10 < 0.82:
        a0 += 1
    while a1 > a0 and sum(agree[max(0, a1 - 10):a1]) / 10 < 0.82:
        a1 -= 1
    length = (a1 - a0) * sec + FP_WIN / FP_RATE * 0.5
    if length < 15 or length > 200:
        return None
    sa = (lo + a0) * sec
    sb = sa - best * sec
    return (round(sa, 2), round(sa + length, 2), round(sb, 2), round(sb + length, 2))


def fp_decode(path, seconds=FP_SECONDS):
    """Décode le son du début d'un fichier (dans le processus d'analyse)."""
    from PySide6.QtCore import QEventLoop
    from PySide6.QtMultimedia import QAudioDecoder
    dec = QAudioDecoder()
    fmt = QAudioFormat()
    fmt.setSampleRate(FP_RATE)
    fmt.setChannelCount(1)
    fmt.setSampleFormat(QAudioFormat.Int16)
    dec.setAudioFormat(fmt)
    dec.setSource(QUrl.fromLocalFile(path))
    loop = QEventLoop()
    out = bytearray()
    want = seconds * FP_RATE * 2

    def on_buf():
        while dec.bufferAvailable():
            b = dec.read()
            raw = b.constData()
            try:
                data = bytes(raw)[: b.byteCount()]
            except TypeError:
                data = raw.tobytes()[: b.byteCount()]
            f = b.format()
            if f.sampleRate() == FP_RATE and f.channelCount() == 1 and _ev(f.sampleFormat()) == _ev(QAudioFormat.Int16):
                out.extend(data)
            if len(out) >= want:
                dec.stop()
                loop.quit()
                return
    dec.bufferReady.connect(on_buf)
    dec.finished.connect(loop.quit)
    dec.error.connect(lambda *a: loop.quit())
    QTimer.singleShot(120000, loop.quit)
    dec.start()
    loop.exec()
    dec.stop()
    return bytes(out[:want])


def fp_cache_path(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = hashlib.sha1(f"{path}|{st.st_size}|{int(st.st_mtime)}|{FP_SECONDS}".encode("utf-8")).hexdigest()
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    d = os.path.join(base, "Nova", "app", "fp")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, key + ".bin")


def fp_decode_many(paths, seconds=FP_SECONDS):
    """Décode le début de plusieurs fichiers EN MÊME TEMPS (plus rapide)."""
    from PySide6.QtCore import QEventLoop
    from PySide6.QtMultimedia import QAudioDecoder
    loop = QEventLoop()
    want = seconds * FP_RATE * 2
    jobs = {}

    def check_done():
        if all(j["done"] for j in jobs.values()):
            loop.quit()

    for path in paths:
        dec = QAudioDecoder()
        fmt = QAudioFormat()
        fmt.setSampleRate(FP_RATE)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.Int16)
        dec.setAudioFormat(fmt)
        dec.setSource(QUrl.fromLocalFile(path))
        job = {"dec": dec, "out": bytearray(), "done": False}
        jobs[path] = job

        def on_buf(job=job):
            dec_ = job["dec"]
            while dec_.bufferAvailable() and not job["done"]:
                b = dec_.read()
                raw = b.constData()
                try:
                    data = bytes(raw)[: b.byteCount()]
                except TypeError:
                    data = raw.tobytes()[: b.byteCount()]
                f = b.format()
                if f.sampleRate() == FP_RATE and f.channelCount() == 1 and _ev(f.sampleFormat()) == _ev(QAudioFormat.Int16):
                    job["out"].extend(data)
                if len(job["out"]) >= want:
                    job["done"] = True
                    dec_.stop()
                    check_done()

        def on_end(*_a, job=job):
            job["done"] = True
            check_done()
        dec.bufferReady.connect(on_buf)
        dec.finished.connect(on_end)
        dec.error.connect(on_end)
    QTimer.singleShot(240000, loop.quit)
    for j in jobs.values():
        j["dec"].start()
    if jobs:
        loop.exec()
    res = {}
    for path, j in jobs.items():
        j["dec"].stop()
        res[path] = bytes(j["out"][:want])
    return res


def fp_get_many(paths):
    out, todo = {}, []
    for path in paths:
        cp = fp_cache_path(path)
        if cp and os.path.exists(cp):
            with open(cp, "rb") as fh:
                data = fh.read()
            h = len(data) // 2
            out[path] = (data[:h], data[h:])
        else:
            todo.append(path)
    for path, pcm in fp_decode_many(todo).items():
        fp = fp_features(pcm)
        out[path] = fp
        cp = fp_cache_path(path)
        if cp and fp[0] and len(pcm) > FP_RATE * 2 * 60:
            with open(cp, "wb") as fh:
                fh.write(fp[0] + fp[1])
    return out


def intro_worker(args):
    """Processus séparé : python -c ... intro_worker([cible, voisin1, voisin2])."""
    from PySide6.QtCore import QCoreApplication
    app_ = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])  # noqa: F841
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
        except Exception:  # noqa: BLE001
            pass
    target, others = args[0], args[1:]
    result = {}
    try:
        fps = fp_get_many([target] + others)
        fa = fps[target]
        best = None
        for o in others:
            m = fp_match(fa, fps[o])
            if m and (best is None or (m[1] - m[0]) > (best[1][1] - best[1][0])):
                best = (o, m)
        if best:
            o, m = best
            result[target] = [m[0], m[1]]
            result[o] = [m[2], m[3]]
        result.setdefault(target, None)
    except Exception as e:  # noqa: BLE001
        result["error"] = repr(e)
    out = os.environ.get("NOVA_INTRO_OUT")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("NOVA_INTRO " + json.dumps(result) + "\n")
    if sys.stdout is not None:
        sys.stdout.write("NOVA_INTRO " + json.dumps(result) + "\n")
        sys.stdout.flush()


def mkv_chapters(path):
    """Lit les chapitres d'un .mkv : [(début s, fin s ou None, nom)]."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(4 * 1024 * 1024)
    except OSError:
        return []

    def vint(pos, keep_marker):
        b = data[pos]
        n = 1
        mask = 0x80
        while n <= 8 and not (b & mask):
            mask >>= 1
            n += 1
        if n > 8:
            raise ValueError
        v = b if keep_marker else b & (mask - 1)
        for i in range(1, n):
            v = (v << 8) | data[pos + i]
        return v, n

    def elements(start, end):
        pos = start
        while pos < end - 1:
            eid, n1 = vint(pos, True)
            size, n2 = vint(pos + n1, False)
            body = pos + n1 + n2
            if size == (1 << (7 * n2)) - 1:   # taille inconnue
                size = end - body
            yield eid, body, size
            pos = body + size

    def uint(body, size):
        return int.from_bytes(data[body:body + size], "big")
    try:
        chapters = []
        for eid, body, size in elements(0, len(data)):
            if eid != 0x18538067:            # Segment
                continue
            for cid, cb, cs in elements(body, min(len(data), body + size)):
                if cid == 0x1F43B675:        # premier Cluster : les chapitres sont avant
                    break
                if cid != 0x1043A770:
                    continue
                for ed, eb, es in elements(cb, cb + cs):
                    if ed != 0x45B9:
                        continue
                    for at, ab, asz in elements(eb, eb + es):
                        if at != 0xB6:
                            continue
                        st, en, name = 0, None, ""
                        for k, kb, ks in elements(ab, ab + asz):
                            if k == 0x91:
                                st = uint(kb, ks) / 1e9
                            elif k == 0x92:
                                en = uint(kb, ks) / 1e9
                            elif k == 0x80 and not name:
                                for d, db, ds in elements(kb, kb + ks):
                                    if d == 0x85:
                                        name = data[db:db + ds].decode("utf-8", "replace")
                        chapters.append((st, en, name))
                return sorted(chapters)
        return chapters
    except (ValueError, IndexError):
        return []


INTRO_WORDS = ("intro", "opening", "générique", "generique", "ouverture", " op ", "theme", "titles")
CREDITS_WORDS = ("credit", "ending", "générique de fin", "generique de fin", "outro", " end ", " ed ")


def chapters_marks(chapters, duration_s):
    """(début intro, fin intro, début générique de fin) d'après les noms des chapitres."""
    intro = credits = None
    for i, (st, en, name) in enumerate(chapters):
        n = " " + name.lower().strip() + " "
        nxt = chapters[i + 1][0] if i + 1 < len(chapters) else duration_s
        end = en or nxt
        if credits is None and any(w in n for w in CREDITS_WORDS) and st > duration_s * 0.5:
            credits = st
        elif intro is None and any(w in n for w in INTRO_WORDS) and st < duration_s * 0.4 and end:
            intro = (st, end)
    return intro, credits


EP_ID_RE = re.compile(r"s(\d{1,2})\s*[ex]\s*(\d{1,3})|\b(\d{1,2})x(\d{1,3})\b|[ée]p(?:isode)?\s*\.?\s*(\d{1,3})", re.I)


def episode_id(name):
    """(saison, épisode, nom de la série) d'après le nom du fichier, ou None."""
    m = EP_ID_RE.search(name)
    if not m:
        return None
    if m.group(1):
        se, ep = int(m.group(1)), int(m.group(2))
    elif m.group(3):
        se, ep = int(m.group(3)), int(m.group(4))
    else:
        se, ep = -1, int(m.group(5))
    series = re.sub(r"[^a-z]", "", name[:m.start()].lower())
    return se, ep, series


def pick_episode_neighbors(path, extra=(), limit=3):
    """Choisit jusqu'à 3 autres épisodes de la même série, les plus proches."""
    name = os.path.basename(path)
    folder = os.path.dirname(path)
    pool = set()

    def add_dir(d, depth=0):
        try:
            with os.scandir(d) as it:
                for e in it:
                    if e.is_file() and os.path.splitext(e.name)[1].lower() in VIDEO_EXT:
                        pool.add(e.path)
                    elif depth == 0 and e.is_dir() and len(pool) < 400:
                        add_dir(e.path, 1)
        except OSError:
            pass
    try:
        with os.scandir(folder) as it:
            for e in it:
                if e.is_file() and os.path.splitext(e.name)[1].lower() in VIDEO_EXT:
                    pool.add(e.path)
    except OSError:
        pass
    # un épisode par dossier : on regarde aussi les dossiers voisins
    parent = os.path.dirname(folder)
    if parent and parent != folder and len(pool) < 3:
        add_dir(parent)
    for q in extra:
        if q and os.path.isfile(q):
            pool.add(q)
    pool.discard(path)
    me = episode_id(name)
    scored = []
    for c in pool:
        cn = os.path.basename(c)
        ce = episode_id(cn)
        if me and ce:
            if me[2] and ce[2] and me[2] != ce[2]:
                continue                      # autre série
            if ce[:2] == me[:2]:
                continue                      # même épisode (autre copie)
            score = (0 if ce[0] == me[0] else 1, abs(ce[1] - me[1]))
        else:
            n = 0
            for x, y in zip(cn.lower(), name.lower()):
                if x != y:
                    break
                n += 1
            if n < max(4, int(len(name) * 0.4)):
                continue
            score = (2, 0)
        scored.append((score, natural_key(cn), c))
    scored.sort()
    return [c for _, _, c in scored[:limit]]


class Backend(QObject):
    recentsChanged = Signal()
    introChanged = Signal()
    introFound = Signal()
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
            self._deband = int(self._s.value("deband", 1))
        except (TypeError, ValueError):
            self._hdr_toe = 0.85
        self._tone_url = self._write_shader("tonemap", TONEMAP_QSB)
        self._stats_url = self._write_shader("stats", STATS_QSB)
        self._probe_url = self._write_shader("probe", PROBE_QSB)
        self._sdr_url = self._write_shader("sdr", SDR_QSB)
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
                           "kind": kind, "bps": bps, "frame": fmt.bytesPerFrame(),
                           "limiter": Limiter(kind, fmt.channelCount(), fmt.sampleRate())}
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
        out = b["limiter"].process(data, boost_curve(self._gain))
        pend = b["pending"]
        pend += out
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
        b["limiter"].reset()
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
        self._intro = (-1.0, -1.0)
        self._credits = -1.0
        self.introChanged.emit()
        self._intro_path = url.toLocalFile() if isinstance(url, QUrl) else ""
        if self._intro_path:
            p = self._intro_path
            QTimer.singleShot(3000, lambda: self._find_intro(p))
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

    def _get_sdr_url(self):
        return self._sdr_url

    def _get_hdr_saturation(self):
        return self._hdr_saturation

    def _get_hdr_dynamic(self):
        return self._hdr_dynamic

    hdrMode = Property(int, _get_hdr_mode, notify=hdrChanged)
    hdrEnabled = Property(bool, _get_hdr_enabled, notify=hdrChanged)
    hdrBrightness = Property(float, _get_hdr_brightness, notify=hdrChanged)
    toneShader = Property(str, _get_tone_url, constant=True)
    statsShader = Property(str, _get_stats_url, constant=True)
    sdrShader = Property(str, _get_sdr_url, constant=True)
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

    def _get_deband(self):
        return self._deband

    deband = Property(int, _get_deband, notify=hdrChanged)

    @Slot(int)
    def setDeband(self, v):
        self._deband = max(0, min(2, int(v)))
        self._s.setValue("deband", self._deband)
        self.hdrChanged.emit()

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
        proc = getattr(self, "_intro_proc", None)
        try:
            if proc is not None and proc.state() != QProcess.NotRunning:
                proc.kill()
        except RuntimeError:
            pass

    # ================================================================ générique
    def _get_intro_start(self):
        return getattr(self, "_intro", (-1.0, -1.0))[0]

    def _get_intro_end(self):
        return getattr(self, "_intro", (-1.0, -1.0))[1]

    def _get_credits(self):
        return getattr(self, "_credits", -1.0)

    introStart = Property(float, _get_intro_start, notify=introChanged)
    introEnd = Property(float, _get_intro_end, notify=introChanged)
    creditsStart = Property(float, _get_credits, notify=introChanged)

    @staticmethod
    def _intro_key(path):
        return "intro2/" + hashlib.sha1(os.path.normcase(path).encode("utf-8")).hexdigest()

    def _set_intro(self, path, se):
        if path != getattr(self, "_intro_path", "") or not se:
            return
        self._intro = (float(se[0]), float(se[1]))
        log(f"générique détecté : {se[0]:.1f}s -> {se[1]:.1f}s ({os.path.basename(path)})")
        self.introChanged.emit()
        self.introFound.emit()

    def _find_intro(self, path):
        if path != getattr(self, "_intro_path", "") or not os.path.isfile(path):
            return
        dur = self.player.duration() / 1000.0
        # 1) chapitres du fichier (.mkv)
        if path.lower().endswith((".mkv", ".mka", ".webm")):
            intro, credits = chapters_marks(mkv_chapters(path), dur or 1e9)
            if credits:
                self._credits = float(credits)
                self.introChanged.emit()
            if intro:
                self._set_intro(path, intro)
                return
        # 2) déjà analysé
        cached = self._s.value(self._intro_key(path))
        if cached:
            try:
                v = json.loads(cached)
            except (TypeError, ValueError):
                v = None
            if v:
                self._set_intro(path, v)
            return
        # 3) comparaison avec d'autres épisodes de la même série (même dossier,
        #    dossiers voisins « Episode 9/ », ou vidéos de la file d'attente)
        cands = pick_episode_neighbors(path, getattr(self, "_queue_paths", []))
        if not cands:
            log(f"générique : aucun autre épisode trouvé à côté de {os.path.basename(path)}")
            return
        folder, name = os.path.dirname(path), os.path.basename(path)
        old = getattr(self, "_intro_proc", None)
        try:
            if old is not None and old.state() != QProcess.NotRunning:
                old.kill()
        except RuntimeError:
            pass
        if getattr(sys, "frozen", False):
            return
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.SeparateChannels)
        out_file = os.path.join(os.path.dirname(fp_cache_path(path) or str(Path.home())), "result.txt")
        try:
            os.remove(out_file)
        except OSError:
            pass
        from PySide6.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        env.insert("NOVA_INTRO_OUT", out_file)
        proc.setProcessEnvironment(env)
        self._intro_out = out_file
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import app; app.intro_worker(sys.argv[2:])")
        args = ["-c", code, str(Path(__file__).resolve().parent), path] + cands
        proc.finished.connect(lambda *_: self._intro_done(proc, path))
        self._intro_proc = proc
        log(f"analyse du générique : {name} comparé à {[os.path.basename(c) for c in cands]}")
        proc.start(sys.executable, args)

    @Slot(list)
    def noteQueue(self, paths):
        """Vidéos ajoutées à la file d'attente (servent aussi à trouver le générique)."""
        lst = getattr(self, "_queue_paths", [])
        for p in paths:
            p = str(p)
            if p.startswith("file:"):
                p = QUrl(p).toLocalFile()
            if p not in lst:
                lst.append(p)
        self._queue_paths = lst[-300:]

    def _intro_done(self, proc, path):
        try:
            out = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            out = ""
        if "NOVA_INTRO " not in out:
            try:
                with open(self._intro_out, encoding="utf-8") as fh:
                    out = fh.read()
            except (OSError, AttributeError):
                pass
        if getattr(self, "_intro_proc", None) is proc:
            self._intro_proc = None
        proc.deleteLater()
        for line in out.splitlines():
            if not line.startswith("NOVA_INTRO "):
                continue
            try:
                res = json.loads(line[11:])
            except ValueError:
                return
            if "error" in res:
                log(f"analyse du générique impossible : {res['error']}")
                return
            for p, v in res.items():
                self._s.setValue(self._intro_key(p), json.dumps(v))
            self._set_intro(path, res.get(path))
            return


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
    property bool sdrFilter: backend.hdrMode === 0 && !backend.hdrMeasuring && backend.deband > 0 && player.hasVideo
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
        backend.noteQueue(paths)
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
            // image de Qt copiée pixel par pixel (sans flou : les pixels invalides
            // ne s'étalent pas, ils sont réparés dans le shader)
            ShaderEffectSource {
                id: videoTex
                anchors.fill: videoOut
                sourceItem: (win.hdrActive || backend.hdrMeasuring || win.sdrFilter) ? videoOut : null
                hideSource: win.hdrActive || backend.hdrMeasuring || win.sdrFilter
                live: true
                visible: false
                smooth: false
                // format choisi par le calibrage automatique (SDR : 16 bits = dégradés plus fins)
                format: (backend.hdrTexFloat || win.sdrFilter) ? ShaderEffectSource.RGBA16F : ShaderEffectSource.RGBA8
            }
            // vidéos normales : anti-compression des zones sombres
            ShaderEffect {
                id: sdrFx
                anchors.fill: videoOut
                visible: win.sdrFilter
                property variant source: videoTex
                property real deband: backend.deband
                property point texel: Qt.point(1 / Math.max(1, width * Screen.devicePixelRatio),
                                               1 / Math.max(1, height * Screen.devicePixelRatio))
                fragmentShader: backend.sdrShader
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
                property real deband: backend.deband
                property point texel: Qt.point(1 / Math.max(1, width * Screen.devicePixelRatio),
                                               1 / Math.max(1, height * Screen.devicePixelRatio))
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

            Connections {
                target: backend
                function onIntroFound() {
                    if (player.position / 1000 < backend.introEnd - 2)
                        toast.show("Générique repéré : bouton « Passer » disponible")
                }
            }
            // ---------- « Passer le générique » / « Épisode suivant »
            Rectangle {
                id: skipBtn
                z: 30
                property real posS: player.position / 1000
                property bool inIntro: backend.introEnd > 0 && posS >= backend.introStart - 0.5
                                       && posS < backend.introEnd - 2
                property bool inCredits: win.currentIndex + 1 < queue.count && player.duration > 0
                                         && ((backend.creditsStart > 0 && posS >= backend.creditsStart)
                                             || (player.duration - player.position < 40000 && player.duration > 300000))
                property bool show: (inIntro || inCredits) && win.hasMedia && !backend.hdrMeasuring
                visible: opacity > 0.01
                opacity: show ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 220 } }
                anchors.right: parent.right; anchors.rightMargin: 36
                anchors.bottom: parent.bottom
                anchors.bottomMargin: win.controlsVisible ? 150 : 48
                Behavior on anchors.bottomMargin { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                width: skipRow.implicitWidth + 36; height: 46; radius: 10
                color: skipMa.containsMouse ? Qt.rgba(1, 1, 1, 0.95) : Qt.rgba(0.08, 0.08, 0.1, 0.82)
                border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.35)
                Behavior on color { ColorAnimation { duration: 150 } }
                Row {
                    id: skipRow
                    anchors.centerIn: parent
                    spacing: 10
                    Text {
                        text: skipBtn.inIntro ? "Passer le générique" : "Épisode suivant"
                        color: skipMa.containsMouse ? "black" : "white"
                        font.pixelSize: 15; font.weight: Font.DemiBold
                    }
                    Text {
                        text: "»"
                        color: skipMa.containsMouse ? "black" : "white"
                        font.pixelSize: 20; font.weight: Font.Bold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                MouseArea {
                    id: skipMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    enabled: skipBtn.show
                    onClicked: {
                        if (skipBtn.inIntro) { win.seekTo((backend.introEnd - 0.4) * 1000); toast.show("Générique passé") }
                        else win.playNext()
                    }
                }
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
                            visible: backend.hdrMode > 0 || player.hasVideo
                            anchors.verticalCenter: parent.verticalCenter
                            width: hdrText.implicitWidth + 20; height: 28; radius: 8
                            color: hdma.containsMouse ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.08)
                            border.width: 1
                            border.color: (backend.hdrMode > 0 && backend.hdrEnabled) ? theme.accent : Qt.rgba(1, 1, 1, 0.2)
                            Text {
                                id: hdrText
                                anchors.centerIn: parent
                                text: backend.hdrMode > 0 ? "HDR" : "IMAGE"
                                color: (backend.hdrMode > 0 ? backend.hdrEnabled : backend.deband > 0) ? "white" : theme.muted
                                font.pixelSize: 12; font.weight: Font.Black; font.letterSpacing: 1
                            }
                            MouseArea { id: hdma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: hdrPop.open() }
                            DarkPopup {
                                id: hdrPop
                                x: Math.min(0, (parent.width - width) / 2)
                                y: -height - 12
                                contentItem: Column {
                                    MenuHeader { text: "SCÈNES SOMBRES" }
                                    Text { text: "Lisse les blocs et bandes de compression"; color: theme.muted; font.pixelSize: 11; leftPadding: 12 }
                                    Row {
                                        leftPadding: 12; topPadding: 6; bottomPadding: 8
                                        spacing: 6
                                        Chip { text: "Désactivé"; selected: backend.deband === 0; onClicked: backend.setDeband(0) }
                                        Chip { text: "Normal"; selected: backend.deband === 1; onClicked: backend.setDeband(1) }
                                        Chip { text: "Fort"; selected: backend.deband === 2; onClicked: backend.setDeband(2) }
                                    }
                                    MenuHeader { visible: backend.hdrMode > 0; text: backend.hdrMode === 2 ? "IMAGE HDR (HLG)" : "IMAGE HDR" }
                                    Text {
                                        visible: backend.hdrMode > 0
                                        text: backend.hdrCalibration === "ok" ? "Calibré pour ta carte graphique ✓"
                                              : backend.hdrCalibration === "impossible" ? "Calibrage impossible : image d'origine affichée"
                                              : "Calibrage en cours…"
                                        color: backend.hdrCalibration === "impossible" ? theme.accent2 : theme.muted
                                        font.pixelSize: 11; leftPadding: 12; bottomPadding: 4
                                    }
                                    MenuRow {
                                        width: 300
                                        visible: backend.hdrMode > 0
                                        icon: "image"
                                        text: "Adapter le HDR à mon écran"
                                        checked: backend.hdrEnabled
                                        onClicked: backend.setHdrEnabled(!backend.hdrEnabled)
                                    }
                                    MenuRow {
                                        width: 300
                                        visible: backend.hdrEnabled && backend.hdrMode > 0
                                        icon: "brush"
                                        text: "Adaptation dynamique (par scène)"
                                        checked: backend.hdrDynamic
                                        onClicked: backend.setHdrDynamic(!backend.hdrDynamic)
                                    }
                                    Text { visible: backend.hdrEnabled && backend.hdrMode > 0; text: "Couleurs"; color: theme.muted; font.pixelSize: 12; leftPadding: 12; topPadding: 4 }
                                    Row {
                                        visible: backend.hdrEnabled && backend.hdrMode > 0
                                        leftPadding: 12; topPadding: 4; bottomPadding: 4
                                        spacing: 6
                                        Chip { text: "Douces"; selected: backend.hdrSaturation < 0.95; onClicked: backend.setHdrSaturation(0.85) }
                                        Chip { text: "Normales"; selected: backend.hdrSaturation >= 0.95 && backend.hdrSaturation <= 1.05; onClicked: backend.setHdrSaturation(1.0) }
                                        Chip { text: "Vives"; selected: backend.hdrSaturation > 1.05; onClicked: backend.setHdrSaturation(1.15) }
                                    }
                                    Text { visible: backend.hdrEnabled && backend.hdrMode > 0; text: "Ombres"; color: theme.muted; font.pixelSize: 12; leftPadding: 12; topPadding: 4 }
                                    Row {
                                        visible: backend.hdrEnabled && backend.hdrMode > 0
                                        leftPadding: 12; topPadding: 4; bottomPadding: 4
                                        spacing: 6
                                        Chip { text: "Profondes"; selected: backend.hdrToe > 0.95; onClicked: backend.setHdrToe(1.0) }
                                        Chip { text: "Détaillées"; selected: backend.hdrToe <= 0.95 && backend.hdrToe > 0.8; onClicked: backend.setHdrToe(0.85) }
                                        Chip { text: "Très claires"; selected: backend.hdrToe <= 0.8; onClicked: backend.setHdrToe(0.75) }
                                    }
                                    Text { visible: backend.hdrEnabled && backend.hdrMode > 0; text: "Luminosité"; color: theme.muted; font.pixelSize: 12; leftPadding: 12; topPadding: 4 }
                                    Row {
                                        visible: backend.hdrEnabled && backend.hdrMode > 0
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
    # Windows : horloge précise à 1 ms (images affichées à intervalles réguliers,
    # moins de micro-saccades) et priorité un peu plus haute pour le lecteur
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.winmm.timeBeginPeriod(1)
            app.aboutToQuit.connect(lambda: ctypes.windll.winmm.timeEndPeriod(1))
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x8000)
        except Exception as e:  # noqa: BLE001
            log(f"réglages Windows ignorés : {e!r}")
    # moins de pauses du ramasse-miettes Python pendant la lecture
    gc.collect()
    gc.freeze()
    gc.set_threshold(20000, 50, 100)
    code = app.exec()
    backend.player.stop()
    return code


if __name__ == "__main__":
    sys.exit(main())
