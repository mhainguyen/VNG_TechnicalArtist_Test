#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Submission Folder Validator  -  single-file tool (PySide6 / PySide2 / PyQt5).

Run the UI:      python asset_validator.py
Maya QC:         done through mayapy; this SAME file is launched by mayapy with
                 "--worker" (Maya does not need to be open).

Edit the "PROJECT STANDARDS" section below to match your pipeline.
"""
import collections
import csv
import glob
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import traceback

# ==========================================================================
# PROJECT STANDARDS  (edit here)
# ==========================================================================
class cfg:
    # ---- Textures -------------------------------------------------------------
    TEXTURE_PREFIX = "T_"                 # the only part allowed to contain uppercase
    TEXTURE_EXTENSION = ".tga"
    TEXTURE_SUFFIXES = (                  # lowercase, without the leading "_"
        "albedo", "normal", "roughness", "metallic", "ao", "emissive", "opacity",
    )
    MAX_RESOLUTION = 2048                 # per side (width and height)

    # ---- Maya files -----------------------------------------------------------
    MAYA_PREFIX = "msh_"
    MAYA_EXTENSION = ".ma"

    # ---- FBX meshes -----------------------------------------------------------
    FBX_PREFIX = "SM_"                    # case-sensitive
    FBX_EXTENSION = ".fbx"
    FBX_REQUIRE_LOWERCASE = False         # True = everything after "SM_" must be lowercase
    FBX_RUN_MAYA_QC = True                # also check n-gons / UV sets / transforms (via mayapy)

    # ---- Maya QC (mayapy) -----------------------------------------------------
    MAX_FACE_SIDES = 4                    # faces must have < 5 sides (no n-gons)
    REQUIRED_UV_SETS = 1
    FREEZE_TOLERANCE = 1e-4
    IGNORED_HISTORY_NODE_TYPES = ("groupId", "tweak")

    # ---- File classification --------------------------------------------------
    TEXTURE_EXTS = {".tga", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp",
                    ".exr", ".hdr", ".psd", ".dds"}
    MAYA_EXTS = {".ma", ".mb"}

# ==========================================================================
# VALIDATION LOGIC  (naming / resolution / Maya QC result formatting)
# ==========================================================================
PASS, FAIL, WARN, SKIP, RUNNING = "PASS", "FAIL", "WARN", "SKIP", "RUNNING"

_ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


# --------------------------------------------------------------------------
# Scanning / classification
# --------------------------------------------------------------------------
def classify(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in cfg.TEXTURE_EXTS:
        return "texture"
    if ext in cfg.MAYA_EXTS:
        return "maya"
    if ext == cfg.FBX_EXTENSION:
        return "fbx"
    return "other"


def scan_folder(folder, recursive=True):
    files = []
    if recursive:
        for root, dirs, names in os.walk(folder):
            dirs.sort()
            for n in sorted(names):
                files.append(os.path.join(root, n))
    else:
        for n in sorted(os.listdir(folder)):
            p = os.path.join(folder, n)
            if os.path.isfile(p):
                files.append(p)
    return files


# --------------------------------------------------------------------------
# Naming
# --------------------------------------------------------------------------
def _name_reasons(stem, prefix, suffixes=None, lowercase=True):
    reasons = []
    if " " in stem:
        reasons.append("Invalid Name (contains spaces, use '_')")
    illegal = sorted({c for c in stem if c not in _ALLOWED and c != " "})
    if illegal:
        reasons.append("Invalid Name (illegal characters: %s)" % " ".join(illegal))

    # The prefix itself (e.g. "T_") is exempt from the lowercase rule.
    body = stem[len(prefix):] if stem.startswith(prefix) else stem
    if lowercase and body != body.lower():
        reasons.append("Invalid Name (must be lowercase)")
    if not stem.startswith(prefix):
        reasons.append("Invalid Name (missing prefix '%s')" % prefix)

    suffix = ""
    if suffixes is not None:
        suffix = stem.rsplit("_", 1)[-1].lower() if "_" in stem else ""
        if suffix not in suffixes:
            reasons.append("Invalid Name (suffix must be one of: %s)"
                           % ", ".join("_" + s for s in suffixes))

    if not reasons:
        core = stem[len(prefix):]
        if suffixes is not None:
            core = core[:-(len(suffix) + 1)]
        if not core.strip("_"):
            reasons.append("Invalid Name (missing asset name)")
    return reasons


def _ext_reasons(ext, expected):
    if ext.lower() != expected:
        return ["Invalid Format (expected %s, got %s)" % (expected, ext or "no extension")]
    if ext != ext.lower():
        return ["Invalid Name (extension must be lowercase)"]
    return []


# --------------------------------------------------------------------------
# Image size
# --------------------------------------------------------------------------
def is_pow2(n):
    return n > 0 and (n & (n - 1)) == 0


def read_image_size(path):
    """Return (w, h) for TGA/PNG, None for formats we don't parse."""
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as f:
        if ext == ".tga":
            h = f.read(18)
            if len(h) < 18:
                raise ValueError("file too small for a TGA header")
            if h[2] not in (1, 2, 3, 9, 10, 11):
                raise ValueError("invalid TGA image type %d" % h[2])
            w, ht = struct.unpack("<HH", h[12:16])
        elif ext == ".png":
            d = f.read(24)
            if len(d) < 24 or d[:8] != b"\x89PNG\r\n\x1a\n" or d[12:16] != b"IHDR":
                raise ValueError("invalid PNG header")
            w, ht = struct.unpack(">II", d[16:24])
        else:
            return None
    if w == 0 or ht == 0:
        raise ValueError("image has zero size")
    return w, ht


