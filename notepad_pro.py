# NotepadX Pro 2.0 — IDE-grade editor
# pip install PyQt6 QScintilla
#
# Features over v1.0:
#   - 15+ language lexers (auto-detected by extension)
#   - File explorer sidebar
#   - Find & Replace panel (regex / case / whole-word)
#   - Code folding
#   - Bracket matching
#   - Catppuccin dark theme throughout
#   - Git status bar (branch + dirty indicator)
#   - Git status / diff / log dialogs
#   - Integrated terminal (QProcess)
#   - Minimap (scaled QsciScintilla clone)
#   - Tab dirty indicator (●) + close confirmation
#   - Command palette (Ctrl+Shift+P)
#   - Zoom in / out / reset
#   - Word wrap toggle
#   - Duplicate line, move line up/down, toggle comment
#   - Save All + Autosave
#   - Ln/Col + word count + language + git in status bar
#   - 100-char edge guide
#   - JetBrains Mono → Cascadia Code → Consolas font fallback

import sys
import os
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QSplitter, QTreeView,
    QTextEdit, QLineEdit, QPushButton, QLabel,
    QCheckBox, QFrame, QDialog, QListWidget,
    QListWidgetItem
)
from PyQt6.QtGui import QAction, QFont, QColor, QPalette, QFileSystemModel
from PyQt6.QtCore import QTimer, Qt, QProcess, QDir, QModelIndex, QSize, pyqtSignal

from PyQt6.Qsci import (
    QsciScintilla, QsciLexerPython, QsciLexerJavaScript,
    QsciLexerHTML, QsciLexerCSS, QsciLexerCPP,
    QsciLexerSQL, QsciLexerBash, QsciLexerXML,
)

# ── Optional lexers (not all QScintilla builds ship these) ──────────────────
LEXER_MAP: dict[str, type] = {
    ".py":   QsciLexerPython,
    ".js":   QsciLexerJavaScript,
    ".ts":   QsciLexerJavaScript,
    ".jsx":  QsciLexerJavaScript,
    ".tsx":  QsciLexerJavaScript,
    ".mjs":  QsciLexerJavaScript,
    ".html": QsciLexerHTML,
    ".htm":  QsciLexerHTML,
    ".css":  QsciLexerCSS,
    ".cpp":  QsciLexerCPP,
    ".c":    QsciLexerCPP,
    ".h":    QsciLexerCPP,
    ".hpp":  QsciLexerCPP,
    ".sql":  QsciLexerSQL,
    ".sh":   QsciLexerBash,
    ".bash": QsciLexerBash,
    ".xml":  QsciLexerXML,
    ".svg":  QsciLexerXML,
}

for _mod, _ext, _cls in [
    ("QsciLexerJSON",     ".json", None),
    ("QsciLexerMarkdown", ".md",   None),
    ("QsciLexerRuby",     ".rb",   None),
    ("QsciLexerPerl",     ".pl",   None),
]:
    try:
        import importlib
        _obj = getattr(__import__("PyQt6.Qsci", fromlist=[_mod]), _mod)
        LEXER_MAP[_ext] = _obj
    except Exception:
        pass


# ── Catppuccin Mocha palette ─────────────────────────────────────────────────
C = {
    "base":    QColor(30,  30,  46),
    "mantle":  QColor(24,  24,  37),
    "crust":   QColor(17,  17,  27),
    "surface0":QColor(49,  50,  68),
    "surface1":QColor(69,  71,  90),
    "overlay0":QColor(108, 112, 134),
    "text":    QColor(205, 214, 244),
    "subtext0":QColor(166, 173, 200),
    "blue":    QColor(137, 180, 250),
    "sky":     QColor(137, 220, 235),
    "green":   QColor(166, 227, 161),
    "red":     QColor(243, 139, 168),
    "yellow":  QColor(249, 226, 175),
    "mauve":   QColor(203, 166, 247),
    "peach":   QColor(250, 179, 135),
}


def apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          C["base"])
    p.setColor(QPalette.ColorRole.WindowText,      C["text"])
    p.setColor(QPalette.ColorRole.Base,            C["mantle"])
    p.setColor(QPalette.ColorRole.AlternateBase,   C["crust"])
    p.setColor(QPalette.ColorRole.ToolTipBase,     C["base"])
    p.setColor(QPalette.ColorRole.ToolTipText,     C["text"])
    p.setColor(QPalette.ColorRole.Text,            C["text"])
    p.setColor(QPalette.ColorRole.Button,          C["surface0"])
    p.setColor(QPalette.ColorRole.ButtonText,      C["text"])
    p.setColor(QPalette.ColorRole.Link,            C["blue"])
    p.setColor(QPalette.ColorRole.Highlight,       C["surface1"])
    p.setColor(QPalette.ColorRole.HighlightedText, C["text"])
    p.setColor(QPalette.ColorRole.Light,           C["surface0"])
    app.setPalette(p)


# ── Editor ────────────────────────────────────────────────────────────────────
class Editor(QsciScintilla):
    def __init__(self, path: str | None = None, parent=None):
        super().__init__(parent)
        self.path = path
        self.modified = False

        # Font fallback chain
        font = None
        for family in ("JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas"):
            f = QFont(family, 12)
            if f.exactMatch() or family == "Consolas":
                font = f
                break
        self.setFont(font)

        # ── Colors ──────────────────────────────────────────────────────────
        self.setPaper(C["base"])
        self.setColor(C["text"])
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(C["mantle"])
        self.setCaretForegroundColor(C["blue"])
        self.setMarginsBackgroundColor(C["crust"])
        self.setMarginsForegroundColor(C["overlay0"])
        self.setSelectionBackgroundColor(C["surface1"])

        # ── Margins ─────────────────────────────────────────────────────────
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "00000 ")

        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 14)
        self.setMarginSensitivity(1, True)
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle, 1)
        self.setFoldMarginColors(C["crust"], C["crust"])

        # ── Editing helpers ──────────────────────────────────────────────────
        self.setAutoIndent(True)
        self.setIndentationGuides(True)
        self.setIndentationGuidesBackgroundColor(C["surface0"])
        self.setIndentationGuidesForegroundColor(C["surface1"])
        self.setTabWidth(4)
        self.setIndentationsUseTabs(False)

        # ── Bracket matching ────────────────────────────────────────────────
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setMatchedBraceBackgroundColor(C["surface1"])
        self.setMatchedBraceForegroundColor(C["sky"])
        self.setUnmatchedBraceBackgroundColor(QColor(80, 30, 40))
        self.setUnmatchedBraceForegroundColor(C["red"])

        # ── Edge column ─────────────────────────────────────────────────────
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(100)
        self.setEdgeColor(C["surface0"])

        # ── Scroll ──────────────────────────────────────────────────────────
        self.setScrollWidth(1)
        self.setScrollWidthTracking(True)

        self.apply_lexer()
        self.textChanged.connect(lambda: setattr(self, "modified", True))

    def apply_lexer(self):
        if not self.path:
            return
        ext = Path(self.path).suffix.lower()
        cls = LEXER_MAP.get(ext)
        if cls:
            lexer = cls(self)
            lexer.setDefaultFont(self.font())
            lexer.setDefaultPaper(C["base"])
            lexer.setDefaultColor(C["text"])
            self.setLexer(lexer)

    # ── Editing commands ────────────────────────────────────────────────────
    def zoom_in_text(self):   self.zoomIn(1)
    def zoom_out_text(self):  self.zoomOut(1)
    def zoom_reset(self):     self.zoomTo(0)

    def toggle_word_wrap(self):
        nw = QsciScintilla.WrapMode.WrapNone
        ww = QsciScintilla.WrapMode.WrapWord
        self.setWrapMode(ww if self.wrapMode() == nw else nw)

    def duplicate_line(self):
        self.SendScintilla(QsciScintilla.SCI_LINEDUPLICATE)

    def move_line_up(self):
        self.SendScintilla(QsciScintilla.SCI_MOVESELECTEDLINESUP)

    def move_line_down(self):
        self.SendScintilla(QsciScintilla.SCI_MOVESELECTEDLINESDOWN)

    def toggle_comment(self):
        line, _ = self.getCursorPosition()
        raw = self.text(line)
        stripped = raw.lstrip()
        indent = len(raw) - len(stripped)
        if stripped.startswith("# "):
            new = raw[:indent] + stripped[2:]
        elif stripped.startswith("#"):
            new = raw[:indent] + stripped[1:]
        else:
            new = raw[:indent] + "# " + stripped
        self.setSelection(line, 0, line, len(raw))
        self.replaceSelectedText(new)


