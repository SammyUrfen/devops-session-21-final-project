"""API tests for POST /api/mazes/community and the source split (PLAN.md section 11)."""

from app.maze import WALL_E, generate

SEED = 20241012


def _publish_drawn(client, title="Hand Drawn", width=8, height=8, author=None, grid=None):
    body = {"title": title, "width": width, "height": height,
            "grid": grid if grid is not None else generate(width, height, SEED)}
    if author is not None:
        body["author"] = author
    return client.post("/api/mazes/community", json=body)


def test_drawn_maze_is_accepted_and_marked_community(client):
    r = _publish_drawn(client, author="explorer")
    assert r.status_code == 201, r.text
    maze = r.json()
    assert maze["source"] == "COMMUNITY"
    assert maze["seed"] is None  # a drawn grid has no seed, the grid is the only source of truth
    assert maze["author"] == "explorer"
    assert maze["solution_length"] >= 15
    assert maze["difficulty"] in {"EASY", "MEDIUM", "HARD"}


def test_derived_label_matches_the_path_length(client):
    maze = _publish_drawn(client).json()
    length = maze["solution_length"]
    expected = "EASY" if length < 20 else "MEDIUM" if length < 45 else "HARD"
    assert maze["difficulty"] == expected


def test_disagreeing_wall_is_rejected(client):
    grid = generate(8, 8, SEED)
    grid[0][0] ^= WALL_E
    r = _publish_drawn(client, grid=grid)
    assert r.status_code == 422
    assert "disagree" in r.json()["detail"]


def test_open_border_is_rejected(client):
    grid = generate(8, 8, SEED)
    grid[0][0] &= ~1  # clear the N bit of the top-left cell
    r = _publish_drawn(client, grid=grid)
    assert r.status_code == 422
    assert "border" in r.json()["detail"]


def test_unsolvable_grid_is_rejected(client):
    grid = generate(8, 8, SEED)
    grid[0][0] = 15
    grid[0][1] |= 8
    grid[1][0] |= 1
    r = _publish_drawn(client, grid=grid)
    assert r.status_code == 422
    assert "no path" in r.json()["detail"]


def test_value_above_fifteen_is_rejected(client):
    grid = generate(8, 8, SEED)
    grid[4][4] = 99
    r = _publish_drawn(client, grid=grid)
    assert r.status_code == 422
    assert "0 and 15" in r.json()["detail"]


def test_size_outside_the_range_is_rejected(client):
    r = _publish_drawn(client, width=2, height=2)
    assert r.status_code == 422
    assert "between 4 and 20" in r.json()["detail"]


def test_difficulty_put_on_a_drawn_maze_is_refused(client):
    maze = _publish_drawn(client).json()
    r = client.put(f"/api/mazes/{maze['id']}", json={"difficulty": "HARD"})
    assert r.status_code == 422
    assert "drawn" in r.json()["detail"]
    # A title-only edit still works, and the grid is untouched.
    renamed = client.put(f"/api/mazes/{maze['id']}", json={"title": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Renamed"
    assert renamed.json()["grid"] == maze["grid"]


def test_list_filters_by_source(client):
    generated = client.post("/api/mazes", json={"title": "Carved", "difficulty": "EASY"}).json()
    drawn = _publish_drawn(client).json()

    def ids(query: str) -> list[int]:
        return [m["id"] for m in client.get(f"/api/mazes{query}").json()]

    assert ids("?source=GENERATED") == [generated["id"]]
    assert ids("?source=COMMUNITY") == [drawn["id"]]
    assert sorted(ids("")) == sorted([generated["id"], drawn["id"]])


def test_stats_counts_by_source(client):
    client.post("/api/mazes", json={"title": "Carved", "difficulty": "EASY"})
    _publish_drawn(client)
    stats = client.get("/api/mazes/stats").json()
    assert stats["by_source"] == {"GENERATED": 1, "COMMUNITY": 1}
    assert stats["total"] == 2