# --------------------------------------------------------------------------
# Per-file validation
# --------------------------------------------------------------------------
def validate_texture(path):
    stem, ext = os.path.splitext(os.path.basename(path))
    reasons = _ext_reasons(ext, cfg.TEXTURE_EXTENSION)
    reasons += _name_reasons(stem, cfg.TEXTURE_PREFIX, cfg.TEXTURE_SUFFIXES)

    info = ""
    try:
        size = read_image_size(path)
    except (OSError, ValueError) as e:
        reasons.append("Unreadable image (%s)" % e)
        size = None
    if size:
        w, h = size
        info = "%d x %d" % (w, h)
        if not (is_pow2(w) and is_pow2(h)):
            reasons.append("Not Power of 2 (%dx%d)" % (w, h))
        if w > cfg.MAX_RESOLUTION or h > cfg.MAX_RESOLUTION:
            reasons.append("Resolution too high (%dx%d, max %dx%d)"
                           % (w, h, cfg.MAX_RESOLUTION, cfg.MAX_RESOLUTION))
    elif not reasons:
        info = "n/a"
    return reasons, info


def validate_fbx_name(path):
    stem, ext = os.path.splitext(os.path.basename(path))
    reasons = _ext_reasons(ext, cfg.FBX_EXTENSION)
    reasons += _name_reasons(stem, cfg.FBX_PREFIX, lowercase=cfg.FBX_REQUIRE_LOWERCASE)
    return reasons


def validate_maya_name(path):
    stem, ext = os.path.splitext(os.path.basename(path))
    reasons = _ext_reasons(ext, cfg.MAYA_EXTENSION)
    reasons += _name_reasons(stem, cfg.MAYA_PREFIX)
    return reasons


def validate_file(path, root):
    """Static (name/format/resolution) validation. Returns a result dict."""
    kind = classify(os.path.basename(path))
    try:
        rel = os.path.relpath(path, root) if root else path
    except ValueError:
        rel = path
    r = {"path": path, "rel": rel, "kind": kind,
         "reasons": [], "warnings": [], "info": "", "running": False}
    if kind == "texture":
        r["reasons"], r["info"] = validate_texture(path)
    elif kind == "maya":
        r["reasons"] = validate_maya_name(path)
    elif kind == "fbx":
        r["reasons"] = validate_fbx_name(path)
    else:
        r["warnings"] = ["Unsupported file type (not validated)"]
    return r


