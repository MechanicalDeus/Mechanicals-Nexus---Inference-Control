from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSpinBox,
    QDoubleSpinBox,
    QTabWidget,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from nexus.core.models import SymbolRecord
from nexus.output.llm_format import DEFAULT_QUERY_MAX_SYMBOLS
from nexus.output.perspective import (
    CenterKind,
    PerspectiveKind,
    PerspectivePayloadKind,
    PerspectiveRequest,
    render_perspective,
)
from nexus.ui.session import ConsoleSession
from nexus.ui.widgets.focus_graph_view import FocusGraphView


class MainWindow(QMainWindow):
    """Nexus Inference Console — UI-Orchestrierung; Projektionen aus ``nexus.output.inference_projection``."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Nexus Inference Console")
        self.resize(1100, 720)

        self._session = ConsoleSession()
        self._session.sliceUpdated.connect(self._on_slice_updated)
        self._session.repoChanged.connect(self._on_repo_changed)
        self._session.statusMessage.connect(self.statusBar().showMessage)

        self._selected_symbol: SymbolRecord | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Steuerung
        ctrl = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Repository root …")
        btn_browse = QPushButton("Ordner …")
        btn_browse.clicked.connect(self._browse_repo)
        btn_refresh = QPushButton("Scan / Refresh")
        btn_refresh.clicked.connect(self._refresh_repo)
        ctrl.addWidget(QLabel("Repo:"))
        ctrl.addWidget(self._path_edit, stretch=1)
        ctrl.addWidget(btn_browse)
        ctrl.addWidget(btn_refresh)
        root.addLayout(ctrl)

        query_row = QHBoxLayout()
        self._query_edit = QLineEdit()
        self._query_edit.setPlaceholderText('Query (z. B. "mutation", "flow") …')
        self._query_edit.returnPressed.connect(self._run_query)
        self._max_sym = QSpinBox()
        self._max_sym.setRange(1, 500)
        self._max_sym.setValue(DEFAULT_QUERY_MAX_SYMBOLS)
        self._min_conf_enabled = QCheckBox("min confidence")
        self._min_conf = QDoubleSpinBox()
        self._min_conf.setRange(0.0, 1.0)
        self._min_conf.setSingleStep(0.05)
        self._min_conf.setValue(0.5)
        self._min_conf.setEnabled(False)
        self._min_conf_enabled.toggled.connect(self._min_conf.setEnabled)
        btn_run = QPushButton("Query")
        btn_run.clicked.connect(self._run_query)
        query_row.addWidget(QLabel("Query:"))
        query_row.addWidget(self._query_edit, stretch=1)
        query_row.addWidget(QLabel("max sym"))
        query_row.addWidget(self._max_sym)
        query_row.addWidget(self._min_conf_enabled)
        query_row.addWidget(self._min_conf)
        query_row.addWidget(btn_run)
        root.addLayout(query_row)

        tabs = QTabWidget()
        root.addWidget(tabs, stretch=1)

        # Tab: Slice
        slice_tab = QWidget()
        slice_layout = QVBoxLayout(slice_tab)
        split = QSplitter(Qt.Orientation.Horizontal)
        left_split = QSplitter(Qt.Orientation.Vertical)
        self._table = QTableView()
        self._model = QStandardItemModel(0, 5)
        self._model.setHorizontalHeaderLabels(["name", "confidence", "layer", "writes", "calls"])
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.selectionModel().selectionChanged.connect(self._on_table_selection)
        self._brief = QTextEdit()
        self._brief.setReadOnly(True)
        self._brief.setPlaceholderText("Balanced Brief (to_llm_brief) …")
        left_split.addWidget(self._table)
        left_split.addWidget(self._brief)
        left_split.setStretchFactor(0, 2)
        left_split.setStretchFactor(1, 1)
        inspector = QWidget()
        ins_layout = QVBoxLayout(inspector)
        ins_layout.addWidget(QLabel("Perspektive (Inspector)"))
        self._perspective_combo = QComboBox()
        for label, kind in (
            ("Trust (Inspector)", PerspectiveKind.TRUST_DETAIL),
            ("Focus (JSON)", PerspectiveKind.FOCUS_GRAPH),
            ("Brief (llm_brief)", PerspectiveKind.LLM_BRIEF),
            ("Namen (agent_names)", PerspectiveKind.AGENT_NAMES),
        ):
            self._perspective_combo.addItem(label, kind)
        self._perspective_combo.currentIndexChanged.connect(self._on_perspective_combo_changed)
        ins_layout.addWidget(self._perspective_combo)
        self._lens = QTextEdit()
        self._lens.setReadOnly(True)
        self._lens.setPlaceholderText("Symbol wählen …")
        ins_layout.addWidget(self._lens, stretch=1)
        split.addWidget(left_split)
        split.addWidget(inspector)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        slice_layout.addWidget(split)

        copy_row = QHBoxLayout()
        for label, slot in [
            ("Copy Minimal", self._copy_minimal),
            ("Copy Brief", self._copy_brief),
            ("Copy JSON", self._copy_json),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            copy_row.addWidget(b)
        slice_layout.addLayout(copy_row)
        tabs.addTab(slice_tab, "Slice")

        # Tab: Mutation
        mut_tab = QWidget()
        mut_layout = QVBoxLayout(mut_tab)
        mk = QHBoxLayout()
        self._mut_key = QLineEdit()
        self._mut_key.setPlaceholderText("State-Key Substring …")
        btn_mut = QPushButton("trace_mutation")
        btn_mut.clicked.connect(self._run_mutation)
        mk.addWidget(self._mut_key)
        mk.addWidget(btn_mut)
        mut_layout.addLayout(mk)
        self._mut_direct = QTextEdit()
        self._mut_direct.setReadOnly(True)
        self._mut_indirect = QTextEdit()
        self._mut_indirect.setReadOnly(True)
        self._mut_transitive = QTextEdit()
        self._mut_transitive.setReadOnly(True)
        mut_layout.addWidget(QLabel("direct_writes"))
        mut_layout.addWidget(self._mut_direct)
        mut_layout.addWidget(QLabel("indirect_writes"))
        mut_layout.addWidget(self._mut_indirect)
        mut_layout.addWidget(QLabel("transitive_writes"))
        mut_layout.addWidget(self._mut_transitive)
        tabs.addTab(mut_tab, "Mutation")

        # Tab: Focus Graph
        focus_tab = QWidget()
        fl = QVBoxLayout(focus_tab)
        self._focus_view = FocusGraphView()
        fl.addWidget(
            QLabel("Selektiere ein Symbol in der Slice-Tabelle (1 Hop: callers / callees).")
        )
        fl.addWidget(self._focus_view, stretch=1)
        tabs.addTab(focus_tab, "Focus Graph")

    def _browse_repo(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Repository-Root")
        if d:
            self._path_edit.setText(d)

    def _refresh_repo(self) -> None:
        path = self._path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "Nexus Console", "Bitte ein Repository-Verzeichnis wählen.")
            return
        ok = self._session.attach_repo(path)
        if not ok:
            QMessageBox.critical(
                self,
                "Nexus Console",
                self._session.last_error() or "attach fehlgeschlagen",
            )

    def _on_repo_changed(self, _path: str) -> None:
        self._model.removeRows(0, self._model.rowCount())
        self._brief.clear()
        self._selected_symbol = None
        self._lens.clear()
        self._perspective_combo.setCurrentIndex(0)

    def _run_query(self) -> None:
        q = self._query_edit.text()
        max_s = self._max_sym.value()
        min_c = self._min_conf.value() if self._min_conf_enabled.isChecked() else None
        self._session.query_slice(q, max_symbols=max_s, min_confidence=min_c)

    def _on_slice_updated(self, rows: list) -> None:
        self._model.removeRows(0, self._model.rowCount())
        for row in rows:
            items = [
                QStandardItem(str(row["name"])),
                QStandardItem(str(row["confidence"])),
                QStandardItem(str(row["layer"])),
                QStandardItem(str(row["writes_count"])),
                QStandardItem(str(row["calls_count"])),
            ]
            sym: SymbolRecord = row["_symbol"]
            items[0].setData(sym, Qt.ItemDataRole.UserRole)
            self._model.appendRow(items)
        self._brief.setPlainText(self._session.get_brief())

    def _on_perspective_combo_changed(self, _index: int) -> None:
        self._refresh_inspector_lens()

    def _refresh_inspector_lens(self) -> None:
        sym = self._selected_symbol
        g = self._session.graph
        if not sym or not g:
            self._lens.clear()
            return
        kind = self._perspective_combo.currentData()
        if not isinstance(kind, PerspectiveKind):
            return
        pq = self._session.last_query or ""
        max_s = self._max_sym.value()
        min_c = self._min_conf.value() if self._min_conf_enabled.isChecked() else None

        if kind is PerspectiveKind.LLM_BRIEF and not pq.strip():
            self._lens.setPlainText("(Keine Query — zuerst Query ausführen.)")
            return
        if kind is PerspectiveKind.AGENT_NAMES and not pq.strip():
            self._lens.setPlainText("(Keine Query — Namen-Liste braucht Query.)")
            return

        r = render_perspective(
            PerspectiveRequest(
                kind=kind,
                graph=g,
                query=pq,
                max_symbols=max_s,
                min_confidence=min_c,
                center_kind=CenterKind.SYMBOL_ID,
                center_ref=sym.id,
            )
        )
        if r.payload_kind is PerspectivePayloadKind.ERROR:
            self._lens.setPlainText(r.error or "")
            return
        if r.payload_kind in (
            PerspectivePayloadKind.JSON,
            PerspectivePayloadKind.GRAPH_JSON,
        ):
            self._lens.setPlainText(
                json.dumps(r.payload_json, indent=2, ensure_ascii=False)
            )
            return
        self._lens.setPlainText(r.payload_text or "")

    def _on_table_selection(self) -> None:
        idxs = self._table.selectionModel().selectedRows()
        if not idxs:
            self._selected_symbol = None
            self._lens.clear()
            self._focus_view.set_from_layout(None)
            return
        row = idxs[0].row()
        it = self._model.item(row, 0)
        if not it:
            return
        sym = it.data(Qt.ItemDataRole.UserRole)
        if isinstance(sym, SymbolRecord):
            self._selected_symbol = sym
            self._session.symbolSelected.emit(sym)
            if self._session.graph:
                fr = render_perspective(
                    PerspectiveRequest(
                        kind=PerspectiveKind.FOCUS_GRAPH,
                        graph=self._session.graph,
                        center_kind=CenterKind.SYMBOL_ID,
                        center_ref=sym.id,
                    )
                )
                self._focus_view.set_from_layout(
                    fr.payload_json if fr.payload_kind is PerspectivePayloadKind.GRAPH_JSON else None
                )
            self._refresh_inspector_lens()
        else:
            self._selected_symbol = None
            self._lens.clear()
            self._focus_view.set_from_layout(None)

    def _copy_minimal(self) -> None:
        names = self._session.get_minimal_names()
        if names is None:
            QMessageBox.information(
                self,
                "Copy Minimal",
                "Für diese Query liefert Nexus keine Namensliste (z. B. Spezialmodus). "
                "Nutze „Copy Brief“.",
            )
            return
        text = "\n".join(names)
        QGuiApplication.clipboard().setText(text)
        self.statusBar().showMessage("Minimal Context kopiert.", 3000)

    def _copy_brief(self) -> None:
        text = self._session.get_brief()
        if not text.strip():
            QMessageBox.information(
                self, "Copy Brief", "Kein Brief — Query ausführen oder Query setzen."
            )
            return
        QGuiApplication.clipboard().setText(text)
        self.statusBar().showMessage("Balanced Brief kopiert.", 3000)

    def _copy_json(self) -> None:
        payload = self._session.get_json_slice()
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        QGuiApplication.clipboard().setText(text)
        self.statusBar().showMessage("Slice-JSON kopiert.", 3000)

    def _run_mutation(self) -> None:
        key = self._mut_key.text().strip()
        if not key:
            return
        r = self._session.trace_mutation(key)

        def fmt(bucket: str) -> str:
            lst = r.get(bucket, [])
            lines = []
            for item in lst:
                if isinstance(item, dict):
                    qn = item.get("qualified_name", item.get("id", "?"))
                    lines.append(str(qn))
                else:
                    lines.append(str(item))
            return "\n".join(lines) if lines else "(leer)"

        self._mut_direct.setPlainText(fmt("direct_writes"))
        self._mut_indirect.setPlainText(fmt("indirect_writes"))
        self._mut_transitive.setPlainText(fmt("transitive_writes"))
