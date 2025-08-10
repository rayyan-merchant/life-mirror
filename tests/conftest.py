import pytest
import os

@pytest.fixture(autouse=True)
def set_mock_mode():
    os.environ["LIFEMIRROR_MODE"] = "mock"
