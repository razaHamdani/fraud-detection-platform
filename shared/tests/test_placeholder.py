def test_shared_import():
    import shared
    assert shared.__version__ == "0.1.0"