def status_of(r):
    if r["kind"] == "other":
        return SKIP
    if r["running"]:
        return RUNNING
    if r["reasons"]:
        return FAIL
    if r["warnings"]:
        return WARN
    return PASS


# --------------------------------------------------------------------------
# Maya QC result -> human readable reasons
# --------------------------------------------------------------------------
def _short(items, limit=4):
    items = list(items)
    s = ", ".join(items[:limit])
    if len(items) > limit:
        s += " ...+%d more" % (len(items) - limit)
    return s


def maya_qc_reasons(qc):
    if qc.get("error"):
        return ["Maya QC: %s" % qc["error"]]
    reasons = []
    if not qc.get("meshes"):
        reasons.append("Maya QC: No mesh found in scene")
    if qc.get("history"):
        reasons.append("Maya QC: History not clean [%s]" % _short(qc["history"]))
    if qc.get("freeze"):
        reasons.append("Maya QC: Transforms not frozen [%s]" % _short(qc["freeze"]))
    if qc.get("ngons"):
        reasons.append("Maya QC: N-gons found [%s]"
                       % _short("%s: %d faces" % (n, c) for n, c in qc["ngons"]))
    if qc.get("uvsets"):
        reasons.append("Maya QC: UV sets != %d [%s]"
                       % (cfg.REQUIRED_UV_SETS,
                          _short("%s: %d" % (n, c) for n, c in qc["uvsets"])))
    return reasons

# ==========================================================================
# MAYA QC WORKER  (runs inside mayapy, no Qt)
# ==========================================================================
START, RESULT, DONE = "@@START@@", "@@RESULT@@", "@@DONE@@"

def emit(tag, payload=""):
    sys.stdout.write("\n%s%s\n" % (tag, payload))
    sys.stdout.flush()


def short(name):
    return name.split("|")[-1]


def check_file(path, cmds, om):
    res = {"path": path, "error": None, "meshes": 0,
           "history": [], "freeze": [], "ngons": [], "uvsets": []}

    is_fbx = os.path.splitext(path)[1].lower() == cfg.FBX_EXTENSION
    cmds.file(new=True, force=True)
    if is_fbx:
        try:
            if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
                cmds.loadPlugin("fbxmaya", quiet=True)
            cmds.file(path, i=True, type="FBX", ignoreVersion=True, options="fbx", pr=True)
        except RuntimeError as e:
            # Maya raises on harmless warnings too; only fail if no mesh arrived.
            if not cmds.ls(type="mesh"):
                res["error"] = "Cannot import FBX (%s)" % str(e).strip().splitlines()[0]
                return res
    else:
        try:
            cmds.file(path, open=True, force=True, ignoreVersion=True)
        except RuntimeError as e:
            # Maya raises on harmless warnings too; only fail if nothing loaded.
            if not cmds.file(query=True, sceneName=True):
                res["error"] = "Cannot open file (%s)" % str(e).strip().splitlines()[0]
                return res

    shapes = cmds.ls(type="mesh", long=True, noIntermediate=True) or []
    res["meshes"] = len(shapes)
    tol = cfg.FREEZE_TOLERANCE

    for shape in shapes:
        parents = cmds.listRelatives(shape, allParents=True, fullPath=True) or []
        label = short(parents[0]) if parents else short(shape)

        # 1) Clean history (any upstream node other than ignored types)
        hist = [] if is_fbx else (cmds.listHistory(shape, pruneDagObjects=True) or [])
        hist = [h for h in hist
                if cmds.nodeType(h) not in cfg.IGNORED_HISTORY_NODE_TYPES]
        if hist and label not in res["history"]:
            res["history"].append(label)

        # 2) Frozen transforms: T=0, R=0, S=1
        for t in parents:
            tr = cmds.getAttr(t + ".translate")[0]
            ro = cmds.getAttr(t + ".rotate")[0]
            sc = cmds.getAttr(t + ".scale")[0]
            if (any(abs(v) > tol for v in tuple(tr) + tuple(ro)) or
                    any(abs(v - 1.0) > tol for v in sc)):
                if short(t) not in res["freeze"]:
                    res["freeze"].append(short(t))

        # 3) N-gons: faces with more than MAX_FACE_SIDES vertices
        sel = om.MSelectionList()
        sel.add(shape)
        it = om.MItMeshPolygon(sel.getDagPath(0))
        count = 0
        while not it.isDone():
            if len(it.getVertices()) > cfg.MAX_FACE_SIDES:
                count += 1
            it.next()
        if count:
            res["ngons"].append([label, count])

        # 4) UV sets
        uv_sets = cmds.polyUVSet(shape, query=True, allUVSets=True) or []
        if len(uv_sets) != cfg.REQUIRED_UV_SETS:
            res["uvsets"].append([label, len(uv_sets)])

    return res


