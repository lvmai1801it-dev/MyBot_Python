"""Reusable labeled form controls."""

from __future__ import annotations

from typing import Sequence

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class LabeledSpinBox(QWidget):
    """A muted label followed by an integer spin box."""

    value_changed = pyqtSignal(int)

    def __init__(
        self,
        label: str,
        minimum: int = 0,
        maximum: int = 100_000_000,
        step: int = 1,
        suffix: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Create the field and connect the spin box signal."""
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        text = QLabel(label)
        text.setObjectName("muted")
        layout.addWidget(text)
        layout.addStretch(1)
        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        if suffix:
            self.spin.setSuffix(suffix)
        self.spin.setMinimumWidth(130)
        self.spin.valueChanged.connect(self.value_changed.emit)
        layout.addWidget(self.spin)

    def value(self) -> int:
        """Return the current value."""
        return int(self.spin.value())

    def set_value(self, value: int) -> None:
        """Set the current value without emitting user intent."""
        self.spin.blockSignals(True)
        self.spin.setValue(int(value))
        self.spin.blockSignals(False)


class LabeledLineEdit(QWidget):
    """A muted label followed by a single-line editor."""

    text_changed = pyqtSignal(str)

    def __init__(
        self,
        label: str,
        placeholder: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Create the field and connect editing signals."""
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        text = QLabel(label)
        text.setObjectName("muted")
        layout.addWidget(text)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(self.text_changed.emit)
        layout.addWidget(self.edit, 1)

    def text(self) -> str:
        """Return the current text."""
        return self.edit.text().strip()

    def set_text(self, value: str) -> None:
        """Set text without emitting user intent."""
        self.edit.blockSignals(True)
        self.edit.setText(value)
        self.edit.blockSignals(False)


class LabeledComboBox(QWidget):
    """A muted label followed by a combo box."""

    current_changed = pyqtSignal(str)

    def __init__(
        self,
        label: str,
        items: Sequence[str] = (),
        parent: QWidget | None = None,
    ) -> None:
        """Create the field and connect selection changes."""
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        text = QLabel(label)
        text.setObjectName("muted")
        layout.addWidget(text)
        layout.addStretch(1)
        self.combo = QComboBox()
        self.combo.addItems(list(items))
        self.combo.setMinimumWidth(150)
        self.combo.currentTextChanged.connect(self.current_changed.emit)
        layout.addWidget(self.combo)

    def current_text(self) -> str:
        """Return the selected text."""
        return self.combo.currentText()

    def set_current_text(self, value: str) -> None:
        """Select *value* without emitting user intent."""
        index = self.combo.findText(value)
        if index < 0:
            return
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(index)
        self.combo.blockSignals(False)


class ToggleRow(QWidget):
    """Checkbox with an optional description underneath."""

    toggled = pyqtSignal(bool)

    def __init__(
        self,
        label: str,
        checked: bool = False,
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Create the toggle and connect its signal."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.checkbox = QCheckBox(label)
        self.checkbox.setChecked(checked)
        self.checkbox.toggled.connect(self.toggled.emit)
        layout.addWidget(self.checkbox)
        if description:
            hint = QLabel(description)
            hint.setObjectName("muted")
            hint.setWordWrap(True)
            layout.addWidget(hint)

    def is_checked(self) -> bool:
        """Return the checkbox state."""
        return self.checkbox.isChecked()

    def set_checked(self, value: bool) -> None:
        """Set the checkbox without emitting user intent."""
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(bool(value))
        self.checkbox.blockSignals(False)
