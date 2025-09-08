import pytest
import os


def pytest_configure(config):
    """Configure pytest for this project."""
    # Ensure test output directories exist
    test_dir = os.path.dirname(__file__)
    actual_dir = os.path.join(test_dir, "actual")
    if not os.path.exists(actual_dir):
        os.makedirs(actual_dir)