def run_worker(argv):
    with io.open(argv[2], "r", encoding="utf-8") as f:
        files = json.load(f)["files"]

    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    import maya.api.OpenMaya as om

    for path in files:
        emit(START, path)
        try:
            res = check_file(path, cmds, om)
        except Exception:
            res = {"path": path, "meshes": 0,
                   "error": "QC crashed: " + traceback.format_exc().strip().splitlines()[-1]}
        emit(RESULT, json.dumps(res))
    emit(DONE)

    try:
        maya.standalone.uninitialize()
    except Exception:
        pass


# Worker mode must be dispatched BEFORE any Qt import: mayapy only needs Maya.
if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[1] == "--worker":
    run_worker(sys.argv)
    sys.exit(0)


# ==========================================================================
# UI
# ==========================================================================
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
        Signal = QtCore.Signal
    except ImportError:
        from PyQt5 import QtCore, QtGui, QtWidgets
        Signal = QtCore.pyqtSignal

Qt = QtCore.Qt
WORKER = os.path.abspath(__file__)          # this same file is run by mayapy in --worker mode

STATUS_STYLE = {            # background, text colour, label
    PASS:    ("#c8e6c9", "#1b5e20", u"\u2714 PASS"),
    FAIL:    ("#ffcdd2", "#b71c1c", u"\u2718 FAIL"),
    WARN:    ("#ffe0b2", "#e65100", u"! WARN"),
    SKIP:    ("#eeeeee", "#616161", u"- SKIP"),
    RUNNING: ("#bbdefb", "#0d47a1", u"... RUNNING"),
}
KIND_LABEL = {"texture": "Texture", "maya": "Maya", "fbx": "FBX", "other": "Other"}
COLUMNS = ["Status", "Type", "File", "Resolution / Info", "Failure reason"]


# --------------------------------------------------------------------------
# mayapy discovery
# --------------------------------------------------------------------------
def find_mayapy():
    cands = []
    loc = os.environ.get("MAYA_LOCATION")
    if loc:
        cands += [os.path.join(loc, "bin", "mayapy.exe"), os.path.join(loc, "bin", "mayapy")]
    for pattern in (
        "C:/Program Files/Autodesk/Maya*/bin/mayapy.exe",
        "/usr/autodesk/maya*/bin/mayapy",
        "/Applications/Autodesk/maya*/Maya.app/Contents/bin/mayapy",
    ):
        cands += sorted(glob.glob(pattern), reverse=True)     # newest first
    on_path = shutil.which("mayapy")
    if on_path:
        cands.append(on_path)
    for c in cands:
        if os.path.isfile(c):
            return c
    return ""


