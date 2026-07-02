"""
五感系统 — 纯函数 + 数据内核
四通道: touch / smell / taste / sound
管线: detect → ignite → decay → snapshot
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any

# ── 衰减常数 (tau, 秒) ──────────────────────────
TAU = {
    "touch": 600,
    "smell": 1200,
    "taste": 900,
    "sound": 450,
}

ACTIVE_THRESHOLD = 0.15

# ── 动作表 ─────────────────────────────────────
ACTION_TABLE: dict[str, dict[str, Any]] = {
    "捏":  {"contact": "指尖", "rhythm": "短促"},
    "戳":  {"contact": "指尖", "rhythm": "短促"},
    "摸":  {"contact": "掌心", "rhythm": "持续"},
    "抱":  {"contact": "环绕", "rhythm": "持续"},
    "蹭":  {"contact": "面颊", "rhythm": "反复"},
    "亲":  {"contact": "唇", "rhythm": "短促"},
    "吻":  {"contact": "唇", "rhythm": "持续"},
    "拍":  {"contact": "掌心", "rhythm": "短促"},
    "揉":  {"contact": "掌心", "rhythm": "反复"},
    "牵":  {"contact": "掌心", "rhythm": "持续"},
    "咬":  {"contact": "齿", "rhythm": "短促"},
    "舔":  {"contact": "舌尖", "rhythm": "持续"},
    "挠":  {"contact": "指尖", "rhythm": "反复"},
    "拉":  {"contact": "掌心", "rhythm": "短促"},
    "推":  {"contact": "掌心", "rhythm": "短促"},
    "靠":  {"contact": "肩侧", "rhythm": "持续"},
    "趴":  {"contact": "胸口", "rhythm": "持续"},
    "贴":  {"contact": "面颊", "rhythm": "持续"},
    "吸":  {"contact": "唇", "rhythm": "短促"},
    "掐":  {"contact": "指尖", "rhythm": "短促"},
}

# ── 部位表 ─────────────────────────────────────
BODY_TABLE: dict[str, dict[str, Any]] = {
    "脸":   {"sensitivity": 0.6, "temp": "温", "texture": "有肉感"},
    "脸颊": {"sensitivity": 0.6, "temp": "温", "texture": "有肉感"},
    "耳后": {"sensitivity": 0.8, "temp": "温", "texture": "薄皮"},
    "耳朵": {"sensitivity": 0.7, "temp": "温", "texture": "薄皮"},
    "脖子": {"sensitivity": 0.8, "temp": "温", "texture": "薄皮"},
    "锁骨": {"sensitivity": 0.7, "temp": "温", "texture": "骨感"},
    "肩":   {"sensitivity": 0.4, "temp": "温", "texture": "有肉感"},
    "肩膀": {"sensitivity": 0.4, "temp": "温", "texture": "有肉感"},
    "手":   {"sensitivity": 0.6, "temp": "温", "texture": "有肉感"},
    "手臂": {"sensitivity": 0.4, "temp": "温", "texture": "有肉感"},
    "手指": {"sensitivity": 0.7, "temp": "温", "texture": "薄皮"},
    "手背": {"sensitivity": 0.5, "temp": "温", "texture": "薄皮"},
    "手心": {"sensitivity": 0.7, "temp": "温", "texture": "软"},
    "腰":   {"sensitivity": 0.7, "temp": "温", "texture": "有肉感"},
    "小腹": {"sensitivity": 0.8, "temp": "温", "texture": "软"},
    "背":   {"sensitivity": 0.5, "temp": "温", "texture": "有肉感"},
    "后背": {"sensitivity": 0.5, "temp": "温", "texture": "有肉感"},
    "头":   {"sensitivity": 0.4, "temp": "温", "texture": "发丝"},
    "头发": {"sensitivity": 0.3, "temp": "温", "texture": "发丝"},
    "额头": {"sensitivity": 0.5, "temp": "温", "texture": "薄皮"},
    "嘴唇": {"sensitivity": 0.9, "temp": "热", "texture": "软"},
    "大腿": {"sensitivity": 0.7, "temp": "温", "texture": "有肉感"},
    "大腿内侧": {"sensitivity": 0.9, "temp": "热", "texture": "软"},
    "膝盖": {"sensitivity": 0.4, "temp": "温", "texture": "骨感"},
    "胸口": {"sensitivity": 0.7, "temp": "温", "texture": "有肉感"},
}

# ── 嗅觉 / 味觉 / 听觉 关键词表 ──────────────────
SMELL_KEYWORDS: dict[str, tuple[float, str]] = {
    "香":     (0.5, "淡香"),
    "香水":   (0.6, "香水味"),
    "洗发水": (0.5, "洗发水清香"),
    "沐浴露": (0.5, "沐浴露味"),
    "汗":     (0.4, "微咸的汗味"),
    "烟":     (0.4, "烟味"),
    "花":     (0.5, "花香"),
    "奶":     (0.5, "奶香"),
    "咖啡":   (0.5, "咖啡香"),
    "茶":     (0.4, "茶香"),
    "薄荷":   (0.5, "薄荷凉意"),
    "草莓":   (0.5, "草莓甜香"),
}

TASTE_KEYWORDS: dict[str, tuple[float, str]] = {
    "亲":   (0.5, "唇上温热"),
    "吻":   (0.6, "对方的味道"),
    "舔":   (0.5, "舌尖咸甜"),
    "咬":   (0.4, "齿间压力"),
    "吃":   (0.4, "食物味道"),
    "喝":   (0.3, "液体温度"),
    "甜":   (0.4, "甜"),
    "苦":   (0.3, "苦"),
    "辣":   (0.4, "辣"),
    "草莓": (0.5, "草莓味"),
}

SOUND_KEYWORDS: dict[str, tuple[float, str]] = {
    "呼吸": (0.5, "呼吸声近了"),
    "心跳": (0.6, "胸腔里的震动"),
    "喘":   (0.6, "喘息加重"),
    "哼":   (0.4, "鼻腔里的哼"),
    "笑":   (0.4, "笑声"),
    "叹":   (0.3, "叹息"),
    "低吟": (0.6, "低沉的声音"),
    "耳语": (0.5, "贴在耳边的气音"),
    "雨":   (0.3, "雨声"),
    "风":   (0.3, "风声"),
    "猫叫": (0.3, "猫叫"),
    "啊":   (0.4, "短促的声音"),
    "嗯":   (0.4, "鼻音"),
}


@dataclass
class ChannelState:
    value: float = 0.0
    label: str = ""
    at: float = 0.0


@dataclass
class SomaticState:
    touch: ChannelState = field(default_factory=ChannelState)
    smell: ChannelState = field(default_factory=ChannelState)
    taste: ChannelState = field(default_factory=ChannelState)
    sound: ChannelState = field(default_factory=ChannelState)
    enabled: bool = True

    def channel(self, name: str) -> ChannelState:
        return getattr(self, name)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for ch_name in ("touch", "smell", "taste", "sound"):
            ch = self.channel(ch_name)
            out[ch_name] = {"value": round(ch.value, 3), "label": ch.label, "at": ch.at}
        out["enabled"] = self.enabled
        return out


# ── 核心纯函数 ────────────────────────────────

def decay(value: float, elapsed: float, tau: float) -> float:
    if elapsed <= 0 or tau <= 0:
        return value
    return value * math.exp(-elapsed / tau)


def _find_in_clause(text: str, action: str) -> str | None:
    """在动作词所在的标点分隔小句中找部位词"""
    clauses = re.split(r"[，。！？、；\s,\.!?;]", text)
    for clause in clauses:
        if action not in clause:
            continue
        for body_part in sorted(BODY_TABLE.keys(), key=len, reverse=True):
            if body_part in clause:
                return body_part
    return None


def detect_touch(text: str) -> tuple[str, str] | None:
    """从文本中检测动作和部位，返回 (action, body_part) 或 None。
    多个动作时取文本中最先出现的。"""
    best: tuple[int, str] | None = None
    for action in ACTION_TABLE:
        pos = text.find(action)
        if pos < 0:
            continue
        if best is None or pos < best[0] or (pos == best[0] and len(action) > len(best[1])):
            best = (pos, action)
    if best is None:
        return None
    action = best[1]
    body = _find_in_clause(text, action)
    return (action, body) if body else (action, "")


def detect_channel(text: str, keyword_table: dict[str, tuple[float, str]]) -> tuple[float, str] | None:
    """关键词匹配，长词优先，同长取值高的"""
    best: tuple[int, float, str] | None = None  # (kw_len, val, label)
    for kw, (val, label) in keyword_table.items():
        if kw in text:
            kw_len = len(kw)
            if best is None or kw_len > best[0] or (kw_len == best[0] and val > best[1]):
                best = (kw_len, val, label)
    return (best[1], best[2]) if best else None


def build_touch_label(action: str, body_part: str) -> str:
    """动作表 × 部位表 → 第一人称体感 label"""
    act_info = ACTION_TABLE.get(action, {"contact": "指尖", "rhythm": "短促"})
    if body_part and body_part in BODY_TABLE:
        body_info = BODY_TABLE[body_part]
        parts = [body_part, act_info["contact"], act_info["rhythm"], body_info["temp"], body_info["texture"]]
        if body_info["sensitivity"] >= 0.7:
            parts.append("敏感")
        return "·".join(parts)
    return f"{act_info['contact']}·{act_info['rhythm']}·温"


def compute_touch_value(action: str, body_part: str) -> float:
    base = 0.5
    if body_part and body_part in BODY_TABLE:
        base = 0.3 + BODY_TABLE[body_part]["sensitivity"] * 0.5
    return min(base, 1.0)


def ignite(old: ChannelState, new_value: float, new_label: str, now: float, tau: float) -> ChannelState:
    """叠加旧残值，clamp[0,1]，强label盖弱"""
    residual = decay(old.value, now - old.at, tau) if old.at > 0 else 0.0
    combined = min(residual + new_value, 1.0)
    label = new_label if new_value >= residual else old.label
    return ChannelState(value=combined, label=label, at=now)


def decay_all(state: SomaticState, now: float) -> SomaticState:
    """对所有通道执行衰减"""
    for ch_name in ("touch", "smell", "taste", "sound"):
        ch = state.channel(ch_name)
        if ch.value > 0 and ch.at > 0:
            elapsed = now - ch.at
            new_val = decay(ch.value, elapsed, TAU[ch_name])
            ch.value = new_val
            ch.at = now
    return state


def snapshot(state: SomaticState, now: float) -> str:
    """生成注入 system prompt 的状态块，只输出过阈值的通道"""
    if not state.enabled:
        return ""
    lines: list[str] = []
    for ch_name in ("touch", "smell", "taste", "sound"):
        ch = state.channel(ch_name)
        if ch.at > 0:
            current = decay(ch.value, now - ch.at, TAU[ch_name])
        else:
            current = ch.value
        if current >= ACTIVE_THRESHOLD:
            lines.append(f"[{ch_name}] {current:.2f} | {ch.label}")
    if not lines:
        return ""
    return "⟨body⟩\n" + "\n".join(lines) + "\n⟨/body⟩"


def process_input(state: SomaticState, text: str, now: float | None = None) -> SomaticState:
    """完整管线：detect → ignite，处理一条输入文本"""
    if not state.enabled:
        return state
    if now is None:
        now = time.time()

    touch_hit = detect_touch(text)
    if touch_hit:
        action, body = touch_hit
        val = compute_touch_value(action, body)
        label = build_touch_label(action, body)
        state.touch = ignite(state.touch, val, label, now, TAU["touch"])

    smell_hit = detect_channel(text, SMELL_KEYWORDS)
    if smell_hit:
        state.smell = ignite(state.smell, smell_hit[0], smell_hit[1], now, TAU["smell"])

    taste_hit = detect_channel(text, TASTE_KEYWORDS)
    if taste_hit:
        state.taste = ignite(state.taste, taste_hit[0], taste_hit[1], now, TAU["taste"])

    sound_hit = detect_channel(text, SOUND_KEYWORDS)
    if sound_hit:
        state.sound = ignite(state.sound, sound_hit[0], sound_hit[1], now, TAU["sound"])

    return state
