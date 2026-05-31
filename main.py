from __future__ import annotations

import random
import select
import sys
import termios
from dataclasses import dataclass
from typing import List, Optional

from closest_pair import closest_pair

WIDTH = 40
HEIGHT = 20
TICK_SECONDS = 1.0
ALERT_DISTANCE = 3.0
COLLISION_DISTANCE = 1.0
INITIAL_OBJECTS = 4
MAX_OBJECTS = 10
ID_POOL = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
DIRECTIONS = [(1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)]


@dataclass
class MovingObject:
    obj_id: str
    x: float
    y: float
    dx: float
    dy: float


def main() -> None:
    available_ids = ID_POOL.copy()
    objects = _spawn_objects(available_ids, WIDTH, HEIGHT, 0.0, count=INITIAL_OBJECTS)
    last_message: Optional[str] = None
    ticks = 0
    input_buffer = ""
    terminal_state = _enter_input_mode()

    try:
        while True:
            cmd, input_buffer = _read_input(input_buffer, timeout=TICK_SECONDS)
            if cmd:
                action = _handle_command(cmd, objects)
                if action == "quit":
                    print("\nSaindo...")
                    break
                last_message = action

            ticks += 1
            objects, released_ids = _update_positions(objects, WIDTH, HEIGHT)
            available_ids.extend(released_ids)

            elapsed_seconds = ticks * TICK_SECONDS
            remaining = MAX_OBJECTS - len(objects)
            if remaining > 0:
                objects.extend(
                    _spawn_objects(
                        available_ids,
                        WIDTH,
                        HEIGHT,
                        elapsed_seconds,
                        max_new=remaining,
                    )
                )

            points = [(o.x, o.y, o.obj_id) for o in objects]
            min_dist, pair = closest_pair(points)

            alert_msg = ""
            if pair and min_dist < ALERT_DISTANCE:
                alert_msg = (
                    f"[ALERTA] Satelites {pair[0]} e {pair[1]} estao muito proximos!"
                )

            screen = _render(
                objects,
                WIDTH,
                HEIGHT,
                alert_msg,
                min_dist,
                pair,
                last_message,
                input_buffer,
            )
            _clear_screen()
            sys.stdout.write(screen)
            sys.stdout.flush()

            if pair and min_dist < COLLISION_DISTANCE:
                print("\nCOLISAO! Fim de jogo.")
                break
    finally:
        _restore_input_mode(terminal_state)


def _spawn_objects(
    available_ids: List[str],
    width: int,
    height: int,
    elapsed_seconds: float,
    count: Optional[int] = None,
    max_new: Optional[int] = None,
) -> List[MovingObject]:
    new_objects: List[MovingObject] = []
    attempts = count if count is not None else _spawn_attempts(elapsed_seconds)
    chance = 1.0 if count is not None else _spawn_chance(elapsed_seconds)
    if max_new is not None:
        attempts = min(attempts, max_new)

    for _ in range(attempts):
        if not available_ids:
            break
        if random.random() > chance:
            continue
        obj_id = available_ids.pop(0)
        new_objects.append(_spawn_single(obj_id, width, height))

    return new_objects


