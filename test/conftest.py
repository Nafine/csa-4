import pathlib

import pytest


@pytest.fixture(autouse=True, scope='session')
def _ensure_log_dir():
    pathlib.Path('log').mkdir(exist_ok=True)
