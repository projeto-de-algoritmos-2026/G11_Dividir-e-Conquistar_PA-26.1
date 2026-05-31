from __future__ import annotations

import math
from typing import Iterable, List, Optional, Tuple

Point = Tuple[float, float, str]
Pair = Tuple[str, str]


def closest_pair(points: Iterable[Point]) -> Tuple[float, Optional[Pair]]:
    pts = list(points)
    if len(pts) < 2:
        return float("inf"), None

    px = sorted(pts, key=lambda p: (p[0], p[1]))
    py = sorted(pts, key=lambda p: p[1])
    return _closest_pair_rec(px, py)


def _closest_pair_rec(px: List[Point], py: List[Point]) -> Tuple[float, Optional[Pair]]:
    n = len(px)
    if n <= 3:
        return _brute_force(px)

    mid = n // 2
    mid_x = px[mid][0]
    qx = px[:mid]
    rx = px[mid:]

    q_ids = {p[2] for p in qx}
    qy = [p for p in py if p[2] in q_ids]
    ry = [p for p in py if p[2] not in q_ids]

    dl, pair_l = _closest_pair_rec(qx, qy)
    dr, pair_r = _closest_pair_rec(rx, ry)

    if dl <= dr:
        d = dl
        best_pair = pair_l
    else:
        d = dr
        best_pair = pair_r

    strip = [p for p in py if abs(p[0] - mid_x) < d]
    ds, pair_s = _strip_closest(strip, d)
    if ds < d:
        return ds, pair_s

    return d, best_pair


def _strip_closest(strip: List[Point], d: float) -> Tuple[float, Optional[Pair]]:
    best = d
    best_pair: Optional[Pair] = None
    for i in range(len(strip)):
        for j in range(i + 1, min(i + 7, len(strip))):
            dist = _distance(strip[i], strip[j])
            if dist < best:
                best = dist
                best_pair = (strip[i][2], strip[j][2])
    return best, best_pair


def _brute_force(points: List[Point]) -> Tuple[float, Optional[Pair]]:
    best = float("inf")
    best_pair: Optional[Pair] = None
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            dist = _distance(points[i], points[j])
            if dist < best:
                best = dist
                best_pair = (points[i][2], points[j][2])
    return best, best_pair


def _distance(p1: Point, p2: Point) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
