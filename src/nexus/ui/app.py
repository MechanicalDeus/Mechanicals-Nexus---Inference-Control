from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        sys.stderr.write(
            "Nexus Inference Console benötigt PyQt6. "
            "Installieren: pip install 'nexus-inference[ui]' oder pip install PyQt6\n"
        )
        return 1
    app = QApplication(sys.argv if argv is None else argv)
    from nexus.ui import theme

    app.setStyleSheet(theme.application_stylesheet())
    from nexus.ui.main_window import MainWindow

    w = MainWindow()
    w.show()
    return app.exec()
