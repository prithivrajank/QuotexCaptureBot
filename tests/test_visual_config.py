from app.vision.config import validate_visual_config


def valid_profile():
    return {
        "symbol": "USD/BRL_OTC",
        "timeframe_seconds": 60,
        "region": {"left": 150, "top": 220, "width": 1257, "height": 650},
        "calibration": {
            "y_top": 40,
            "price_top": 0.17210,
            "y_bottom": 600,
            "price_bottom": 0.17110,
        },
        "time_calibration": {
            "x_left": 20,
            "timestamp_left": 1795000000,
            "x_right": 1200,
            "timestamp_right": 1795003600,
        },
    }


def test_valid_profile_has_no_errors():
    assert validate_visual_config(valid_profile()) == []


def test_price_anchor_must_be_inside_crop():
    profile = valid_profile()
    profile["calibration"]["y_bottom"] = 650
    assert any("price calibration y anchors" in error for error in validate_visual_config(profile))


def test_time_anchor_must_be_inside_crop():
    profile = valid_profile()
    profile["time_calibration"]["x_right"] = 1257
    assert any("time calibration x anchors" in error for error in validate_visual_config(profile))


def test_missing_calibration_is_rejected():
    profile = valid_profile()
    del profile["time_calibration"]
    assert any("time_calibration needs" in error for error in validate_visual_config(profile))


def test_invalid_region_is_rejected():
    profile = valid_profile()
    profile["region"]["width"] = 50
    assert any("region needs" in error for error in validate_visual_config(profile))
