# ==== COCbot/gui/tabs/about_tab.py ====
"""About tab widget builder."""
import webbrowser

from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def build_about_tab(win):
    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 10, 0, 0)
    outer.setSpacing(12)

    card = QFrame()
    card.setObjectName("card")
    cv = QVBoxLayout(card)
    cv.setContentsMargins(16, 16, 16, 16)
    cv.setSpacing(8)

    title = QLabel("MyBot PHMOD v15.9")
    title.setStyleSheet("font-size:16px; font-weight:600; color:#193431;")
    cv.addWidget(title)

    subtitle = QLabel("Clash of Clans automation control panel")
    subtitle.setStyleSheet("font-size:11px; color:#657877;")
    cv.addWidget(subtitle)

    desc = QLabel(
        "Bot tự động farm tài nguyên, huấn luyện quân, xin quân, "
        "Clan Games / Clan Capital và chuyển account. "
        "Redline dùng OpenCV fallback, có thể nâng cấp bằng YOLO-seg."
    )
    desc.setWordWrap(True)
    desc.setStyleSheet("font-size:11px; color:#193431; line-height: 150%;")
    cv.addWidget(desc)

    meta = QLabel(
        "Python 3.13 · PyQt5 · OpenCV · Ultralytics (optional)\n"
        "Freeware · Open source · Không liên kết với Supercell."
    )
    meta.setWordWrap(True)
    meta.setStyleSheet("font-size:10px; color:#657877;")
    cv.addWidget(meta)

    btn_row = QHBoxLayout()
    github_btn = QPushButton("GitHub repository")
    github_btn.clicked.connect(
        lambda: webbrowser.open(
            "https://github.com/lvmai1801it-dev/MyBot_Python"))
    btn_row.addWidget(github_btn)
    btn_row.addStretch()
    cv.addLayout(btn_row)

    outer.addWidget(card)
    outer.addStretch()
    return page
