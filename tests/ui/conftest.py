"""Fixtures de Qt, separadas del `conftest.py` raíz a propósito: PySide6
cuesta ~1s por proceso y la mayoría de las pruebas no lo necesitan.
"""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
