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
APP_VERSION = 13  # augmenter à chaque mise à jour publiée

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
    "7xdqUvaljHaZJulbmL8vI39vID9sZboVmR8wrorMD39KOeVFTH5Jk/TjmPxSSv4GJn9baj6M0nzYRmM8SjkJf8pEv9vX6MiCRvKY"
    "R5ZeUa43KrWqYZnmwFS9PFoRpe2V8e1TRjhRKzWHWsiVanNoYKDRrE+PNo1t0+HAlQOGYRiTpaZrXN4sbig165WZIUETEpC4cao0"
    "WmnOcupkbazMy9vqlfHtzWq50eDURqk5XS81K7Uqp47NVkuTlVFO2lGpjiXKjdHSRKKD8dLkdNM2bXNoYNfQwMB0tRLW6pNogVF0"
    "fIeRpJ2N0uTURLlurzMaten6aHmoc32z1GwMDQxcUarPVqrjxhXlURut3lSeWVur1cdMrCuPOkajPr5tU22kUi2X6plKtTbdNCQ9"
    "S05sGMPGZGkm0xgUFRkzZ2az0gjBOFEzho2GcZqstexcYJv48fN24ASu51i2x/m3V4xhY6q2M5NpGMsjkZ4biI9vWoGf9/28ZTum"
    "my/4XjYbyVZsru+5fmDZXuDnvbztZUk1O+eKrs3Ac/K+61h518Rq6r5ebk7Xq8ZkZSazvTJoTNQGjUazPMUtc01X9GD7dsF2HMfx"
    "XdN2XAfVyA4N7CKnTV2+vjpaGytnRKlaaUbeEoTZKTJxdKI0OZXB+sgGVC9nZpkzByPrsjHZ8gLHtHzPL1gtBgjnEV/B8QLUzlhu"
    "ZGanjGWGVcgVPEt4BR2XiWRzDulX6swv5ArSQm5gNCdEuZywL2leeS5bTMvOFxzHchwnCNxC3nMt3y2o0W0xDSfblLHCSFnIp59x"
    "mpiSsq/YYGOFkeEWUpMgF9Dkcn3Pdm3f9At+wfEs27I81y945RWmH+mbz9m+7wSu71ue7wVYSHtnujpWu6C5qVYtT5amyEGDKofs"
    "TLqqVC9NGsNGmUVA0cr7GDM88gRfIqwwLVDoTZaajhrwvO07QRAULNO2CgXLMh1p/KBh5sx8YEpL867t+LblWI4rQ0RUYzyIDzo/"
    "b/um6+Z9ZV/kX8cObOwh7+Rt1/Nt33MCk0QEViDiw3HQj4FfYJ0XfNm3ZztW3i64lh/wUcDocmzBYRYKplsIHDdw8p4ML6mfJfWz"
    "Atu23cAPXNPMcwsKgZc3TdM2CwXPzfseako5Yplwa2KSLMMlJGcOpUajaBnD0r2spizmtApr4svyXD2LeW6s1syUp6Je7LydR4Ms"
    "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"
    "ScK820GH9uLzv37ZMKs="
)
STATS_QSB = (
    "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"
    "cqxGwV7tVYj1or2Sqmkzw3egsdpkTwgcSOwOXJ2cblqmaeXcrFh8rmI74/GDwMrqpqc7tPqqXsOjt6kyrbgyhbgNZ47V+syJBmp7"
    "ts2yCzy1KsUBDdNlKXnk0LE0MrSkMqhG0XSo+IV1MayMm8dE3DymzdW8Xm1Mhs3RioeUo4JylCLsUTXCjns5nlka2YC7F7+muAip"
    "0TQdl6kxeaab/CymA9xMGdmMjhtcT8SZsfOSsnzmwiWVgUWrVqZE1qtHG9nQo2Eokhkde3ez94foWMU0WiZK1DUjMyVZlK9rRmaF"
    "ZIkjIUloS0Ilu9cwQ2FBaigSP7nkF1N+seQXO91s6CWUK0CnVSqWI7eFabImG1/PuIbDTSeLO980Hd1TUgWuKczKzGUN3TTR9gxK"
    "GukNS0b7cFafVqoMmtx5LeF0ukFeyXZtz7Udw9IdK+fZui3f2+OMaOPyDJBfWNejLUk3D6zFnAsbcPPT6Idqhm0n7ACZhSIJjpsh"
    "1Qa/3+a5rnAXpjCr2qNsZnW0vJ11otBiOLNRm9ssskAy9eW2pfclQr6TosxybP68WY46WMofWS0MLizUC6v1k7U+Ln8Ko+LhzGgP"
    "KqtHK6R7NIEZ69GG1wmEjoZo8FXd1N2dSM2PRpfc9lgYpebNZGr+8OOOGD81//pKt7dOtLdT7O0UezvF3k6xt1Ps7RR7O8XewLad"
    "Ym+n2Nsp9naKvZ1i/xdKRLVT7K/3FWyn2Nsp9rZdtFPsjeelmmJv59fb+fV2fv1Vza9fpuTX94ny647+r5swpwS4rQXVwuCCSqlS"
    "7e0ultv583b+vJ0/b+fP2/nzdv68nT9v58/b+fN2/rydP2/nz/8Vskzt/PnrfQXb+fN2/rxtF+38eeN5ScnLdva8nT1/TbPn/9S5"
    "8zDTuzXS5h30D0PSZ+9z+9eMBIFf5Wlp/MH5YLFW96upNWH4W61szA8V3lWpCuHsUZuLng9z6docbbjQv64SBDW/nurXE8oTpJRh"
    "T9DajbT87E9QZcYa6VBzDXTvbqTjMWCSbmMTOm76CUqnkS4KDhOkXEhM9K+UFZm5QmHzKKuvqreOWlohkvsr6jiVvCDKU8ZfJa4h"
    "cSNX3LMxnkYDTyRpyhFJu2v1Qr3YT8uqFhTUhoayAlVWViw/+rjj8wuqlVotf3R5eKSuHl3xTtocbeWiVQuWLTtuIdVCmvBYNlJP"
    "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"
    "wtqk+0GL/vzzf0h+4iQ="
)
PROBE_QSB = (
    "AAAQb3ic5VhZb9tGEP502QlzNneatNnEaUPFgkrTcg4rdgPYvdAETmMjLSAYBE2RCluJVMilKzcw0P6BPvZXtf+nL0WL3Z2VKFlO"
    "3IfmpQsw3Jmd85vZkRkAxwGUARQAXMErcDjYgo8B1hAjRoI2LABFAPibFqYsYeAcAiRw0ZHKXamuzL9VdQY7yBDInYMGbADrOZmi"
    "NK/iewoXHAlCDACcIInHOemzenOBVDbQhwsPITj2yOVjHdthSwidRIoYGRJ48AGYlEThTYpHXTP0bo9YZbNUnJsV9k/gGOaJ+x6K"
    "0uMJzMj3F082n9RT3q43lkRxcBqlYcRnMCvTEk/PDSOlD1yWuJQkf1bYQBmnANwkPU3fIp+CFnof5ujLY3QJJlXmS5TlXqyKpCtD"
    "epbqkefN0VvzCsR7TH7uUlzI0Tqu8yhKnzdRklmL/SWUJJhM5lmWPgVdkrwyjlEc4rmK4zDofLKKmr6Gkuwrg/RPEl/wmkSfIp7w"
    "d4bsFUn+7LAWSv4s1aBA8udJvkzylyjW8yR/ieolePMoS9mrAP74/cmqpq9J7z8PaV0XTd9Q559eQRl3yHZZyqla3aEYhP8qxW6S"
    "f0HfJd49VORbXxUR058oyjo3CdvjhO0KyhKj04TPCmFzjvL/FhUZxwWSEfwNHJO6F4l/IVcL4XcVJWn/ItmblZNK+fwVFUm/TzyB"
    "0TPMSN51wkg/v5DsByR/PSfLCD/9aP5NwlE/JynWWxTfPNljJPsNKhLTuVy/at7tnJ7mfUS8ovQ5K7H5mPRv0/kNwuAynf2FAh6o"
    "Ti3T/S7QDKH2LWRzu36ShnHEFizL6Ce+F0rqZdh52WdBN3Z58wA7jHjTMFKeZB5nO1lgvDYYY6zn8gZ7xZ2nLk/CQVPypAXB3Oi7"
    "Xsj3msZ+0zCyKAzipCd0mdOwcxzlIHV7/a6f2OssjbPE85uGsesme2HUYbu+Zwt7W/5gLY6TtiXO4rDNRIJmlULZ9b1FtstWGPcH"
    "PEt8e91UlmpjutX6YO8nFWin63yeuJ11l7sta5utCBMN0+u6vb5p7rK7zKrbllr2wweWvWjbiw/u33u4tLhgL1XZvHRpWnV7qVrT"
    "e0tvF+pWtVpj4tU09g1joiCD3FhZGxXEtv4jkP9n8P6Wg/frEbxL7xDeMJqGbJxxiQMLErezFnfj5Ehovw3robV3B7OYSvYI5tJ9"
    "bycLAj+R6CyzxO+EKfcTc8fSSSXxj07P/T5OFLyNQUOg6AyhZ8us73o/xEGQ+tz0hMtRLUiS6jEh2qiqAm3p3nykPKxSOfLxcGF3"
    "U9Vrk7vcZ44ScqiIeeFUCBspd3noqUAmC5o/G68qNdrms6+ev3DWkjhNna+ifsYJjSnW2DLb+uy7tY2N5+uWSmiKjY2MTxjJuWXL"
    "bPOFs+UmHZ+TCdlcQsAZ6zCpqXpMpV9XmJgTaByp5VQYR226QHSdaLigPhgMasyqW7RboJ1quUD13MHk1V05ACxLudvxnVDsdZpj"
    "8K7kJerjddQpEUqKMcW1shBLQgnlOfUxVEbNINvf51kSTRjYz1+psvwjYriKnbkw8rpZ22ePej53u07K291wZ9UY8dOw1/5E/FN/"
    "uWoYWSoGeuT2/LTvej6TWtN+t4cX8Ehzj9RFlJaI/LDma7U88Tat6vb2FM0wekPrt1pZ6idmN/aikbow3fOjnGu1M7VBFkas1dJV"
    "3d6uDX+e2moEDCdAq6VHqTBf0xObjjd7/a6In7hSpjr8fdC+xbPCXu83D7lBStvMmayxMKofcoHiyXZRlyhwU768/C/mt4pDT/Ah"
    "ZY2IsSmea8VYdaBowYrMksb6xGhXn/eg7/SJD6OJnj3wXwHTPqImdeT6ByhCaqk="
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


def qt_expected(e, mw):
    """Ce que le shader HDR de Qt (P010) produit pour un gris PQ e (modèle mesuré, Qt 6.12)."""
    ml = 0.5081
    ks = 1.5 * ml - 0.5
    p = e / mw
    s = 1.0
    if p >= ks:
        t = (p - ks) / (1 - ks)
        t2, t3 = t * t, t * t * t
        pn = (2 * t3 - 3 * t2 + 1) * ks + (t3 - 2 * t2 + t) * (1 - ks) + (-2 * t3 + 3 * t2) * ml
        s = pn * mw / e
    x = max(pq_to_nits(e * s) / 100.0, 0.0)
    return x * 12.92 if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def make_calibration_frame(kind):
    """Image HDR10 de test (gris PQ connus), au format du décodage carte graphique (P010)
    ou logiciel (YUV420P10)."""
    PF = QVideoFrameFormat.PixelFormat
    pf = PF.Format_P010 if kind == "p010" else PF.Format_YUV420P10
    fmt = QVideoFrameFormat(QSize(CAL_W, CAL_H), pf)
    fmt.setColorTransfer(QVideoFrameFormat.ColorTransfer.ColorTransfer_ST2084)
    fmt.setColorSpace(QVideoFrameFormat.ColorSpace.ColorSpace_BT2020)
    fmt.setColorRange(QVideoFrameFormat.ColorRange.ColorRange_Video)
    frame = QVideoFrame(fmt)
    if not frame.map(QVideoFrame.MapMode.WriteOnly):
        return None
    zone = CAL_W // len(CAL_GRAYS)
    ys = [round(64 + 876 * g) for g in CAL_GRAYS]
    shift = 6 if kind == "p010" else 0

    def put(buf, off, v):
        buf[off] = v & 0xFF
        buf[off + 1] = (v >> 8) & 0xFF

    yb, ybpl = frame.bits(0), frame.bytesPerLine(0)
    for row in range(CAL_H):
        for x in range(CAL_W):
            put(yb, row * ybpl + x * 2, ys[min(x // zone, len(ys) - 1)] << shift)
    if kind == "p010":
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


def make_sized_calibration_frame(width, height, max_lum):
    """Image de test P010 aux dimensions de la vidéo (rempli ligne par ligne, rapide même en 4K)."""
    width -= width % 2
    height -= height % 2
    fmt = QVideoFrameFormat(QSize(width, height), QVideoFrameFormat.PixelFormat.Format_P010)
    fmt.setColorTransfer(QVideoFrameFormat.ColorTransfer.ColorTransfer_ST2084)
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


def solve_mastering_white(measured):
    """Retrouve le réglage de Qt (mw) à partir des gris mesurés sur l'affichage."""
    best = None
    for i in range(300, 1001):
        mw = i / 1000.0
        err = sum((qt_expected(g, mw) - m) ** 2 for g, m in zip(CAL_GRAYS, measured))
        if best is None or err < best[0]:
            best = (err, mw)
    return best[1], (best[0] / len(CAL_GRAYS)) ** 0.5


def calibration_matches(kind, raw):
    """Compare la mesure au modèle attendu pour ce chemin de décodage."""
    expected = [qt_expected(g, 1.0) for g in CAL_GRAYS] if kind == "p010" else list(CAL_GRAYS)
    got = [sum(c) / 3 for c in raw]
    return all(abs(a - b) < 0.06 for a, b in zip(got, expected)), expected


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
        self._tone_url = self._write_shader("tonemap", TONEMAP_QSB)
        self._stats_url = self._write_shader("stats", STATS_QSB)
        self._probe_url = self._write_shader("probe", PROBE_QSB)
        # calibrage : mesuré au démarrage sur la carte graphique de l'utilisateur
        self._cal_sink = None
        self._cal_frame = None
        self._cal_status = "en cours"      # en cours | ok | impossible (pour la vidéo en cours)
        self._cal_ok = {}                  # "p010" / "sw" -> bool, mesuré au démarrage
        self._cal_queue = []
        self._hdr_kind, self._hdr_scale, self._hdr_gamut2020 = 0, 1.0, 1
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
                self._hdr_path = "p010"
                if self._cal_ok.get("p010"):
                    QTimer.singleShot(0, lambda fs=sf.frameSize(), m=sf.maxLuminance(): self._measure_main(fs, m))
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
        return bool(self._hdr_path) and self._cal_ok.get(self._hdr_path, False)

    def _get_hdr_brightness(self):
        return self._hdr_brightness

    def _get_tone_url(self):
        return self._tone_url

    def _get_stats_url(self):
        return self._stats_url

    def _get_hdr_saturation(self):
        return self._hdr_saturation

    def _get_hdr_dynamic(self):
        return self._hdr_dynamic

    hdrMode = Property(int, _get_hdr_mode, notify=hdrChanged)
    hdrEnabled = Property(bool, _get_hdr_enabled, notify=hdrChanged)
    hdrBrightness = Property(float, _get_hdr_brightness, notify=hdrChanged)
    toneShader = Property(str, _get_tone_url, constant=True)
    statsShader = Property(str, _get_stats_url, constant=True)
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
        self._cal_queue = ["p010", "sw"]
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
                c = img.pixelColor(i * zone + zone // 2, CAL_H // 2)
                raw.append(tuple(round((v / 255.0 - 0.25) / 0.2, 3) for v in (c.red(), c.green(), c.blue())))
        except Exception as e:  # noqa: BLE001
            log(f"calibrage HDR : lecture impossible ({e!r})")
        ok, expected = calibration_matches(kind, raw) if len(raw) == len(CAL_GRAYS) else (False, [])
        self._cal_ok[kind] = ok
        log(f"calibrage HDR [{kind}] mesuré={raw} attendu={[round(x, 3) for x in expected]} -> {'OK' if ok else 'ÉCART'}")
        self._next_calibration()

    # --- mesure sur l'affichage principal (au début de chaque vidéo HDR décodée par la carte graphique)
    def _measure_main(self, size, max_lum):
        if self._display is None or self._measuring:
            return
        try:
            frame = make_sized_calibration_frame(size.width(), size.height(), max_lum)
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
                c = img.pixelColor(i * zone + zone // 2, CAL_H // 2)
                measured.append(sum((v / 255.0 - 0.25) / 0.2 for v in (c.red(), c.green(), c.blue())) / 3)
        except Exception as e:  # noqa: BLE001
            log(f"mesure HDR : lecture impossible ({e!r})")
        if len(measured) == len(CAL_GRAYS):
            mw, rms = solve_mastering_white(measured)
            ok = rms < 0.05
            log(f"mesure HDR sur l'affichage : gris={[round(m, 3) for m in measured]} -> réglage Qt={mw:.3f} (écart {rms:.3f}) {'OK' if ok else 'REFUSÉ'}")
            if ok:
                self._hdr_scale = mw
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

    def _get_tex_float(self):
        return self._hdr_tex_float

    def _get_cal_status(self):
        if self._cal_queue:
            return "en cours"
        if self._hdr_mode and not self._hdr_supported():
            return "impossible"
        return "ok" if self._cal_ok else "en cours"

    probeShader = Property(str, _get_probe_url, constant=True)
    hdrKind = Property(int, _get_kind, notify=hdrChanged)
    hdrScale = Property(float, _get_scale, notify=hdrChanged)
    hdrGamut2020 = Property(int, _get_gamut, notify=hdrChanged)
    hdrTexFloat = Property(bool, _get_tex_float, notify=hdrChanged)
    hdrCalibration = Property(str, _get_cal_status, notify=hdrChanged)

    @Slot(float)
    def setHdrSaturation(self, v):
        self._hdr_saturation = max(0.5, min(1.5, float(v)))
        self._s.setValue("hdrSaturation", self._hdr_saturation)
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
            ShaderEffectSource {
                id: videoTex
                anchors.fill: videoOut
                sourceItem: (win.hdrActive || backend.hdrMeasuring) ? videoOut : null
                hideSource: win.hdrActive || backend.hdrMeasuring
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
                anchors.fill: videoOut
                visible: win.hdrActive
                property variant source: videoTex
                property variant stats: statsSrc
                property real mode: backend.hdrMode
                property real brightness: backend.hdrBrightness
                property real saturation: backend.hdrSaturation
                property real dynamic: backend.hdrDynamic ? 1 : 0
                property real kind: backend.hdrKind
                property real kscale: backend.hdrScale
                property real gamut2020: backend.hdrGamut2020
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