# ── Find & Replace panel ──────────────────────────────────────────────────────
class FindReplacePanel(QWidget):
    def __init__(self, get_editor, parent=None):
        super().__init__(parent)
        self.get_editor = get_editor
        self.setVisible(False)
        self.setStyleSheet(f"""
            QWidget      {{ background: {C['crust'].name()}; border-top: 1px solid {C['surface0'].name()}; }}
            QLineEdit    {{ background: {C['surface0'].name()}; border: 1px solid {C['surface1'].name()};
                           border-radius: 4px; padding: 4px 8px; color: {C['text'].name()};
                           font-size: 12px; min-width: 190px; }}
            QLineEdit:focus {{ border-color: {C['blue'].name()}; }}
            QPushButton  {{ background: {C['surface0'].name()}; border: 1px solid {C['surface1'].name()};
                           border-radius: 4px; padding: 4px 12px; color: {C['text'].name()};
                           font-size: 11px; }}
            QPushButton:hover   {{ background: {C['surface1'].name()}; }}
            QPushButton:pressed {{ background: {C['overlay0'].name()}; }}
            QCheckBox {{ color: {C['subtext0'].name()}; font-size: 11px; }}
            QLabel    {{ color: {C['subtext0'].name()}; font-size: 11px; }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(6)

        lay.addWidget(QLabel("Find:"))
        self.find_in = QLineEdit()
        self.find_in.setPlaceholderText("Search…")
        self.find_in.returnPressed.connect(self.find_next)
        lay.addWidget(self.find_in)

        lay.addWidget(QLabel("Replace:"))
        self.repl_in = QLineEdit()
        self.repl_in.setPlaceholderText("Replace with…")
        lay.addWidget(self.repl_in)

        self.cb_case  = QCheckBox("Case")
        self.cb_word  = QCheckBox("Word")
        self.cb_regex = QCheckBox("Regex")
        for cb in (self.cb_case, self.cb_word, self.cb_regex):
            lay.addWidget(cb)

        lay.addSpacing(6)
        for label, fn in [("▲", self.find_prev), ("▼", self.find_next),
                          ("Replace", self.replace_one), ("Replace All", self.replace_all)]:
            b = QPushButton(label); b.clicked.connect(fn); lay.addWidget(b)

        self.lbl = QLabel("")
        lay.addWidget(self.lbl)
        lay.addStretch()

        close = QPushButton("✕")
        close.setFixedWidth(28)
        close.clicked.connect(self.hide)
        lay.addWidget(close)

    def show_panel(self):
        self.setVisible(True)
        self.find_in.setFocus()
        self.find_in.selectAll()

    def _search(self, forward=True) -> bool:
        ed = self.get_editor()
        if not ed:
            return False
        term = self.find_in.text()
        if not term:
            return False
        found = ed.findFirst(term, self.cb_regex.isChecked(),
                             self.cb_case.isChecked(), self.cb_word.isChecked(),
                             True, forward)
        self.lbl.setText("" if found else "Not found")
        return found

    def find_next(self): self._search(True)
    def find_prev(self): self._search(False)

    def replace_one(self):
        ed = self.get_editor()
        if not ed: return
        if ed.hasSelectedText():
            ed.replaceSelectedText(self.repl_in.text())
        self.find_next()

    def replace_all(self):
        ed = self.get_editor()
        if not ed: return
        term = self.find_in.text()
        if not term: return
        ed.setCursorPosition(0, 0)
        n = 0
        while ed.findFirst(term, self.cb_regex.isChecked(),
                           self.cb_case.isChecked(), self.cb_word.isChecked(), False):
            ed.replaceSelectedText(self.repl_in.text())
            n += 1
        self.lbl.setText(f"Replaced {n}")


# ── Minimap ───────────────────────────────────────────────────────────────────
class Minimap(QsciScintilla):
    """Scaled-down read-only editor clone used for file navigation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFixedWidth(100)
        self.setFont(QFont("Consolas", 1))
        for i in range(5):
            self.setMarginWidth(i, 0)
        self.setPaper(C["crust"])
        self.setColor(C["overlay0"])
        self.setCaretLineVisible(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def sync(self, text: str):
        self.setText(text)

    def mousePressEvent(self, _):
        pass   # intentionally non-interactive (navigation coming in v3 👀)


# ── Terminal panel ────────────────────────────────────────────────────────────
class TerminalPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        mono = "font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px;"
        self.setStyleSheet(f"""
            QWidget   {{ background: {C['crust'].name()}; }}
            QTextEdit {{ background: {C['crust'].name()}; color: {C['text'].name()};
                        {mono} border: none; }}
            QLineEdit {{ background: {C['surface0'].name()}; color: {C['green'].name()};
                        {mono} border: none; border-top: 1px solid {C['surface1'].name()};
                        padding: 4px 8px; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.out = QTextEdit(); self.out.setReadOnly(True)
        lay.addWidget(self.out)

        self.inp = QLineEdit()
        self.inp.setPlaceholderText("$ command…")
        self.inp.returnPressed.connect(self.run)
        lay.addWidget(self.inp)

        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._stdout)
        self.proc.readyReadStandardError.connect(self._stderr)
        self.proc.finished.connect(lambda code, _: self._append(
            f'<span style="color:{C["overlay0"].name()}">exit {code}</span>', code != 0))
        self.cwd = os.path.expanduser("~")

    def run(self):
        cmd = self.inp.text().strip()
        if not cmd: return
        self.inp.clear()
        self._append(f'<span style="color:{C["blue"].name()}">$ {cmd}</span>')
        if cmd.startswith("cd "):
            try:
                nd = os.path.realpath(os.path.join(self.cwd, cmd[3:].strip()))
                os.chdir(nd); self.cwd = nd
            except Exception as e:
                self._append(f'<span style="color:{C["red"].name()}">{e}</span>')
            return
        self.proc.setWorkingDirectory(self.cwd)
        self.proc.start("bash", ["-c", cmd])

    def _stdout(self):
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._append(f'<pre style="margin:0;color:{C["text"].name()}">{data}</pre>')

    def _stderr(self):
        data = bytes(self.proc.readAllStandardError()).decode("utf-8", errors="replace")
        self._append(f'<pre style="margin:0;color:{C["red"].name()}">{data}</pre>')

    def _append(self, html: str, _=False):
        self.out.append(html)
        self.out.verticalScrollBar().setValue(self.out.verticalScrollBar().maximum())


# ── Command palette ───────────────────────────────────────────────────────────
class CommandPalette(QDialog):
    command_selected = pyqtSignal(str)

    def __init__(self, commands: list[str], parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.commands = commands
        self.setFixedWidth(520)
        self.setStyleSheet(f"""
            QDialog    {{ background: {C['base'].name()}; border: 1px solid {C['blue'].name()};
                         border-radius: 8px; }}
            QLineEdit  {{ background: {C['surface0'].name()}; border: none;
                         border-bottom: 1px solid {C['surface1'].name()};
                         padding: 12px 16px; color: {C['text'].name()}; font-size: 14px; }}
            QListWidget {{ background: {C['base'].name()}; border: none;
                           color: {C['text'].name()}; font-size: 13px; }}
            QListWidget::item         {{ padding: 8px 16px; }}
            QListWidget::item:selected{{ background: {C['surface0'].name()};
                                         color: {C['blue'].name()}; }}
            QListWidget::item:hover   {{ background: {C['mantle'].name()}; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.search = QLineEdit(); self.search.setPlaceholderText("Type a command…")
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)

        self.lst = QListWidget()
        self.lst.itemActivated.connect(self._emit)
        lay.addWidget(self.lst)

        self._filter("")
        self.search.installEventFilter(self)

    def _filter(self, text: str):
        self.lst.clear()
        for cmd in self.commands:
            if text.lower() in cmd.lower():
                self.lst.addItem(QListWidgetItem(cmd))
        if self.lst.count():
            self.lst.setCurrentRow(0)
        self.setFixedHeight(min(self.lst.count() * 37 + 52, 420))

    def _emit(self, item):
        self.command_selected.emit(item.text())
        self.close()

    def eventFilter(self, obj, event):
        if obj is self.search and event.type() == event.Type.KeyPress:
            k = event.key()
            if k == Qt.Key.Key_Down:
                self.lst.setCurrentRow(min(self.lst.currentRow() + 1, self.lst.count() - 1))
                return True
            if k == Qt.Key.Key_Up:
                self.lst.setCurrentRow(max(self.lst.currentRow() - 1, 0))
                return True
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.lst.currentItem()
                if item: self._emit(item)
                return True
        return super().eventFilter(obj, event)


# ── Main window ───────────────────────────────────────────────────────────────
class NotepadXPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NotepadX Pro 2.0")
        self.resize(1440, 900)
        self.file_paths: dict[Editor, str | None] = {}
        self._mm_timer = QTimer(); self._mm_timer.setSingleShot(True)
        self._mm_timer.timeout.connect(self._sync_minimap)

        self._build_ui()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        self._register_commands()
        self.new_tab()

        QTimer(self, timeout=self._autosave, interval=30_000).start()
        QTimer(self, timeout=self._update_status, interval=500).start()

    # ── UI ──────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # Vertical split: editor area / terminal
        self.v_split = QSplitter(Qt.Orientation.Vertical)

        # Horizontal split: file tree / tabs+minimap
        self.h_split = QSplitter(Qt.Orientation.Horizontal)

        # File tree
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(QDir.homePath())
        self.tree = QTreeView()
        self.tree.setModel(self.fs_model)
        self.tree.setRootIndex(self.fs_model.index(QDir.homePath()))
        for col in (1, 2, 3): self.tree.setColumnHidden(col, True)
        self.tree.header().hide()
        self.tree.setFixedWidth(220)
        self.tree.doubleClicked.connect(self._tree_open)
        self.tree.setStyleSheet(f"""
            QTreeView {{ background: {C['mantle'].name()}; color: {C['text'].name()};
                        border: none; font-size: 12px; }}
            QTreeView::item:hover    {{ background: {C['surface0'].name()}; }}
            QTreeView::item:selected {{ background: {C['surface0'].name()};
                                        color: {C['blue'].name()}; }}
        """)
        self.h_split.addWidget(self.tree)

        # Tabs + minimap container
        tab_area = QWidget()
        tab_lay = QVBoxLayout(tab_area)
        tab_lay.setContentsMargins(0, 0, 0, 0)
        tab_lay.setSpacing(0)

        tab_mini = QSplitter(Qt.Orientation.Horizontal)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_change)
        tab_mini.addWidget(self.tabs)

        self.minimap = Minimap()
        tab_mini.addWidget(self.minimap)
        tab_mini.setStretchFactor(0, 1)
        tab_mini.setStretchFactor(1, 0)
        tab_lay.addWidget(tab_mini, 1)

        # Find/Replace panel
        self.find_panel = FindReplacePanel(self.current_editor)
        tab_lay.addWidget(self.find_panel)

        self.h_split.addWidget(tab_area)
        self.h_split.setStretchFactor(1, 1)

        # Terminal
        self.terminal = TerminalPanel()
        self.terminal.setVisible(False)

        self.v_split.addWidget(self.h_split)
        self.v_split.addWidget(self.terminal)
        self.v_split.setStretchFactor(0, 3)
        self.v_split.setStretchFactor(1, 1)

        root_lay.addWidget(self.v_split)

    def _build_menus(self):
        mb = self.menuBar()
        def act(menu, name, fn, sc=None):
            a = QAction(name, self); a.triggered.connect(fn)
            if sc: a.setShortcut(sc)
            menu.addAction(a)

        f = mb.addMenu("File")
        act(f, "New Tab",     self.new_tab,   "Ctrl+N")
        act(f, "Open…",       self.open_file, "Ctrl+O")
        f.addSeparator()
        act(f, "Save",        self.save_file, "Ctrl+S")
        act(f, "Save As…",    self.save_as,   "Ctrl+Shift+S")
        act(f, "Save All",    self.save_all)
        f.addSeparator()
        act(f, "Close Tab",   lambda: self._close_tab(self.tabs.currentIndex()), "Ctrl+W")

        e = mb.addMenu("Edit")
        act(e, "Undo",           lambda: self.current_editor() and self.current_editor().undo(), "Ctrl+Z")
        act(e, "Redo",           lambda: self.current_editor() and self.current_editor().redo(), "Ctrl+Y")
        e.addSeparator()
        act(e, "Find & Replace", self.find_panel.show_panel, "Ctrl+H")
        act(e, "Find Next",      self.find_panel.find_next, "F3")
        act(e, "Find Prev",      self.find_panel.find_prev, "Shift+F3")
        e.addSeparator()
        act(e, "Duplicate Line",  lambda: self.current_editor() and self.current_editor().duplicate_line(), "Ctrl+D")
        act(e, "Move Line Up",    lambda: self.current_editor() and self.current_editor().move_line_up(), "Alt+Up")
        act(e, "Move Line Down",  lambda: self.current_editor() and self.current_editor().move_line_down(), "Alt+Down")
        act(e, "Toggle Comment",  lambda: self.current_editor() and self.current_editor().toggle_comment(), "Ctrl+/")

        v = mb.addMenu("View")
        act(v, "Zoom In",          lambda: self.current_editor() and self.current_editor().zoom_in_text(), "Ctrl+=")
        act(v, "Zoom Out",         lambda: self.current_editor() and self.current_editor().zoom_out_text(), "Ctrl+-")
        act(v, "Reset Zoom",       lambda: self.current_editor() and self.current_editor().zoom_reset(), "Ctrl+0")
        v.addSeparator()
        act(v, "Toggle Word Wrap", lambda: self.current_editor() and self.current_editor().toggle_word_wrap())
        act(v, "Toggle Sidebar",   self._toggle_tree)
        act(v, "Toggle Minimap",   self._toggle_minimap)
        act(v, "Toggle Terminal",  self._toggle_terminal, "Ctrl+`")

        g = mb.addMenu("Git")
        act(g, "Status",           self._git_status)
        act(g, "Diff Current File",self._git_diff)
        act(g, "Log (graph)",      self._git_log)

        t = mb.addMenu("Tools")
        act(t, "Command Palette",  self._show_palette, "Ctrl+Shift+P")

    def _build_toolbar(self):
        tb = QToolBar(); tb.setMovable(False)
        self.addToolBar(tb)
        for name, fn in [("New", self.new_tab), ("Open", self.open_file),
                          ("Save", self.save_file), ("|", None),
                          ("Find/Replace", self.find_panel.show_panel),
                          ("Terminal", self._toggle_terminal),
                          ("⌨ Palette", self._show_palette)]:
            if name == "|":
                tb.addSeparator(); continue
            a = QAction(name, self); a.triggered.connect(fn); tb.addAction(a)

    def _build_statusbar(self):
        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.lbl_pos   = QLabel("Ln 1, Col 1")
        self.lbl_words = QLabel("Words: 0")
        self.lbl_lang  = QLabel("Plain Text")
        self.lbl_git   = QLabel("")
        self.lbl_enc   = QLabel("UTF-8")
        def sep():
            f = QFrame(); f.setFrameShape(QFrame.Shape.VLine)
            f.setStyleSheet(f"color: {C['surface1'].name()};"); return f
        for w in (self.lbl_pos, sep(), self.lbl_words, sep(),
                  self.lbl_lang, sep(), self.lbl_git, sep(), self.lbl_enc):
            self.status.addPermanentWidget(w)

    def _register_commands(self):
        self.COMMANDS: dict[str, callable] = {
            "New Tab":            self.new_tab,
            "Open File":          self.open_file,
            "Save":               self.save_file,
            "Save As":            self.save_as,
            "Save All":           self.save_all,
            "Find & Replace":     self.find_panel.show_panel,
            "Toggle Terminal":    self._toggle_terminal,
            "Toggle Sidebar":     self._toggle_tree,
            "Toggle Minimap":     self._toggle_minimap,
            "Toggle Word Wrap":   lambda: self.current_editor() and self.current_editor().toggle_word_wrap(),
            "Duplicate Line":     lambda: self.current_editor() and self.current_editor().duplicate_line(),
            "Toggle Comment":     lambda: self.current_editor() and self.current_editor().toggle_comment(),
            "Zoom In":            lambda: self.current_editor() and self.current_editor().zoom_in_text(),
            "Zoom Out":           lambda: self.current_editor() and self.current_editor().zoom_out_text(),
            "Git Status":         self._git_status,
            "Git Diff":           self._git_diff,
            "Git Log":            self._git_log,
        }

    # ── Tab management ───────────────────────────────────────────────────────
    def current_editor(self) -> Editor | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, Editor) else None

    def new_tab(self):
        ed = Editor()
        idx = self.tabs.addTab(ed, "Untitled")
        self.tabs.setCurrentIndex(idx)
        self.file_paths[ed] = None
        ed.textChanged.connect(lambda: self._mark_dirty(ed))
        ed.textChanged.connect(lambda: self._mm_timer.start(300))
        ed.cursorPositionChanged.connect(
            lambda l, c: self.lbl_pos.setText(f"Ln {l+1}, Col {c+1}"))

    def _mark_dirty(self, ed: Editor):
        idx = self.tabs.indexOf(ed)
        if idx >= 0:
            name = self.tabs.tabText(idx)
            if not name.startswith("●"):
                self.tabs.setTabText(idx, "● " + name)

    def _close_tab(self, idx: int):
        ed = self.tabs.widget(idx)
        if isinstance(ed, Editor) and ed.modified:
            r = QMessageBox.question(self, "Unsaved changes",
                    "Save before closing?",
                    QMessageBox.StandardButton.Save |
                    QMessageBox.StandardButton.Discard |
                    QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Save:
                self.tabs.setCurrentIndex(idx); self.save_file()
            elif r == QMessageBox.StandardButton.Cancel:
                return
        if isinstance(ed, Editor): self.file_paths.pop(ed, None)
        self.tabs.removeTab(idx)
        if not self.tabs.count(): self.new_tab()

    def _on_tab_change(self, _):
        ed = self.current_editor()
        if not ed: return
        path = self.file_paths.get(ed)
        ext  = Path(path).suffix.lstrip(".").upper() if path else "Text"
        self.lbl_lang.setText(ext or "Text")
        self._sync_minimap()
        self._refresh_git(path)

    # ── File operations ──────────────────────────────────────────────────────
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if path: self._open_path(path)

    def _open_path(self, path: str):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        ed = Editor(path=path); ed.setText(text); ed.modified = False
        idx = self.tabs.addTab(ed, os.path.basename(path))
        self.tabs.setCurrentIndex(idx)
        self.file_paths[ed] = path
        ed.textChanged.connect(lambda: self._mark_dirty(ed))
        ed.textChanged.connect(lambda: self._mm_timer.start(300))
        ed.cursorPositionChanged.connect(
            lambda l, c: self.lbl_pos.setText(f"Ln {l+1}, Col {c+1}"))

    def save_file(self):
        ed = self.current_editor()
        if not ed: return
        path = self.file_paths.get(ed)
        if not path: return self.save_as()
        self._write(ed, path)

    def save_as(self):
        ed = self.current_editor()
        if not ed: return
        path, _ = QFileDialog.getSaveFileName(self, "Save As")
        if not path: return
        self.file_paths[ed] = path; ed.path = path; ed.apply_lexer()
        self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(path))
        self._write(ed, path)

    def save_all(self):
        for ed, path in list(self.file_paths.items()):
            if path: self._write(ed, path)

    def _write(self, ed: Editor, path: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(ed.text())
        ed.modified = False
        idx = self.tabs.indexOf(ed)
        self.tabs.setTabText(idx, os.path.basename(path))
        self.status.showMessage("Saved", 2000)

    # ── File tree ────────────────────────────────────────────────────────────
    def _tree_open(self, index: QModelIndex):
        path = self.fs_model.filePath(index)
        if os.path.isfile(path): self._open_path(path)

    def _toggle_tree(self):     self.tree.setVisible(not self.tree.isVisible())
    def _toggle_minimap(self):  self.minimap.setVisible(not self.minimap.isVisible())
    def _toggle_terminal(self):
        self.terminal.setVisible(not self.terminal.isVisible())
        if self.terminal.isVisible(): self.terminal.inp.setFocus()

    # ── Minimap ──────────────────────────────────────────────────────────────
    def _sync_minimap(self):
        ed = self.current_editor()
        if ed and self.minimap.isVisible():
            self.minimap.sync(ed.text())

    # ── Status bar ───────────────────────────────────────────────────────────
    def _update_status(self):
        ed = self.current_editor()
        if not ed: return
        self.lbl_words.setText(f"Words: {len(ed.text().split())}")

    def _refresh_git(self, path: str | None):
        if not path: self.lbl_git.setText(""); return
        try:
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=os.path.dirname(path), stderr=subprocess.DEVNULL
            ).decode().strip()
            dirty = subprocess.check_output(
                ["git", "status", "--short"],
                cwd=os.path.dirname(path), stderr=subprocess.DEVNULL
            ).decode().strip()
            self.lbl_git.setText(f" {branch} {'✦' if dirty else '✓'}")
        except Exception:
            self.lbl_git.setText("")

    # ── Git dialogs ──────────────────────────────────────────────────────────
    def _git_run(self, args: list[str]):
        ed   = self.current_editor()
        path = self.file_paths.get(ed) if ed else None
        cwd  = os.path.dirname(path) if path else os.getcwd()
        try:
            out = subprocess.check_output(["git"] + args, cwd=cwd,
                                          stderr=subprocess.STDOUT).decode()
        except subprocess.CalledProcessError as e:
            out = e.output.decode()
        dlg = QDialog(self); dlg.setWindowTitle(f"git {' '.join(args)}")
        dlg.resize(720, 520)
        te = QTextEdit(); te.setReadOnly(True)
        te.setFont(QFont("Consolas", 11)); te.setPlainText(out)
        te.setStyleSheet(f"background:{C['crust'].name()};color:{C['text'].name()};border:none;")
        lay = QVBoxLayout(dlg); lay.addWidget(te); dlg.exec()

    def _git_status(self): self._git_run(["status"])
    def _git_log(self):    self._git_run(["log", "--oneline", "-20", "--graph", "--decorate"])
    def _git_diff(self):
        ed   = self.current_editor()
        path = self.file_paths.get(ed) if ed else None
        self._git_run(["diff", path] if path else ["diff"])

    # ── Command palette ──────────────────────────────────────────────────────
    def _show_palette(self):
        pal = CommandPalette(list(self.COMMANDS.keys()), self)
        pal.command_selected.connect(lambda cmd: self.COMMANDS.get(cmd, lambda: None)())
        geo = self.geometry()
        pal.move(geo.x() + (geo.width() - pal.width()) // 2, geo.y() + 80)
        pal.show(); pal.search.setFocus()

    # ── Autosave ─────────────────────────────────────────────────────────────
    def _autosave(self):
        for ed, path in list(self.file_paths.items()):
            if path and ed.modified:
                try: self._write(ed, path)
                except Exception: pass


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    win = NotepadXPro()
    win.show()
    sys.exit(app.exec())