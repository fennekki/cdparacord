def test_create_config(mock_config_dir):
    from cdparacord.config import Config
    c = Config()


def test_get_lame(mock_config_dir):
    from cdparacord.config import Config
    c = Config()
    # Would error if we couldn't find it
    c.get('lame')
