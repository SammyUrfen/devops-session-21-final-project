#!/usr/bin/env python3
"""Show every guard on a hand-drawn maze refusing a bad grid, and accepting a good one.

Capture items 26, 27 and 28 of .evidence/CAPTURE.md. One run prints one line for each rule, so a
single screenshot covers all of them. The standard library only, because the capture must run on
the host with no virtual environment.

Usage, from the repository root:

    python3 scripts/verify_guards.py                          # the compose stack
    python3 scripts/verify_guards.py http://mazehub.local     # through the Ingress

The five structural rules live in backend/app/maze.py, in check_drawn_grid. This script builds one
payload for each rule, so a change to a rule that the grid no longer breaks shows up as a 201 here.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys
import urllib.error
import urllib.request

# The wall bitmask of PLAN.md section 10. A set bit means the wall stands.
WALL_N = 1
WALL_E = 2

GOOD_GRID_FILE = pathlib.Path(__file__).with_name("grid.json")
TIMEOUT_SECONDS = 15


def request(method: str, url: str, payload: dict | None) -> tuple[int, str]:
    """Return the status code and the detail sentence, without raising on a 4xx."""
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=body, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            return response.status, json.load(response).get("title", "accepted")
    except urllib.error.HTTPError as error:
        raw = error.read().decode()
        try:
            return error.code, json.loads(raw).get("detail", raw)
        except json.JSONDecodeError:
            return error.code, raw


def bad_payloads(good: dict) -> list[tuple[str, dict]]:
    """One payload for each of the five rules, in the order check_drawn_grid applies them."""
    out: list[tuple[str, dict]] = []

    # Rule 1, size. 2x2 is below MIN_DRAWN_SIZE, so no cell is ever indexed.
    too_small = copy.deepcopy(good)
    too_small.update(width=2, height=2, grid=[[15, 15], [15, 15]])
    out.append(("1 size out of range", too_small))

    # Rule 1 again, the shape. The declared size and the row count disagree.
    wrong_shape = copy.deepcopy(good)
    wrong_shape["grid"] = wrong_shape["grid"][:-1]
    out.append(("1 shape does not match", wrong_shape))

    # Rule 2, cell values. 99 carries bits the renderer and the solver both drop.
    bad_value = copy.deepcopy(good)
    bad_value["grid"][3][4] = 99
    out.append(("2 cell value out of 0..15", bad_value))

    # Rule 3, closed border. Take the north wall off the top left cell.
    open_border = copy.deepcopy(good)
    open_border["grid"][0][0] &= ~WALL_N
    out.append(("3 open border", open_border))

    # Rule 4, neighbours agree. Open the east side of one cell and leave its neighbour closed.
    disagree = copy.deepcopy(good)
    disagree["grid"][0][0] |= WALL_E
    disagree["grid"][0][1] |= WALL_N | WALL_E
    disagree["grid"][0][0] &= ~WALL_E
    out.append(("4 neighbours disagree", disagree))

    # Rule 5, a path exists. Every wall stands, so the entrance reaches nothing.
    no_path = copy.deepcopy(good)
    size = no_path["width"]
    no_path["grid"] = [[15] * size for _ in range(no_path["height"])]
    out.append(("5 no path to the exit", no_path))

    return out


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
    good = json.loads(GOOD_GRID_FILE.read_text())
    print(f"base URL: {base}\n")

    print("Item 27, each structural rule refuses its own bad grid:")
    failures = 0
    for name, payload in bad_payloads(good):
        code, detail = request("POST", f"{base}/api/mazes/community", payload)
        print(f"  {code}  {name:26}  {detail}")
        if code != 422:
            failures += 1

    print("\nItem 26, the good grid is accepted:")
    body = json.dumps(good).encode()
    req = urllib.request.Request(
        f"{base}/api/mazes/community", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
        created = json.load(response)
        print(
            f"  {response.status}  id={created['id']}  source={created['source']}  "
            f"difficulty={created['difficulty']} (derived)  "
            f"solution_length={created['solution_length']}  seed={created['seed']}"
        )

    maze_id = created["id"]
    print("\nItem 28, a difficulty change on a drawn maze is refused, a title change is not:")
    code, detail = request("PUT", f"{base}/api/mazes/{maze_id}", {"difficulty": "HARD"})
    print(f"  {code}  difficulty -> HARD           {detail}")
    if code != 422:
        failures += 1
    code, detail = request("PUT", f"{base}/api/mazes/{maze_id}", {"title": "Curl Sketch, renamed"})
    print(f"  {code}  title -> Curl Sketch, renamed  {detail}")
    if code != 200:
        failures += 1

    print(f"\n{failures} unexpected status codes")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
