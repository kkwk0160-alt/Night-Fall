"""念头池单测"""
from night_fall.thought_pool import (
    FLASH_DECAY,
    OBSESSION_THRESHOLD,
    ThoughtPool,
)


def test_ignite_new():
    pool = ThoughtPool()
    t = pool.ignite("想她", now=100.0)
    assert t.intensity == 0.5
    assert not t.is_obsession


def test_ignite_stack():
    pool = ThoughtPool()
    pool.ignite("想她", now=100.0)
    t = pool.ignite("想她", boost=0.4, now=101.0)
    assert t.intensity == 0.9
    assert t.is_obsession


def test_flash_decays():
    pool = ThoughtPool()
    pool.ignite("随便想想", now=100.0)
    pool.tick(now=101.0)
    t = pool.thoughts["随便想想"]
    assert t.intensity < 0.5
    assert abs(t.intensity - 0.5 * FLASH_DECAY) < 0.001


def test_flash_dies():
    pool = ThoughtPool()
    pool.ignite("随便想想", boost=0.1, now=100.0)
    for i in range(50):
        pool.tick(now=100.0 + i)
    assert "随便想想" not in pool.thoughts


def test_obsession_grows():
    pool = ThoughtPool()
    pool.ignite("想她", boost=0.85, now=100.0)
    assert pool.thoughts["想她"].is_obsession
    old_val = pool.thoughts["想她"].intensity
    pool.tick(now=101.0)
    assert "想她" in pool.thoughts
    assert pool.thoughts["想她"].intensity > old_val


def test_obsession_pushes_libido():
    pool = ThoughtPool()
    pool.ignite("想她", boost=0.85, now=100.0)
    pool.tick(now=101.0)
    assert pool.libido > 0


def test_obsession_resolves():
    pool = ThoughtPool()
    pool.ignite("想她", boost=0.9, now=100.0)
    resolved_all: list[str] = []
    for i in range(20):
        resolved = pool.tick(now=100.0 + i)
        resolved_all.extend(resolved)
    assert "想她" in resolved_all
    assert "想她" not in pool.thoughts


def test_snapshot_empty():
    pool = ThoughtPool()
    assert pool.snapshot() == ""


def test_snapshot_content():
    pool = ThoughtPool()
    pool.ignite("想她", now=100.0)
    s = pool.snapshot()
    assert "闪念" in s
    assert "想她" in s
    assert "⟨mind⟩" in s


def test_snapshot_obsession_tag():
    pool = ThoughtPool()
    pool.ignite("想她", boost=0.85, now=100.0)
    s = pool.snapshot()
    assert "执念" in s


def test_libido_in_snapshot():
    pool = ThoughtPool()
    pool.ignite("想她", boost=0.9, now=100.0)
    for i in range(5):
        pool.tick(now=100.0 + i)
    s = pool.snapshot()
    assert "欲望" in s


def test_multiple_thoughts():
    pool = ThoughtPool()
    pool.ignite("想她", now=100.0)
    pool.ignite("饿了", now=100.0)
    pool.ignite("困了", now=100.0)
    assert len(pool.thoughts) == 3
    pool.tick(now=101.0)
    assert len(pool.thoughts) == 3


def test_to_dict():
    pool = ThoughtPool()
    pool.ignite("想她", now=100.0)
    d = pool.to_dict()
    assert "thoughts" in d
    assert "想她" in d["thoughts"]
    assert "libido" in d