# --------------------------------------------------------------------------
# Background thread running mayapy
# --------------------------------------------------------------------------
class MayaQCThread(QtCore.QThread):
    file_started = Signal(str)
    result_ready = Signal(dict)
    finished_info = Signal(str)          # "" = OK, otherwise an error message

    def __init__(self, mayapy, files, parent=None):
        super(MayaQCThread, self).__init__(parent)
        self.mayapy, self.files = mayapy, list(files)
        self.proc, self.stopped = None, False

    def stop(self):
        self.stopped = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def run(self):
        tmp, msg = None, ""
        try:
            fd, tmp = tempfile.mkstemp(prefix="qc_files_", suffix=".json")
            os.close(fd)
            with io.open(tmp, "w", encoding="utf-8") as f:
                f.write(json.dumps({"files": self.files}))
            env = dict(os.environ, PYTHONIOENCODING="utf-8", MAYA_DISABLE_CIP="1")
            kw = {"creationflags": 0x08000000} if os.name == "nt" else {}   # no console flash
            self.proc = subprocess.Popen(
                [self.mayapy, WORKER, "--worker", tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding="utf-8", errors="replace", env=env,
                cwd=os.path.dirname(WORKER), **kw)

            tail, done = collections.deque(maxlen=20), False
            for line in self.proc.stdout:
                line = line.rstrip()
                if RESULT in line:
                    try:
                        self.result_ready.emit(json.loads(line.split(RESULT, 1)[1]))
                    except ValueError:
                        tail.append(line)
                elif START in line:
                    self.file_started.emit(line.split(START, 1)[1])
                elif DONE in line:
                    done = True
                elif line.strip():
                    tail.append(line)
            rc = self.proc.wait()
            if not done and not self.stopped:
                msg = "mayapy exited before finishing (exit code %s).\n\n%s" % (rc, "\n".join(tail))
        except Exception as e:                                   # noqa
            msg = "Could not run mayapy:\n%s" % e
        finally:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        self.finished_info.emit(msg)


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Submission Folder Validator")
        self.resize(1150, 720)
        self.settings = QtCore.QSettings("SubmissionValidator", "AssetValidator")
        self.results, self.by_path, self.qc_thread, self.cancelled = [], {}, None, False
        self.selected_files = []          # non-empty = 'files mode' (picked files instead of a folder)
        self._build_ui()
        self._load_settings()

    # ---- UI ---------------------------------------------------------------
    def _build_ui(self):
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        lay = QtWidgets.QVBoxLayout(root)

        # folder row
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Folder / files:"))
        self.folder_edit = QtWidgets.QLineEdit()
        self.folder_edit.setPlaceholderText("Select a folder, or pick one or more files...")
        self.folder_edit.textEdited.connect(self._on_path_typed)
        row.addWidget(self.folder_edit, 1)
        b = QtWidgets.QPushButton("Browse Folder...")
        b.clicked.connect(self.on_browse)
        row.addWidget(b)
        b = QtWidgets.QPushButton("Select Files...")
        b.setToolTip("Pick one or more files (Ctrl/Shift+click for multiple)")
        b.clicked.connect(self.on_select_files)
        row.addWidget(b)
        self.recursive_cb = QtWidgets.QCheckBox("Include subfolders")
        self.recursive_cb.setChecked(True)
        row.addWidget(self.recursive_cb)
        lay.addLayout(row)

        # rules hint (generated from config)
        rules = QtWidgets.QLabel(
            "Textures: <b>%s&lt;name&gt;_(%s)%s</b>, power of 2, max %d px &nbsp;|&nbsp; "
            "Maya: <b>%s&lt;name&gt;%s</b>, FBX: <b>%s&lt;name&gt;%s</b> &nbsp;|&nbsp; "
            "QC: clean history, frozen transforms, no n-gons, %d UV set" % (
                cfg.TEXTURE_PREFIX, "|".join(cfg.TEXTURE_SUFFIXES), cfg.TEXTURE_EXTENSION,
                cfg.MAX_RESOLUTION, cfg.MAYA_PREFIX, cfg.MAYA_EXTENSION,
                cfg.FBX_PREFIX, cfg.FBX_EXTENSION, cfg.REQUIRED_UV_SETS))
        rules.setStyleSheet("color:#666; font-size:11px;")
        rules.setWordWrap(True)
        lay.addWidget(rules)

        # mayapy group
        self.maya_group = QtWidgets.QGroupBox("Maya QC via mayapy (Maya does not need to be open)")
        self.maya_group.setCheckable(True)
        g = QtWidgets.QHBoxLayout(self.maya_group)
        g.addWidget(QtWidgets.QLabel("mayapy:"))
        self.mayapy_edit = QtWidgets.QLineEdit()
        self.mayapy_edit.setPlaceholderText("Path to mayapy executable")
        g.addWidget(self.mayapy_edit, 1)
        b = QtWidgets.QPushButton("Browse...")
        b.clicked.connect(self.on_browse_mayapy)
        g.addWidget(b)
        b = QtWidgets.QPushButton("Auto-detect")
        b.clicked.connect(self.on_autodetect)
        g.addWidget(b)
        lay.addWidget(self.maya_group)

        # action row
        row = QtWidgets.QHBoxLayout()
        self.validate_btn = QtWidgets.QPushButton("Validate")
        self.validate_btn.setMinimumHeight(32)
        self.validate_btn.setStyleSheet("font-weight:bold;")
        self.validate_btn.clicked.connect(self.on_validate)
        row.addWidget(self.validate_btn)
        self.cancel_btn = QtWidgets.QPushButton("Cancel QC")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.on_cancel)
        row.addWidget(self.cancel_btn)
        self.export_btn = QtWidgets.QPushButton("Export CSV...")
        self.export_btn.clicked.connect(self.on_export)
        row.addWidget(self.export_btn)
        row.addStretch(1)
        row.addWidget(QtWidgets.QLabel("Show:"))
        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItems(["All files", "Failed only", "Passed only", "Warnings / Skipped"])
        self.filter_combo.currentIndexChanged.connect(self.refresh_table)
        row.addWidget(self.filter_combo)
        lay.addLayout(row)

        # progress
        self.progress = QtWidgets.QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v / %m")
        self.progress.setVisible(False)
        lay.addWidget(self.progress)
        self.status_label = QtWidgets.QLabel("")
        lay.addWidget(self.status_label)

        # table
        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)             # lines between rows and columns
        self.table.setStyleSheet("QTableWidget { gridline-color: #7a7a7a; } "
                                 "QTableWidget::item { padding: 4px 6px; }")
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(True)
        for i, w in enumerate((110, 70, 380, 130)):
            hh.setSectionResizeMode(i, QtWidgets.QHeaderView.Interactive)
            self.table.setColumnWidth(i, w)
        lay.addWidget(self.table, 1)

        # summary
        self.summary = QtWidgets.QLabel("No results yet.")
        self.summary.setStyleSheet("font-weight:bold; padding:4px;")
        lay.addWidget(self.summary)

    # ---- settings ---------------------------------------------------------
    def _load_settings(self):
        s = self.settings
        self.folder_edit.setText(s.value("folder", ""))
        self.recursive_cb.setChecked(s.value("recursive", "true") in (True, "true"))
        self.maya_group.setChecked(s.value("run_qc", "true") in (True, "true"))
        self.mayapy_edit.setText(s.value("mayapy", "") or find_mayapy())

    def _save_settings(self):
        s = self.settings
        if not self.selected_files:
            s.setValue("folder", self.folder_edit.text())
        s.setValue("recursive", self.recursive_cb.isChecked())
        s.setValue("run_qc", self.maya_group.isChecked())
        s.setValue("mayapy", self.mayapy_edit.text())

    # ---- browse buttons ---------------------------------------------------
    def on_browse(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select submission folder", self.folder_edit.text() or os.path.expanduser("~"))
        if d:
            self._set_files_mode([])
            self.folder_edit.setText(d)

    def _set_files_mode(self, files):
        self.selected_files = list(files)
        self.recursive_cb.setEnabled(not files)
        self.folder_edit.setToolTip("\n".join(files))

    def _on_path_typed(self, _text):
        # user typed/pasted a path by hand -> back to folder mode
        if self.selected_files:
            self._set_files_mode([])

    def on_select_files(self):
        cur = self.folder_edit.text().strip()
        if self.selected_files:
            start = os.path.dirname(self.selected_files[0])
        else:
            start = cur if os.path.isdir(cur) else os.path.expanduser("~")
        exts = " ".join("*" + e for e in sorted(cfg.MAYA_EXTS | cfg.TEXTURE_EXTS | {cfg.FBX_EXTENSION}))
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select files to validate", start,
            "Maya & texture files (%s);;All files (*)" % exts)
        if files:
            files = [os.path.normpath(f) for f in files]
            self._set_files_mode(files)
            self.folder_edit.setText(files[0] if len(files) == 1 else
                                     "%d files selected: %s" % (len(files), "; ".join(os.path.basename(f) for f in files)))

    def on_browse_mayapy(self):
        f, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select mayapy executable")
        if f:
            self.mayapy_edit.setText(f)

    def on_autodetect(self):
        p = find_mayapy()
        if p:
            self.mayapy_edit.setText(p)
        else:
            QtWidgets.QMessageBox.information(
                self, "mayapy", "Could not find mayapy automatically.\nPlease browse to it manually.")

    # ---- validation flow --------------------------------------------------
    def on_validate(self):
        if self.selected_files:                                   # ---- files mode
            paths = [p for p in self.selected_files if os.path.isfile(p)]
            if not paths:
                QtWidgets.QMessageBox.warning(self, "Files", "The selected files no longer exist.")
                return
            try:
                root = os.path.commonpath([os.path.dirname(p) for p in paths])
            except ValueError:                                    # files on different drives
                root = None
        else:                                                     # ---- folder mode
            root = os.path.normpath(self.folder_edit.text().strip())
            if not self.folder_edit.text().strip() or not os.path.isdir(root):
                QtWidgets.QMessageBox.warning(self, "Folder", "Please select a valid folder (or pick files) first.")
                return
            paths = scan_folder(root, self.recursive_cb.isChecked())
        self._save_settings()

        self.results = [validate_file(p, root) for p in paths]
        self.by_path = {r["path"]: r for r in self.results}
        if not self.results:
            self.refresh_table()
            QtWidgets.QMessageBox.information(self, "Folder", "No files found in this folder.")
            return

        maya_rows = [r for r in self.results
                     if r["kind"] == "maya" or (r["kind"] == "fbx" and cfg.FBX_RUN_MAYA_QC)]
        if maya_rows:
            mayapy = self.mayapy_edit.text().strip()
            if not self.maya_group.isChecked():
                self._warn_rows(maya_rows, "Maya QC not run (disabled)")
            elif not os.path.isfile(mayapy):
                self._warn_rows(maya_rows, "Maya QC not run (mayapy not found - set its path)")
                QtWidgets.QMessageBox.warning(
                    self, "mayapy", "mayapy was not found, so Maya QC was skipped.\n"
                                    "Set the path in the Maya QC box and validate again.")
            else:
                self._start_qc(mayapy, maya_rows)
        self.refresh_table()

    @staticmethod
    def _warn_rows(rows, text):
        for r in rows:
            r["warnings"].append(text)

    def _start_qc(self, mayapy, rows):
        for r in rows:
            r["running"] = True
        self.cancelled = False
        self.progress.setRange(0, len(rows))
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.status_label.setText("Starting mayapy (this can take a few seconds)...")
        self._set_busy(True)
        self.qc_thread = MayaQCThread(mayapy, [r["path"] for r in rows], self)
        self.qc_thread.file_started.connect(self.on_qc_started)
        self.qc_thread.result_ready.connect(self.on_qc_result)
        self.qc_thread.finished_info.connect(self.on_qc_finished)
        self.qc_thread.start()

    def _set_busy(self, busy):
        self.validate_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)

    def on_qc_started(self, path):
        self.status_label.setText("Maya QC: %s" % os.path.basename(path))

    def on_qc_result(self, qc):
        r = self.by_path.get(qc.get("path"))
        if r is None:
            return
        r["running"] = False
        r["reasons"] += maya_qc_reasons(qc)
        if not qc.get("error"):
            r["info"] = "%d mesh(es)" % qc.get("meshes", 0)
        self.progress.setValue(self.progress.value() + 1)
        self.refresh_table()

    def on_qc_finished(self, msg):
        for r in self.results:
            if r["running"]:
                r["running"] = False
                if self.cancelled:
                    r["warnings"].append("Maya QC cancelled")
                else:
                    r["reasons"].append("Maya QC: no result returned")
        self.progress.setVisible(False)
        self.status_label.setText("Maya QC cancelled." if self.cancelled else "Done.")
        self._set_busy(False)
        self.refresh_table()
        if msg and not self.cancelled:
            QtWidgets.QMessageBox.critical(self, "Maya QC error", msg)

    def on_cancel(self):
        if self.qc_thread:
            self.cancelled = True
            self.qc_thread.stop()

    # ---- table ------------------------------------------------------------
    def refresh_table(self):
        mode = self.filter_combo.currentIndex()
        keep = {0: None, 1: (FAIL,), 2: (PASS,), 3: (WARN, SKIP)}[mode]
        rows = [r for r in self.results if keep is None or status_of(r) in keep]

        t = self.table
        t.setSortingEnabled(False)
        t.setRowCount(len(rows))
        bold = QtGui.QFont()
        bold.setBold(True)
        for i, r in enumerate(rows):
            st = status_of(r)
            bg, fg, label = STATUS_STYLE[st]
            if st == RUNNING:
                reason = "Running Maya QC..."
            elif st == PASS:
                reason = "OK"
            else:
                reason = "\n".join(r["reasons"] + r["warnings"])
            for c, text in enumerate((label, KIND_LABEL[r["kind"]], r["rel"], r["info"], reason)):
                item = QtWidgets.QTableWidgetItem(text)
                item.setBackground(QtGui.QBrush(QtGui.QColor(bg)))
                item.setForeground(QtGui.QBrush(QtGui.QColor(fg)))
                if c == 0:
                    item.setFont(bold)
                item.setToolTip(r["path"] if c == 2 else text)
                t.setItem(i, c, item)
        t.setSortingEnabled(True)
        t.resizeRowsToContents()      # after sorting so heights match rows

        n = collections.Counter(status_of(r) for r in self.results)
        self.summary.setText("Total: %d   |   Passed: %d   |   Failed: %d   |   Warnings: %d   |   Skipped: %d"
                             % (len(self.results), n[PASS], n[FAIL], n[WARN], n[SKIP]))

    # ---- export -----------------------------------------------------------
    def on_export(self):
        if not self.results:
            QtWidgets.QMessageBox.information(self, "Export", "Nothing to export yet.")
            return
        f, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export report", "validation_report.csv", "CSV (*.csv)")
        if not f:
            return
        with io.open(f, "w", encoding="utf-8-sig", newline="") as fh:   # BOM so Excel reads UTF-8
            w = csv.writer(fh)
            w.writerow(["Status", "Type", "File", "Info", "Reasons"])
            for r in self.results:
                w.writerow([status_of(r), KIND_LABEL[r["kind"]], r["rel"], r["info"],
                            " | ".join(r["reasons"] + r["warnings"])])

    def closeEvent(self, e):
        if self.qc_thread and self.qc_thread.isRunning():
            self.cancelled = True
            self.qc_thread.stop()
            self.qc_thread.wait(3000)
        self._save_settings()
        super(MainWindow, self).closeEvent(e)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec() if hasattr(app, "exec") else app.exec_())


if __name__ == "__main__":
    main()
