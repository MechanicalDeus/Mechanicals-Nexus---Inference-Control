from __future__ import annotations

import json

from PyQt6.QtCore import QEvent, QModelIndex, QObject, Qt
from PyQt6.QtGui import QGuiApplication, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
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
from nexus.output.inference_projection import (
    build_focus_payload,
    build_focus_reason_entries,
    build_inference_chain,
)
from nexus.output.perspective import (
    CenterKind,
    PerspectiveAdvice,
    PerspectiveKind,
    PerspectivePayloadKind,
    PerspectiveRequest,
    render_perspective,
)
from nexus.ui import theme
from nexus.ui.session import ConsoleSession
from nexus.ui.widgets.focus_graph_view import FocusGraphView
from nexus.ui.widgets.tags_delegate import TagsChipDelegate


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
        self._hover_row = -1

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        gb_repo = QGroupBox("Repo / Scan")
        ctrl = QHBoxLayout(gb_repo)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Repository root …")
        self._path_edit.setToolTip("Wurzelverzeichnis des zu analysierenden Python-Projekts.")
        btn_browse = QPushButton("Ordner …")
        btn_browse.clicked.connect(self._browse_repo)
        btn_refresh = QPushButton("Scan / Refresh")
        btn_refresh.clicked.connect(self._refresh_repo)
        btn_refresh.setToolTip("Graph neu aus dem gewählten Repo aufbauen.")
        ctrl.addWidget(QLabel("Pfad:"))
        ctrl.addWidget(self._path_edit, stretch=1)
        ctrl.addWidget(btn_browse)
        ctrl.addWidget(btn_refresh)
        root.addWidget(gb_repo)

        gb_query = QGroupBox("Query / Slice")
        query_row = QHBoxLayout(gb_query)
        self._query_edit = QLineEdit()
        self._query_edit.setPlaceholderText('Query (z. B. "mutation", "flow") …')
        self._query_edit.returnPressed.connect(self._run_query)
        self._query_edit.setToolTip("Heuristischer Slice wie in der CLI; Enter startet die Query.")
        self._max_sym = QSpinBox()
        self._max_sym.setRange(1, 500)
        self._max_sym.setValue(DEFAULT_QUERY_MAX_SYMBOLS)
        self._max_sym.setToolTip("Obergrenze für Symbole im Slice (wie --max-symbols).")
        self._min_conf_enabled = QCheckBox("min confidence")
        self._min_conf_enabled.setToolTip(
            "Nur Symbole mit mindestens dieser Konfidenz (Schwellwert unten)."
        )
        self._min_conf = QDoubleSpinBox()
        self._min_conf.setRange(0.0, 1.0)
        self._min_conf.setSingleStep(0.05)
        self._min_conf.setValue(0.5)
        self._min_conf.setEnabled(False)
        self._min_conf.setToolTip("Heuristische Zuverlässigkeit der Symbol-Zuordnung (0–1).")
        self._min_conf_enabled.toggled.connect(self._min_conf.setEnabled)
        btn_run = QPushButton("Query")
        btn_run.clicked.connect(self._run_query)
        btn_run.setToolTip("Slice berechnen (heuristic_slice).")
        query_row.addWidget(QLabel("Query:"))
        query_row.addWidget(self._query_edit, stretch=1)
        query_row.addWidget(QLabel("max sym"))
        query_row.addWidget(self._max_sym)
        query_row.addWidget(self._min_conf_enabled)
        query_row.addWidget(self._min_conf)
        query_row.addWidget(btn_run)
        root.addWidget(gb_query)

        tabs = QTabWidget()
        root.addWidget(tabs, stretch=1)

        # Tab: Slice
        slice_tab = QWidget()
        slice_layout = QVBoxLayout(slice_tab)
        split = QSplitter(Qt.Orientation.Horizontal)
        left_split = QSplitter(Qt.Orientation.Vertical)
        self._table = QTableView()
        self._table_headers = [
            "kind",
            "name",
            "conf",
            "layer",
            "file",
            "line",
            "tags",
            "writes",
            "reads",
            "calls",
        ]
        self._model = QStandardItemModel(0, len(self._table_headers))
        self._model.setHorizontalHeaderLabels(self._table_headers)
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(True)
        self._table.selectionModel().selectionChanged.connect(self._on_table_selection)
        self._table.setMouseTracking(True)
        self._table.entered.connect(self._on_table_entered)
        self._table.viewport().installEventFilter(self)
        self._table.setItemDelegateForColumn(6, TagsChipDelegate(self._table))
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in range(2, len(self._table_headers)):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

        self._context_panel = QPlainTextEdit()
        self._context_panel.setReadOnly(True)
        self._context_panel.setMaximumHeight(220)
        self._context_panel.setPlaceholderText("Kontext zum gewählten Symbol …")
        self._set_context_for_symbol(None)

        self._brief = QTextEdit()
        self._brief.setReadOnly(True)
        self._brief.setPlaceholderText("Balanced Brief (llm_brief) …")
        left_split.addWidget(self._table)
        left_split.addWidget(self._context_panel)
        left_split.addWidget(self._brief)
        left_split.setStretchFactor(0, 3)
        left_split.setStretchFactor(1, 0)
        left_split.setStretchFactor(2, 1)
        inspector = QWidget()
        ins_layout = QVBoxLayout(inspector)
        ins_layout.addWidget(QLabel("Perspektive (Inspector)"))
        self._perspective_combo = QComboBox()
        for label, kind in (
            ("Trust (Inspector)", PerspectiveKind.TRUST_DETAIL),
            ("Focus (JSON)", PerspectiveKind.FOCUS_GRAPH),
            ("Brief (llm_brief)", PerspectiveKind.LLM_BRIEF),
            ("Namen (agent_names)", PerspectiveKind.AGENT_NAMES),
            ("Compact (agent_compact)", PerspectiveKind.AGENT_COMPACT),
        ):
            self._perspective_combo.addItem(label, kind)
        self._perspective_combo.currentIndexChanged.connect(self._on_perspective_combo_changed)
        ins_layout.addWidget(self._perspective_combo)
        self._lens = QTextEdit()
        self._lens.setReadOnly(True)
        self._lens.setPlaceholderText("Symbol in der Tabelle wählen — Perspektive erscheint hier.")
        ins_layout.addWidget(self._lens, stretch=1)
        split.addWidget(left_split)
        split.addWidget(inspector)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        slice_layout.addWidget(split)

        copy_row = QHBoxLayout()
        for label, slot, tip in [
            (
                "Copy Minimal",
                self._copy_minimal,
                "Nur Namensliste (agent_names) in die Zwischenablage.",
            ),
            (
                "Copy Brief",
                self._copy_brief,
                "Text-Brief (llm_brief) in die Zwischenablage.",
            ),
            (
                "Copy JSON",
                self._copy_json,
                "Begrenzter Slice als JSON (query_slice_json).",
            ),
            (
                "Copy Focus (LLM)",
                self._copy_focus_payload,
                "Kanonischer Focus-Payload (schema nexus.focus_payload/v1) — gleiche Struktur wie „nexus focus -s …“.",
            ),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            b.setToolTip(tip)
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
        mut_sub = QTabWidget()
        self._mut_direct = QTextEdit()
        self._mut_direct.setReadOnly(True)
        self._mut_direct.setPlaceholderText("(Leer — trace_mutation ausführen.)")
        self._mut_indirect = QTextEdit()
        self._mut_indirect.setReadOnly(True)
        self._mut_indirect.setPlaceholderText("(Leer — trace_mutation ausführen.)")
        self._mut_transitive = QTextEdit()
        self._mut_transitive.setReadOnly(True)
        self._mut_transitive.setPlaceholderText("(Leer — trace_mutation ausführen.)")
        mut_sub.addTab(self._mut_direct, "direct_writes")
        mut_sub.addTab(self._mut_indirect, "indirect_writes")
        mut_sub.addTab(self._mut_transitive, "transitive_writes")
        mut_layout.addWidget(mut_sub, stretch=1)
        tabs.addTab(mut_tab, "Mutation")

        # Tab: Focus Graph
        focus_tab = QWidget()
        fl = QVBoxLayout(focus_tab)
        self._focus_view = FocusGraphView()
        c = theme.GRAPH_ROLE_HEX["center"]
        ca = theme.GRAPH_ROLE_HEX["caller"]
        ce = theme.GRAPH_ROLE_HEX["callee"]
        legend = QLabel(
            f'<span style="color:{ca}">●</span> caller &nbsp; '
            f'<span style="color:{c}">●</span> center &nbsp; '
            f'<span style="color:{ce}">●</span> callee'
        )
        legend.setToolTip(
            "Knotenfarben = theme.GRAPH_ROLE_HEX (caller / center / callee), identisch im Graph-Renderer."
        )
        fl.addWidget(legend)
        fl.addWidget(
            QLabel(
                "Symbol wählen — 1 Hop: callers (links) / callees (rechts). "
                "Hover über eine Zeile: Graph-Vorschau ohne Auswahl; Klick: Fokus mit kurzem Fade."
            )
        )
        fl.addWidget(self._focus_view, stretch=1)
        tabs.addTab(focus_tab, "Focus Graph")

    def eventFilter(self, obj: QObject | None, event: QEvent | None) -> bool:
        if (
            obj is self._table.viewport()
            and event is not None
            and event.type() == QEvent.Type.Leave
        ):
            self._clear_hover_focus_graph()
        return super().eventFilter(obj, event)

    def _apply_focus_graph(self, sym: SymbolRecord | None, *, animate: bool) -> None:
        if not sym or not self._session.graph:
            self._focus_view.set_from_layout(None, animate=False)
            return
        fr = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.FOCUS_GRAPH,
                graph=self._session.graph,
                center_kind=CenterKind.SYMBOL_ID,
                center_ref=sym.id,
            )
        )
        payload = (
            fr.payload_json if fr.payload_kind is PerspectivePayloadKind.GRAPH_JSON else None
        )
        self._focus_view.set_from_layout(payload, animate=animate)

    def _on_table_entered(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        row = index.row()
        if row == self._hover_row:
            return
        self._hover_row = row
        it = self._model.item(row, 1)
        if not it:
            return
        sym = it.data(Qt.ItemDataRole.UserRole)
        if isinstance(sym, SymbolRecord):
            self._apply_focus_graph(sym, animate=False)

    def _clear_hover_focus_graph(self) -> None:
        self._hover_row = -1
        self._apply_focus_graph(self._selected_symbol, animate=False)

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
        self._set_context_for_symbol(None)
        self._hover_row = -1
        self._focus_view.set_from_layout(None, animate=False)

    def _run_query(self) -> None:
        q = self._query_edit.text()
        max_s = self._max_sym.value()
        min_c = self._min_conf.value() if self._min_conf_enabled.isChecked() else None
        self._session.query_slice(q, max_symbols=max_s, min_confidence=min_c)

    @staticmethod
    def _reason_entries_to_lines(entries: list[dict[str, str]]) -> list[str]:
        label = {
            "called_by": "Called by",
            "writes": "Writes",
            "calls": "Calls",
            "reads": "Reads",
        }
        return [f"{label[e['type']]}: {e['target']}" for e in entries]

    def _structural_reason_lines(self, sym: SymbolRecord) -> list[str]:
        g = self._session.graph
        if not g:
            return []
        return self._reason_entries_to_lines(build_focus_reason_entries(g, sym))

    def _set_context_for_symbol(self, sym: SymbolRecord | None) -> None:
        if sym is None:
            self._context_panel.setPlainText(
                "Kein Symbol gewählt.\n"
                "Zeile in der Slice-Tabelle auswählen — Datei, Kind, Tags und strukturelle „Reason“-Zeilen erscheinen hier.\n"
                "Tab „Focus Graph“: 1-Hop-Beziehungen (Farben wie Legende)."
            )
            return
        tags = ", ".join(sym.semantic_tags) if sym.semantic_tags else "(keine)"
        n_read = len(sym.reads)
        n_write = len(sym.writes)
        n_call = len(sym.calls)
        influence = n_call + n_write
        g = self._session.graph
        chain = build_inference_chain(g, sym) if g else []
        chain_s = " → ".join(chain) if chain else "(leer)"
        reason = self._structural_reason_lines(sym)
        reason_block = (
            "Reason (structural):\n" + "\n".join(f"- {line}" for line in reason)
            if reason
            else "Reason (structural):\n- (keine Kanten in den ersten Slots — Detail siehe Trust-Perspektive)"
        )
        self._context_panel.setPlainText(
            f"Symbol: {sym.qualified_name}\n"
            f"Datei: {sym.file}:{sym.line_start}\n"
            f"Kind: {sym.kind}\n"
            f"Tags: {tags}\n"
            f"Reads: {n_read}   Writes: {n_write}   Calls: {n_call}\n"
            f"Influence: {influence} (calls={n_call}, writes={n_write})\n"
            f"Chain: {chain_s}\n"
            f"\n{reason_block}"
        )

    @staticmethod
    def _apply_semantic_item_roles(items: list[QStandardItem], row: dict) -> None:
        kc = theme.kind_text_qcolor(str(row.get("kind", "")))
        if kc:
            items[0].setForeground(kc)
        wc = theme.confidence_text_qcolor(float(row["confidence"]))
        if wc:
            items[2].setForeground(wc)
        lc = theme.layer_cell_qcolor(str(row.get("layer", "")))
        if lc:
            items[3].setBackground(lc)

    def _on_slice_updated(self, rows: list) -> None:
        self._hover_row = -1
        self._model.removeRows(0, self._model.rowCount())
        for row in rows:
            sym: SymbolRecord = row["_symbol"]
            items = [
                QStandardItem(str(row["kind"])),
                QStandardItem(str(row["name"])),
                QStandardItem(str(row["confidence"])),
                QStandardItem(str(row["layer"])),
                QStandardItem(str(row["file"])),
                QStandardItem(str(row["line_start"])),
                QStandardItem(""),
                QStandardItem(str(row["writes_count"])),
                QStandardItem(str(row["reads_count"])),
                QStandardItem(str(row["calls_count"])),
            ]
            items[1].setData(sym, Qt.ItemDataRole.UserRole)
            items[6].setData(row["tags_list"], TagsChipDelegate.TAGS_LIST_ROLE)
            self._apply_semantic_item_roles(items, row)
            self._model.appendRow(items)
        if not rows:
            self._brief.setPlainText("(Keine Treffer — Slice leer. Query oder Repo prüfen.)")
            self._set_context_for_symbol(None)
        else:
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
        if kind is PerspectiveKind.AGENT_COMPACT and not pq.strip():
            self._lens.setPlainText("(Keine Query — Compact braucht Query.)")
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
        if (
            kind is PerspectiveKind.AGENT_COMPACT
            and r.advice is PerspectiveAdvice.FALLBACK_TO_LLM_BRIEF
        ):
            r = render_perspective(
                PerspectiveRequest(
                    kind=PerspectiveKind.LLM_BRIEF,
                    graph=g,
                    query=pq,
                    max_symbols=max_s,
                    min_confidence=min_c,
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
            self._focus_view.set_from_layout(None, animate=False)
            self._set_context_for_symbol(None)
            return
        row = idxs[0].row()
        it = self._model.item(row, 1)
        if not it:
            return
        sym = it.data(Qt.ItemDataRole.UserRole)
        if isinstance(sym, SymbolRecord):
            self._selected_symbol = sym
            self._session.symbolSelected.emit(sym)
            self._set_context_for_symbol(sym)
            self._apply_focus_graph(sym, animate=True)
            self._refresh_inspector_lens()
        else:
            self._selected_symbol = None
            self._lens.clear()
            self._focus_view.set_from_layout(None, animate=False)
            self._set_context_for_symbol(None)

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

    def _copy_focus_payload(self) -> None:
        sym = self._selected_symbol
        g = self._session.graph
        if not sym or not g:
            QMessageBox.information(
                self,
                "Copy Focus (LLM)",
                "Symbol in der Tabelle wählen und Repo angebunden sein.",
            )
            return
        payload = build_focus_payload(g, sym)
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        QGuiApplication.clipboard().setText(text)
        self.statusBar().showMessage("Focus-Payload kopiert (nexus.focus_payload/v1).", 4000)

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
            return "\n".join(lines) if lines else "(Leer für diesen Bucket.)"

        self._mut_direct.setPlainText(fmt("direct_writes"))
        self._mut_indirect.setPlainText(fmt("indirect_writes"))
        self._mut_transitive.setPlainText(fmt("transitive_writes"))
