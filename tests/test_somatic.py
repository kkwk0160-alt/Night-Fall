"""五感系统单测"""
from night_fall.somatic import (
    ACTIVE_THRESHOLD,
    TAU,
    ChannelState,
    SomaticState,
    build_touch_label,
    compute_touch_value,
    decay,
    detect_channel,
    detect_touch,
    ignite,
    process_input,
    snapshot,
    SMELL_KEYWORDS,
    TASTE_KEYWORDS,
    SOUND_KEYWORDS,
)


def test_decay_basic():
    assert decay(1.0, 0, 600) == 1.0
    val = decay(1.0, 600, 600)
    assert 0.36 < val < 0.38  # e^-1 ≈ 0.3679


def test_detect_touch_action_only():
    result = detect_touch("戳你一下")
    assert result is not None
    assert result[0] == "戳"


def test_detect_touch_with_body():
    result = detect_touch("捏你的脸")
    assert result is not None
    assert result == ("捏", "脸")


def test_detect_touch_clause_boundary():
    result = detect_touch("抱住了你，然后摸你的头发")
    assert result is not None
    action, body = result
    assert action == "抱"


def test_detect_touch_no_cross_clause_body():
    """部位只在动作词所在小句中找，不跨标点"""
    result = detect_touch("摸了摸猫，看着你的脸")
    assert result is not None
    action, body = result
    assert action == "摸"
    assert body != "脸"


def test_build_touch_label():
    label = build_touch_label("捏", "脸")
    assert "脸" in label
    assert "指尖" in label
    assert "短促" in label


def test_build_touch_label_sensitive():
    label = build_touch_label("亲", "嘴唇")
    assert "敏感" in label


def test_compute_touch_value():
    val = compute_touch_value("捏", "嘴唇")
    assert val > compute_touch_value("捏", "肩")


def test_ignite_stacks():
    old = ChannelState(value=0.5, label="旧的", at=100.0)
    new = ignite(old, 0.4, "新的", 101.0, 600)
    assert new.value > 0.5
    assert new.value <= 1.0


def test_ignite_strong_label_wins():
    old = ChannelState(value=0.3, label="旧的", at=100.0)
    new = ignite(old, 0.6, "新的", 101.0, 600)
    assert new.label == "新的"


def test_snapshot_below_threshold():
    state = SomaticState()
    state.touch = ChannelState(value=0.05, label="轻触", at=1.0)
    result = snapshot(state, 2.0)
    assert result == ""


def test_snapshot_above_threshold():
    state = SomaticState()
    state.touch = ChannelState(value=0.8, label="捏脸", at=100.0)
    result = snapshot(state, 100.5)
    assert "touch" in result
    assert "捏脸" in result
    assert "⟨body⟩" in result


def test_snapshot_disabled():
    state = SomaticState(enabled=False)
    state.touch = ChannelState(value=0.8, label="捏脸", at=100.0)
    assert snapshot(state, 100.5) == ""


def test_process_input_touch():
    state = SomaticState()
    state = process_input(state, "戳你的脸", now=100.0)
    assert state.touch.value > 0
    assert "脸" in state.touch.label


def test_process_input_smell():
    state = SomaticState()
    state = process_input(state, "闻到你身上的香水味", now=100.0)
    assert state.smell.value > 0


def test_process_input_multi_channel():
    state = SomaticState()
    state = process_input(state, "亲了你的嘴唇，听到你的呼吸", now=100.0)
    assert state.touch.value > 0
    assert state.taste.value > 0
    assert state.sound.value > 0


def test_decay_over_time():
    state = SomaticState()
    state = process_input(state, "捏你的脸", now=100.0)
    initial = state.touch.value
    result_early = snapshot(state, 200.0)
    result_late = snapshot(state, 10000.0)
    assert "touch" in result_early
    assert result_late == ""


def test_detect_smell():
    result = detect_channel("空气里有咖啡香", SMELL_KEYWORDS)
    assert result is not None
    assert result[1] == "咖啡香"


def test_detect_sound():
    result = detect_channel("你的呼吸越来越重", SOUND_KEYWORDS)
    assert result is not None
    assert "呼吸" in result[1]
