"""Tests for apix.explore"""
from apix import explore


def test_positive_explore():
    t_explorer = explore.AsyncExplorer(
        name="test",
        version="1.0",
        host_url="https://github.com/",
        base_path="JacobCallahan?tab=repositories",
        parser="test",
    )
    assert t_explorer.explore()
    save_file = t_explorer.save_data(return_path=True)
    assert save_file.exists()
    data_dir = save_file.parent
    save_file.unlink()
    data_dir.rmdir()
