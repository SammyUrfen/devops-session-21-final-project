"""API tests. The conftest fixture points the app at a throwaway SQLite file."""

from app.maze import SIZES


def _publish(client, title="Spiral", difficulty="EASY", author=None):
    body = {"title": title, "difficulty": difficulty}
    if author is not None:
        body["author"] = author
    r = client.post("/api/mazes", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}


def test_ready_checks_db(client):
    assert client.get("/ready").json() == {"status": "READY"}


def test_metrics_exposed(client):
    client.get("/health")
    assert "http_requests_total" in client.get("/metrics").text


def test_config_and_root(client):
    assert "banner" in client.get("/api/config").json()
    assert client.get("/").status_code == 200


def test_create_sets_size_grid_and_solution(client):
    maze = _publish(client, "Hedge", "MEDIUM")
    width, height = SIZES["MEDIUM"]
    assert (maze["width"], maze["height"]) == (width, height)
    assert len(maze["grid"]) == height
    assert all(len(row) == width for row in maze["grid"])
    assert maze["author"] == "anonymous"
    assert maze["solution_length"] >= width + height - 1
    assert maze["completion_count"] == 0


def test_rejects_bad_difficulty(client):
    assert client.post("/api/mazes", json={"title": "x", "difficulty": "INSANE"}).status_code == 422


def test_read_and_404(client):
    maze = _publish(client, "Knot")
    assert client.get(f"/api/mazes/{maze['id']}").json()["title"] == "Knot"
    assert client.get("/api/mazes/9999").status_code == 404


def test_list_newest_first_and_filters(client):
    _publish(client, "first", "EASY", author="explorer")
    _publish(client, "second", "HARD", author="ajij")
    assert [m["title"] for m in client.get("/api/mazes").json()] == ["second", "first"]
    assert [m["title"] for m in client.get("/api/mazes?difficulty=EASY").json()] == ["first"]
    assert [m["title"] for m in client.get("/api/mazes?author=ajij").json()] == ["second"]


def test_update_difficulty_changes_size(client):
    maze = _publish(client, "Grow", "EASY")
    r = client.put(f"/api/mazes/{maze['id']}", json={"title": "Grown", "difficulty": "HARD"})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Grown"
    assert (body["width"], body["height"]) == SIZES["HARD"]
    assert len(body["grid"]) == SIZES["HARD"][1]
    assert body["grid"] != maze["grid"]


def test_delete_then_404(client):
    maze = _publish(client, "Gone")
    assert client.delete(f"/api/mazes/{maze['id']}").status_code == 204
    assert client.get(f"/api/mazes/{maze['id']}").status_code == 404
    assert client.delete(f"/api/mazes/{maze['id']}").status_code == 404


def test_stats(client):
    _publish(client, "a", "EASY", author="explorer")
    maze = _publish(client, "b", "HARD", author="ajij")
    client.post(
        f"/api/mazes/{maze['id']}/completions",
        json={"player": "nova", "moves": maze["solution_length"], "seconds": 30},
    )
    assert client.get("/api/mazes/stats").json() == {
        "total": 2,
        "by_difficulty": {"EASY": 1, "MEDIUM": 0, "HARD": 1},
        "by_source": {"GENERATED": 2, "COMMUNITY": 0},
        "completions": 1,
        "authors": 2,
    }


def test_solution_endpoint(client):
    maze = _publish(client, "Path", "MEDIUM")
    body = client.get(f"/api/mazes/{maze['id']}/solution").json()
    assert body["length"] == maze["solution_length"] == len(body["path"])
    assert body["path"][0] == [0, 0]
    assert body["path"][-1] == [maze["width"] - 1, maze["height"] - 1]


def test_completion_flow(client):
    maze = _publish(client, "Run", "EASY")
    r = client.post(
        f"/api/mazes/{maze['id']}/completions",
        json={"player": "nova", "moves": maze["solution_length"] + 5, "seconds": 42},
    )
    assert r.status_code == 201
    done = r.json()
    assert done["maze_id"] == maze["id"]
    assert done["maze_title"] == "Run"
    assert done["player"] == "nova"
    assert client.get(f"/api/mazes/{maze['id']}").json()["completion_count"] == 1
    assert [c["id"] for c in client.get("/api/completions?player=nova").json()] == [done["id"]]
    assert client.get("/api/completions?player=nobody").json() == []


def test_completion_accepts_the_optimal_run(client):
    """A player who walks the shortest path takes solution_length - 1 moves, one per crossed wall.

    solution_length counts cells, so the perfect run is one move short of it. The guard must accept
    that number, otherwise the best possible run is the one run the server refuses.
    """
    maze = _publish(client, "Perfect", "EASY")
    best_moves = maze["solution_length"] - 1
    r = client.post(
        f"/api/mazes/{maze['id']}/completions",
        json={"player": "nova", "moves": best_moves, "seconds": 9},
    )
    assert r.status_code == 201, r.text
    assert r.json()["moves"] == best_moves


def test_completion_rejects_impossible_move_count(client):
    """The cheat guard: fewer moves than the shortest path cannot happen in a real run."""
    maze = _publish(client, "Cheat", "EASY")
    r = client.post(
        f"/api/mazes/{maze['id']}/completions",
        json={"player": "cheater", "moves": maze["solution_length"] - 2, "seconds": 1},
    )
    assert r.status_code == 422
    assert "shortest path" in r.json()["detail"].lower()


def test_completion_on_missing_maze_404(client):
    r = client.post("/api/mazes/9999/completions", json={"player": "p", "moves": 10, "seconds": 1})
    assert r.status_code == 404
