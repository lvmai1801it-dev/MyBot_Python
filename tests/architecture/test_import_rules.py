"""Architecture contracts: the domain and core layers must stay Qt-free."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2]
COCbot = SRC_ROOT / "COCbot"


def _python_files(root: Path) -> list[Path]:
    """Return every Python file under *root*, excluding caches."""
    return sorted(
        path for path in root.rglob("*.py") if "__pycache__" not in path.parts
    )


def _imported_modules(tree: ast.Module) -> set[str]:
    """Collect absolute module names imported by *tree*."""
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


class LayerContractTests(unittest.TestCase):
    """Enforce the dependency direction documented in ARCHITECTURE.md."""

    def test_core_and_models_do_not_import_pyqt(self) -> None:
        for base in (COCbot / "core", COCbot / "models"):
            for path in _python_files(base):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for module in _imported_modules(tree):
                    self.assertFalse(
                        module.startswith("PyQt5"),
                        f"{path.relative_to(SRC_ROOT)} imports {module}",
                    )

    def test_core_and_models_do_not_import_ui_layers(self) -> None:
        forbidden = (
            "COCbot.gui",
            "COCbot.app",
            "COCbot.attack",
            "COCbot.game",
            "COCbot.vision",
            "COCbot.platform",
            "COCbot.emulator",
            "COCbot.workers",
            "COCbot.views",
            "COCbot.viewmodels",
            "COCbot.features",
        )
        for base in (COCbot / "core", COCbot / "models"):
            for path in _python_files(base):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for module in _imported_modules(tree):
                    for prefix in forbidden:
                        self.assertFalse(
                            module == prefix or module.startswith(prefix + "."),
                            f"{path.relative_to(SRC_ROOT)} imports {module}",
                        )

    def test_models_stay_framework_free(self) -> None:
        forbidden = ("numpy", "cv2", "torch", "ultralytics", "PyQt5", "requests")
        for path in _python_files(COCbot / "models"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for module in _imported_modules(tree):
                self.assertNotIn(
                    module.split(".")[0],
                    forbidden,
                    f"{path.relative_to(SRC_ROOT)} imports {module}",
                )

    def test_no_wildcard_imports(self) -> None:
        for path in _python_files(COCbot / "core") + _python_files(COCbot / "models"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        self.assertNotEqual(
                            alias.name,
                            "*",
                            f"{path.relative_to(SRC_ROOT)} uses a wildcard import",
                        )

    def test_public_symbols_have_docstrings(self) -> None:
        for path in _python_files(COCbot / "core") + _python_files(COCbot / "models"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            self.assertIsNotNone(
                ast.get_docstring(tree),
                f"{path.relative_to(SRC_ROOT)} is missing a module docstring",
            )
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name.startswith("_"):
                        continue
                    self.assertIsNotNone(
                        ast.get_docstring(node),
                        f"{path.relative_to(SRC_ROOT)}::{node.name} is missing a docstring",
                    )
                    if isinstance(node, ast.ClassDef):
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                if item.name.startswith("_") and item.name != "__post_init__":
                                    continue
                                self.assertIsNotNone(
                                    ast.get_docstring(item),
                                    f"{path.relative_to(SRC_ROOT)}::{node.name}.{item.name} "
                                    "is missing a docstring",
                                )


class NewLayerTests(unittest.TestCase):
    """Contracts for the new application and worker layers."""

    APP_FILES = (
        COCbot / "app" / "session.py",
        COCbot / "app" / "orchestrator.py",
    )
    WORKER_FILES = (
        COCbot / "workers" / "_bootstrap.py",
        COCbot / "workers" / "base_worker.py",
        COCbot / "workers" / "bot_worker.py",
        COCbot / "workers" / "task_worker.py",
    )

    def test_application_layer_does_not_import_pyqt(self) -> None:
        for path in self.APP_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for module in _imported_modules(tree):
                self.assertFalse(
                    module.startswith("PyQt5"),
                    f"{path.relative_to(SRC_ROOT)} imports {module}",
                )

    def test_new_layers_have_docstrings(self) -> None:
        for path in self.APP_FILES + self.WORKER_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            self.assertIsNotNone(
                ast.get_docstring(tree),
                f"{path.relative_to(SRC_ROOT)} is missing a module docstring",
            )
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name.startswith("_"):
                        continue
                    self.assertIsNotNone(
                        ast.get_docstring(node),
                        f"{path.relative_to(SRC_ROOT)}::{node.name} is missing a docstring",
                    )
                    if isinstance(node, ast.ClassDef):
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                if item.name.startswith("_"):
                                    continue
                                self.assertIsNotNone(
                                    ast.get_docstring(item),
                                    f"{path.relative_to(SRC_ROOT)}::{node.name}.{item.name} "
                                    "is missing a docstring",
                                )


class FeatureContractTests(unittest.TestCase):
    """Contracts for feature colocation and MVVM boundaries."""

    FEATURE = COCbot / "features" / "settings"

    def test_model_is_qt_free(self) -> None:
        tree = ast.parse((self.FEATURE / "model.py").read_text(encoding="utf-8"))
        for module in _imported_modules(tree):
            self.assertFalse(
                module.startswith("PyQt5"),
                f"features/settings/model.py imports {module}",
            )

    def test_viewmodel_uses_qt_signals(self) -> None:
        tree = ast.parse((self.FEATURE / "viewmodel.py").read_text(encoding="utf-8"))
        modules = _imported_modules(tree)
        self.assertTrue(any(module.startswith("PyQt5") for module in modules))

    def test_attack_model_is_qt_free(self) -> None:
        path = COCbot / "features" / "attack" / "model.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for module in _imported_modules(tree):
            self.assertFalse(
                module.startswith("PyQt5"),
                f"features/attack/model.py imports {module}",
            )

    def test_accounts_model_is_qt_free(self) -> None:
        path = COCbot / "features" / "accounts" / "model.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for module in _imported_modules(tree):
            self.assertFalse(
                module.startswith("PyQt5"),
                f"features/accounts/model.py imports {module}",
            )

    def test_logs_model_is_qt_free(self) -> None:
        path = COCbot / "features" / "logs" / "model.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for module in _imported_modules(tree):
            self.assertFalse(
                module.startswith("PyQt5"),
                f"features/logs/model.py imports {module}",
            )

    def test_statistics_model_is_qt_free(self) -> None:
        path = COCbot / "features" / "statistics" / "model.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for module in _imported_modules(tree):
            self.assertFalse(
                module.startswith("PyQt5"),
                f"features/statistics/model.py imports {module}",
            )

    def test_village_and_clan_models_are_qt_free(self) -> None:
        for feature in ("village", "clan"):
            path = COCbot / "features" / feature / "model.py"
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for module in _imported_modules(tree):
                self.assertFalse(
                    module.startswith("PyQt5"),
                    f"features/{feature}/model.py imports {module}",
                )

    def test_feature_files_have_docstrings(self) -> None:
        for feature in (
            "settings",
            "attack",
            "accounts",
            "logs",
            "statistics",
            "village",
            "clan",
        ):
            for name in ("model.py", "viewmodel.py", "view.py"):
                path = COCbot / "features" / feature / name
                tree = ast.parse(path.read_text(encoding="utf-8"))
                self.assertIsNotNone(
                    ast.get_docstring(tree),
                    f"features/{feature}/{name} is missing a module docstring",
                )
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if node.name.startswith("_"):
                            continue
                        self.assertIsNotNone(
                            ast.get_docstring(node),
                            f"features/{feature}/{name}::{node.name} is missing a docstring",
                        )


if __name__ == "__main__":
    unittest.main()
