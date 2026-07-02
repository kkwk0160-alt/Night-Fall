"""
念头池 — 闪念与执念的流转系统
闪念: 强度 0.5 起步，每拍 ×0.82 衰减
执念: 涨过 0.8 升级，每拍 ×1.10 自己长
执念够强 (≥0.85) 反哺欲望维度，推够三次出池
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

FLASH_DECAY = 0.82
OBSESSION_GROWTH = 1.10
OBSESSION_THRESHOLD = 0.8
LIBIDO_PUSH_THRESHOLD = 0.85
LIBIDO_PUSH_AMOUNT = 0.18
MAX_PUSHES = 3


@dataclass
class Thought:
    key: str
    intensity: float = 0.5
    is_obsession: bool = False
    push_count: int = 0
    at: float = 0.0

    @property
    def resolved(self) -> bool:
        return self.is_obsession and self.push_count >= MAX_PUSHES


@dataclass
class ThoughtPool:
    thoughts: dict[str, Thought] = field(default_factory=dict)
    libido: float = 0.0

    def tick(self, now: float | None = None) -> list[str]:
        """一拍：衰减闪念、增长执念、反哺欲望。返回本拍出池的念头key列表"""
        if now is None:
            now = time.time()

        resolved: list[str] = []
        to_remove: list[str] = []

        for key, t in self.thoughts.items():
            if t.is_obsession:
                t.intensity = min(t.intensity * OBSESSION_GROWTH, 1.0)
                if t.intensity >= LIBIDO_PUSH_THRESHOLD and t.push_count < MAX_PUSHES:
                    self.libido = min(self.libido + LIBIDO_PUSH_AMOUNT, 1.0)
                    t.push_count += 1
                if t.resolved:
                    resolved.append(key)
                    to_remove.append(key)
            else:
                t.intensity *= FLASH_DECAY
                if t.intensity < 0.05:
                    to_remove.append(key)
                elif t.intensity >= OBSESSION_THRESHOLD:
                    t.is_obsession = True

            t.at = now

        for key in to_remove:
            del self.thoughts[key]

        return resolved

    def ignite(self, key: str, boost: float = 0.5, now: float | None = None) -> Thought:
        """点燃或加强一个念头"""
        if now is None:
            now = time.time()

        if key in self.thoughts:
            t = self.thoughts[key]
            t.intensity = min(t.intensity + boost, 1.0)
            t.at = now
            if not t.is_obsession and t.intensity >= OBSESSION_THRESHOLD:
                t.is_obsession = True
            return t

        t = Thought(key=key, intensity=boost, at=now)
        if t.intensity >= OBSESSION_THRESHOLD:
            t.is_obsession = True
        self.thoughts[key] = t
        return t

    def snapshot(self) -> str:
        """生成念头池状态块"""
        lines: list[str] = []

        sorted_thoughts = sorted(self.thoughts.values(), key=lambda t: t.intensity, reverse=True)
        for t in sorted_thoughts[:5]:
            tag = "执念" if t.is_obsession else "闪念"
            lines.append(f"[{tag}] {t.key} | {t.intensity:.2f}")

        if self.libido > 0.1:
            lines.append(f"[欲望] {self.libido:.2f}")

        if not lines:
            return ""
        return "⟨mind⟩\n" + "\n".join(lines) + "\n⟨/mind⟩"

    def active_thoughts(self) -> list[Thought]:
        return sorted(self.thoughts.values(), key=lambda t: t.intensity, reverse=True)

    def to_dict(self) -> dict:
        return {
            "thoughts": {
                k: {
                    "intensity": round(t.intensity, 3),
                    "is_obsession": t.is_obsession,
                    "push_count": t.push_count,
                }
                for k, t in self.thoughts.items()
            },
            "libido": round(self.libido, 3),
        }