def _spawn_attempts(elapsed_seconds: float) -> int:
    return 1 + int(elapsed_seconds // 45)


def _spawn_chance(elapsed_seconds: float) -> float:
    return min(0.45, 0.05 + elapsed_seconds * 0.004)


def _spawn_single(obj_id: str, width: int, height: int) -> MovingObject:
    edge = random.choice(["top", "bottom", "left", "right"])
    if edge == "top":
        x = random.uniform(0, width - 1)
        y = 0.0
        dx, dy = 0.0, 1.0
    elif edge == "bottom":
        x = random.uniform(0, width - 1)
        y = float(height - 1)
        dx, dy = 0.0, -1.0
    elif edge == "left":
        x = 0.0
        y = random.uniform(0, height - 1)
        dx, dy = 1.0, 0.0
    else:
        x = float(width - 1)
        y = random.uniform(0, height - 1)
        dx, dy = -1.0, 0.0

    return MovingObject(obj_id, x, y, dx, dy)


def _update_positions(
    objects: List[MovingObject],
    width: int,
    height: int,
) -> tuple[List[MovingObject], List[str]]:
    alive: List[MovingObject] = []
    released_ids: List[str] = []
    for obj in objects:
        obj.x += obj.dx
        obj.y += obj.dy

        if obj.x < 0 or obj.x > width - 1 or obj.y < 0 or obj.y > height - 1:
            released_ids.append(obj.obj_id)
            continue

        alive.append(obj)

    return alive, released_ids


def _render(
    objects: List[MovingObject],
    width: int,
    height: int,
    alert_msg: str,
    min_dist: float,
    pair: Optional[tuple[str, str]],
    last_message: Optional[str],
    input_buffer: str,
) -> str:
    grid = [[" " for _ in range(width)] for _ in range(height)]

    for obj in objects:
        ix = _clamp(int(round(obj.x)), 0, width - 1)
        iy = _clamp(int(round(obj.y)), 0, height - 1)
        if grid[iy][ix] == " ":
            grid[iy][ix] = obj.obj_id
        else:
            grid[iy][ix] = "*"

    if pair:
        pair_set = set(pair)
        for obj in objects:
            if obj.obj_id not in pair_set:
                continue
            ix = _clamp(int(round(obj.x)), 0, width - 1)
            iy = _clamp(int(round(obj.y)), 0, height - 1)
            grid[iy][ix] = _color_red(obj.obj_id)

    lines = []
    header_width = width + 2
    lines.append("=" * header_width)
    lines.append("RADAR DE TRAFEGO ORBITAL".center(header_width))
    lines.append("=" * header_width)

    for row in grid:
        lines.append("[" + "".join(row) + "]")

    lines.append("=" * header_width)
    lines.append("SISTEMA DE ALERTA:")

    if alert_msg and pair:
        lines.append(alert_msg)
        lines.append(f"Distancia Atual: {min_dist:.2f} unidades.")
    else:
        lines.append("Nenhum alerta no momento.")

    lines.append("Comandos validos: letra do aviao (ex: A) ou 'sair'")
    if last_message:
        lines.append(last_message)
    lines.append(f"Digite seu comando: {input_buffer}")

    return "\n".join(lines) + "\n"


def _handle_command(cmd: str, objects: List[MovingObject]) -> Optional[str]:
    text = cmd.strip()
    if not text:
        return None

    lowered = text.lower()
    if lowered in {"q", "quit", "sair"}:
        return "quit"

    parts = text.split()
    if len(parts) != 1 or len(parts[0]) != 1:
        return "Comando invalido. Digite somente a letra (ex: A)."

    obj_id = parts[0].upper()

    obj = next((o for o in objects if o.obj_id == obj_id), None)
    if not obj:
        return f"Objeto '{obj_id}' nao encontrado."

    obj.dx, obj.dy = _random_direction(exclude=(obj.dx, obj.dy))
    return f"Rota de '{obj_id}' desviada."


def _read_input(buffer: str, timeout: float) -> tuple[Optional[str], str]:
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        return None, buffer

    while True:
        char = sys.stdin.read(1)
        if not char:
            break

        if char in {"\n", "\r"}:
            command = buffer.strip()
            return command if command else None, ""

        if char in {"\b", "\x7f"}:
            buffer = buffer[:-1]
        elif char.isprintable():
            buffer += char

        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            break

    return None, buffer


def _clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _random_direction(exclude: tuple[float, float]) -> tuple[float, float]:
    excluded = (float(int(exclude[0])), float(int(exclude[1])))
    options = [d for d in DIRECTIONS if d != excluded]
    if not options:
        options = DIRECTIONS
    return random.choice(options)


def _color_red(text: str) -> str:
    return f"\033[31m{text}\033[0m"


def _enter_input_mode() -> Optional[list[int]]:
    if not sys.stdin.isatty():
        return None

    fd = sys.stdin.fileno()
    old_state = termios.tcgetattr(fd)
    new_state = termios.tcgetattr(fd)
    new_state[3] &= ~(termios.ECHO | termios.ICANON)
    termios.tcsetattr(fd, termios.TCSADRAIN, new_state)
    return old_state


def _restore_input_mode(state: Optional[list[int]]) -> None:
    if state is None:
        return

    fd = sys.stdin.fileno()
    termios.tcsetattr(fd, termios.TCSADRAIN, state)


if __name__ == "__main__":
    main()
