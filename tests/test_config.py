from redlink_controller.config import AppConfig, ensure_config, load_config, save_config, update_config, validate_config


def test_save_and_load_roundtrip(tmp_path) -> None:
    path = tmp_path / "config.json"
    config = AppConfig(username="u", password="p", device_id=123)
    save_config(config, str(path))

    loaded = load_config(str(path))
    assert loaded.username == "u"
    assert loaded.password == "p"
    assert loaded.device_id == 123


def test_update_config_merges(tmp_path) -> None:
    path = tmp_path / "config.json"
    ensure_config(str(path))

    update_config(str(path), {"username": "u", "device_id": 456})
    updated = load_config(str(path))
    assert updated.username == "u"
    assert updated.device_id == 456


def test_validate_config_flags_thresholds() -> None:
    config = AppConfig(heat_on_below=72.0, heat_off_at=70.0)
    errors = validate_config(config)
    assert "heat_on_below must be less than heat_off_at" in errors
