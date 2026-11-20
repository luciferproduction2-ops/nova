#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nova — application (interface + fonctions).
Ce fichier est celui qui se met à jour automatiquement : il est chargé par
nova.py (le lanceur), qui le télécharge depuis GitHub quand une nouvelle
version est publiée.
"""
import hashlib
import os
import re
import sys
from pathlib import Path

from PySide6.QtCore import (QObject, Property, QSettings, QStandardPaths, QUrl,
                            Signal, Slot, QPointF, QRectF, Qt)
from PySide6.QtGui import (QColor, QGuiApplication, QIcon, QLinearGradient,
                           QPainter, QPainterPath, QPixmap)
from PySide6.QtQml import QQmlApplicationEngine
from PySide6 import QtMultimedia, QtQuick  # noqa: F401  (embarque le moteur vidéo dans le .exe)
from PySide6.QtQuickControls2 import QQuickStyle

APP_NAME = "Nova"
APP_VERSION = 1  # augmenter à chaque mise à jour publiée

VIDEO_EXT = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv", ".ts",
    ".m2ts", ".mts", ".mpg", ".mpeg", ".3gp", ".ogv", ".vob", ".divx",
}

THEME = {
    "bg": "#0A0A0F",
    "panel": "#111118",
    "panel2": "#1B1B25",
    "text": "#F2F2F7",
    "muted": "#8B8B9E",
    "accent": "#8B5CF6",
    "accent2": "#EC4899",
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
    "close":   ["", "M6.5 6.5l11 11 M17.5 6.5l-11 11"],
    "check":   ["", "M5 12.5l4.5 4.5L19 7.5"],
    "trash":   ["", "M4 7h16 M10 11v6 M14 11v6 M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12 M9 7V4h6v3"],
    "film":    ["", "M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z "
                    "M8 4v16 M16 4v16 M4 9h4 M4 15h4 M16 9h4 M16 15h4"],
    "keys":    ["", "M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z "
                    "M7 10h.01 M11 10h.01 M15 10h.01 M8 14h8"],
}


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def fmt_time(ms, sep=":"):
    s = max(0, int(ms // 1000))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}{sep}{m:02d}{sep}{s:02d}" if h else f"{m}{sep}{s:02d}"


class Backend(QObject):
    recentsChanged = Signal()

    def __init__(self, initial_files):
        super().__init__()
        self._s = QSettings(APP_NAME, "NovaPlayer")
        self._initial = initial_files

    # ---------- fichiers ----------
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
                    files = [f for f in p.iterdir()
                             if f.is_file() and f.suffix.lower() in VIDEO_EXT]
                    files.sort(key=lambda f: natural_key(f.name))
                    out += [str(f) for f in files]
                elif p.is_file():
                    out.append(str(p))
            except OSError:
                pass
        return out

    @Slot(str, result=str)
    def toUrl(self, path):
        return QUrl.fromLocalFile(path).toString()

    @Slot(str, result=str)
    def displayName(self, path):
        return Path(path).stem

    def _get_initial(self):
        return self._initial

    initialFiles = Property("QVariantList", _get_initial, constant=True)

    # ---------- reprise de lecture ----------
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
        if pos > 10_000 and pos < dur - 15_000:
            self._s.setValue(self._key(path), int(pos))
        else:
            self._s.remove(self._key(path))

    @Slot(str)
    def clearResume(self, path):
        if path:
            self._s.remove(self._key(path))

    # ---------- récents ----------
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

    # ---------- volume ----------
    @Slot(result=float)
    def getVolume(self):
        try:
            return float(self._s.value("volume", 0.8))
        except (TypeError, ValueError):
            return 0.8

    @Slot(float)
    def setVolume(self, v):
        self._s.setValue("volume", float(v))

    # ---------- capture d'écran ----------
    @Slot(QObject, str, int, result=str)
    def screenshot(self, sink, name, pos):
        try:
            frame = sink.videoFrame()
            if not frame.isValid():
                return ""
            img = frame.toImage()
            if img.isNull():
                return ""
            folder = Path(QStandardPaths.writableLocation(
                QStandardPaths.PicturesLocation)) / APP_NAME
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
    minimumWidth: 760; minimumHeight: 460
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
    property bool menuOpen: speedPop.opened || trackPop.opened || helpPop.opened
    property bool showBars: hasMedia && (controlsVisible || !playing)
    readonly property var speeds: [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 3]

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
            layer.enabled: true
            layer.samples: 8
            layer.smooth: true
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
            color: b.active ? theme.accent : theme.text
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
        signal clicked()
        height: 46; radius: 13
        width: tbRow.implicitWidth + 40
        color: primary ? "transparent" : Qt.rgba(1, 1, 1, 0.06)
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
        Rectangle { anchors.fill: parent; radius: parent.radius; color: "white"; opacity: tma.containsMouse ? 0.08 : 0 }
        Row {
            id: tbRow
            anchors.centerIn: parent
            spacing: 9
            Icon { visible: tb.icon !== ""; name: tb.icon; width: 18; height: 18; color: "white"; anchors.verticalCenter: parent.verticalCenter }
            Text { text: tb.text; color: "white"; font.pixelSize: 14; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
        }
        MouseArea { id: tma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: tb.clicked() }
    }

    component MenuRow: Rectangle {
        id: mr
        property string text: ""
        property bool checked: false
        signal clicked()
        width: 230; height: 34; radius: 8
        color: mra.containsMouse ? Qt.rgba(0.545, 0.36, 0.965, 0.25) : "transparent"
        Text {
            anchors.left: parent.left; anchors.leftMargin: 12
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

    component DarkPopup: Popup {
        padding: 6
        margins: 8
        background: Rectangle { color: theme.panel2; radius: 12; border.color: Qt.rgba(1, 1, 1, 0.08) }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 } }
        exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 } }
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
    function poke() { controlsVisible = true; hideTimer.restart() }
    function togglePlay() {
        if (!hasMedia) { openDlg.open(); return }
        if (playing) { player.pause(); flash.show("pause") }
        else { player.play(); flash.show("play") }
        poke()
    }
    function seekBy(ms) {
        if (!hasMedia) return
        player.setPosition(Math.max(0, Math.min(player.duration, player.position + ms)))
        flash.show(ms > 0 ? "fwd" : "rew")
        toast.show((ms > 0 ? "+" : "−") + Math.abs(ms / 1000) + " s")
        poke()
    }
    function changeVolume(d) {
        audioOut.muted = false
        audioOut.volume = Math.max(0, Math.min(1, audioOut.volume + d))
        backend.setVolume(audioOut.volume)
        toast.show("Volume " + Math.round(audioOut.volume * 100) + " %")
    }
    function toggleMute() {
        audioOut.muted = !audioOut.muted
        toast.show(audioOut.muted ? "Son coupé" : "Son activé")
    }
    function toggleFull() {
        if (isFull) { if (wasMaximized) win.showMaximized(); else win.showNormal() }
        else { wasMaximized = (win.visibility === Window.Maximized); win.showFullScreen() }
    }
    function rateText(r) { return String(Math.round(r * 100) / 100).replace(".", ",") + "×" }
    function setSpeed(r) {
        player.playbackRate = r
        toast.show("Vitesse " + rateText(r))
    }
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
        player.setPosition(Math.max(0, player.position + dir * 1000 / fps))
        poke()
    }
    function addFiles(paths, playFirst) {
        if (!paths || paths.length === 0) { toast.show("Aucune vidéo trouvée"); return }
        var start = queue.count
        for (var i = 0; i < paths.length; i++)
            queue.append({ path: paths[i], name: backend.displayName(paths[i]) })
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
        if (player.position > 4000 || currentIndex <= 0) player.setPosition(0)
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
    }
    function clearQueue() { saveResume(); resetPlayer(); queue.clear() }
    function screenshot() {
        if (!hasMedia) return
        var p = backend.screenshot(videoOut.videoSink, currentName, player.position)
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

    // ------------------------------------------------------------ média
    ListModel { id: queue }

    MediaPlayer {
        id: player
        audioOutput: AudioOutput { id: audioOut; volume: backend.getVolume() }
        videoOutput: videoOut
        onMediaStatusChanged: {
            if ((mediaStatus === MediaPlayer.LoadedMedia || mediaStatus === MediaPlayer.BufferedMedia)
                    && win.pendingResume > 0) {
                var r = win.pendingResume
                win.pendingResume = -1
                if (r < player.duration - 15000) {
                    player.setPosition(r)
                    toast.show("Reprise à " + win.fmt(r))
                }
            } else if (mediaStatus === MediaPlayer.EndOfMedia) {
                backend.clearResume(win.currentPath)
                if (win.currentIndex + 1 < queue.count) win.playNext()
                else win.poke()
            }
        }
        onErrorOccurred: (error, errorString) => toast.show("Lecture impossible : " + errorString)
        onPlaybackStateChanged: {
            if (!win.playing) win.controlsVisible = true
            else hideTimer.restart()
        }
    }

    Timer {
        id: hideTimer
        interval: 2600
        onTriggered: {
            if (win.playing && !barHover.hovered && !win.menuOpen) win.controlsVisible = false
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
    Shortcut { sequence: "Ctrl+O"; onActivated: openDlg.open() }
    Shortcut { sequence: "H"; onActivated: helpPop.opened ? helpPop.close() : helpPop.open() }

    // ------------------------------------------------------------ interface
    Item {
        id: root
        anchors.fill: parent

        // ---------- file d'attente ----------
        Rectangle {
            id: panel
            anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.right: parent.right
            width: (win.playlistOpen && !win.isFull && win.hasMedia) ? 320 : 0
            Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
            clip: true
            color: theme.panel
            Rectangle { width: 1; anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; color: Qt.rgba(1, 1, 1, 0.06) }

            Item {
                width: 320
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

                ListView {
                    id: plView
                    anchors.top: plHeader.bottom; anchors.bottom: parent.bottom
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.leftMargin: 8; anchors.rightMargin: 8; anchors.bottomMargin: 8
                    clip: true
                    spacing: 2
                    model: queue
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
                            anchors.right: rm.left; anchors.rightMargin: 6
                            anchors.verticalCenter: parent.verticalCenter
                            text: row.name; elide: Text.ElideRight
                            color: row.current ? "white" : theme.text
                            font.pixelSize: 13
                            font.weight: row.current ? Font.DemiBold : Font.Normal
                        }
                        IconBtn {
                            id: rm
                            icon: "close"; size: 28; iconSize: 14
                            anchors.right: parent.right; anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            opacity: rowHover.hovered ? 1 : 0
                            onClicked: win.removeAt(row.index)
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
            VideoOutput { id: videoOut; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit }

            MouseArea {
                id: stageMouse
                anchors.fill: parent
                enabled: win.hasMedia
                hoverEnabled: true
                cursorShape: win.showBars ? Qt.ArrowCursor : Qt.BlankCursor
                onPositionChanged: win.poke()
                onClicked: clickTimer.restart()
                onDoubleClicked: { clickTimer.stop(); win.toggleFull() }
                onWheel: (wheel) => win.changeVolume(wheel.angleDelta.y > 0 ? 0.05 : -0.05)
            }
            Timer { id: clickTimer; interval: 220; onTriggered: win.togglePlay() }

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
                    onMoved: player.setPosition(value)
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
                            icon: (audioOut.muted || audioOut.volume === 0) ? "mute" : (audioOut.volume < 0.5 ? "vol_low" : "vol")
                            tip: "Couper le son (M)"
                            onClicked: win.toggleMute()
                        }
                        Slider {
                            id: volSlider
                            width: 96; height: 30
                            anchors.verticalCenter: parent.verticalCenter
                            from: 0; to: 1
                            value: audioOut.muted ? 0 : audioOut.volume
                            focusPolicy: Qt.NoFocus
                            onMoved: { audioOut.muted = false; audioOut.volume = value; backend.setVolume(value) }
                            background: Item {
                                x: volSlider.leftPadding
                                y: volSlider.topPadding + volSlider.availableHeight / 2 - 2
                                width: volSlider.availableWidth; height: 4
                                Rectangle { anchors.fill: parent; radius: 2; color: Qt.rgba(1, 1, 1, 0.2) }
                                Rectangle { width: volSlider.visualPosition * parent.width; height: 4; radius: 2; color: "white" }
                            }
                            handle: Rectangle {
                                x: volSlider.leftPadding + volSlider.visualPosition * volSlider.availableWidth - 6
                                y: volSlider.topPadding + volSlider.availableHeight / 2 - 6
                                width: 12; height: 12; radius: 6; color: "white"
                            }
                        }
                        Item { width: 12; height: 1 }
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
                            onClicked: trackPop.open()
                            DarkPopup {
                                id: trackPop
                                x: (parent.width - width) / 2
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
                                            onClicked: { player.activeAudioTrack = index; trackPop.close() }
                                        }
                                    }
                                    Text {
                                        visible: player.audioTracks.length === 0
                                        text: "Aucune piste"; color: theme.muted; font.pixelSize: 13
                                        leftPadding: 12; topPadding: 4; bottomPadding: 6
                                    }
                                    Item { width: 230; height: 9; Rectangle { anchors.centerIn: parent; width: parent.width - 16; height: 1; color: Qt.rgba(1, 1, 1, 0.07) } }
                                    MenuHeader { text: "SOUS-TITRES" }
                                    MenuRow {
                                        text: "Désactivés"
                                        checked: player.activeSubtitleTrack === -1
                                        onClicked: { player.activeSubtitleTrack = -1; trackPop.close() }
                                    }
                                    Repeater {
                                        model: player.subtitleTracks
                                        delegate: MenuRow {
                                            required property var modelData
                                            required property int index
                                            text: win.trackName(modelData, index)
                                            checked: player.activeSubtitleTrack === index
                                            onClicked: { player.activeSubtitleTrack = index; trackPop.close() }
                                        }
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
            Rectangle { anchors.fill: parent; color: theme.bg }
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeColor: "transparent"
                    fillGradient: RadialGradient {
                        centerX: empty.width * 0.5; centerY: empty.height * 0.32
                        focalX: centerX; focalY: centerY
                        centerRadius: Math.max(empty.width, empty.height) * 0.65
                        GradientStop { position: 0.0; color: "#388B5CF6" }
                        GradientStop { position: 0.45; color: "#12EC4899" }
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
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "MP4, MKV, AVI, MOV, WEBM… ou un dossier entier"; color: theme.muted; font.pixelSize: 14 }
                Item { width: 1; height: 30 }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 12
                    TextBtn { primary: true; icon: "folder"; text: "Ouvrir des vidéos"; onClicked: openDlg.open() }
                    TextBtn { text: "Ouvrir un dossier"; onClicked: folderDlg.open() }
                }
                Item { width: 1; height: 38 }
                Column {
                    width: parent.width
                    spacing: 2
                    visible: backend.recents.length > 0
                    Text { text: "RÉCENTS"; color: theme.muted; font.pixelSize: 11; font.letterSpacing: 1.4; font.weight: Font.DemiBold; leftPadding: 12; bottomPadding: 6 }
                    Repeater {
                        model: backend.recents
                        delegate: Rectangle {
                            id: rd
                            required property string modelData
                            width: parent.width; height: 42; radius: 10
                            color: rh.hovered ? Qt.rgba(1, 1, 1, 0.06) : "transparent"
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
                Item { width: 1; height: 22 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Appuie sur H pour voir les raccourcis clavier   ·   Nova v" + appVersion; color: theme.muted; opacity: 0.7; font.pixelSize: 12 }
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
                var paths = backend.expandUrls(drop.urls)
                win.addFiles(paths, true)
                drop.accept(Qt.CopyAction)
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
                        ["↑ / ↓ / molette", "Volume"],
                        ["M", "Couper le son"],
                        [", / ;", "Image par image"],
                        ["− / +", "Vitesse de lecture"],
                        ["S", "Capture d'écran"],
                        ["P", "File d'attente"],
                        ["N / B", "Vidéo suivante / précédente"],
                        ["Ctrl + O", "Ouvrir des vidéos"]
                    ]
                    delegate: Row {
                        required property var modelData
                        spacing: 12
                        Rectangle {
                            width: 128; height: 28; radius: 7
                            color: Qt.rgba(1, 1, 1, 0.07); border.color: Qt.rgba(1, 1, 1, 0.08)
                            Text { anchors.centerIn: parent; text: modelData[0]; color: theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                        }
                        Text { width: 190; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]; color: theme.muted; font.pixelSize: 13 }
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        if (startupMessage !== "") toast.show(startupMessage, 4000)
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
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
