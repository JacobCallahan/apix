"""Tests for apix.diff."""
from pathlib import Path

from apix import diff
from apix.helpers import load_api


def test_positive_fill_defaults():
    vdiff = diff.VersionDiff(data_dir="./", mock=True)
    assert vdiff.api_name == "test123"
    assert vdiff.ver1 == "2.1"
    assert vdiff.ver2 == "1.3"


def test_positive_save_diff():
    vdiff = diff.VersionDiff(data_dir="./", mock=True)
    vdiff.diff()
    assert vdiff._vdiff
    path = vdiff.save_diff(return_path=True)
    assert Path(path).exists()
    Path(path).unlink()


def test_positive_validate_diff():
    vdiff = diff.VersionDiff(data_dir="./", mock=True)
    vdiff.diff()
    good_diff = load_api("test123", "good-diff", "./", True)
    assert vdiff._vdiff == good_diff
