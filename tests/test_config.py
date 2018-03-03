def test_create_config(monkeypatch, mock_config_dir):
    import os
    # Monkeypatch XDG_CONFIG_HOME inside this test only
    # This way we don't need to have a $HOME
    monkeypatch.setitem(os.environ, 'XDG_CONFIG_HOME', mock_config_dir)

    from cdparacord.config import Config
    c = Config()
