import os
import tempfile

os.environ["DB_FILE"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["REVIEW_SECONDS"] = "3600"
os.environ["ADMIN_KEY"] = "k"

from fastapi.testclient import TestClient  # noqa: E402

from scholarhub.api import app  # noqa: E402

client = TestClient(app)
GOOD = {"scholarship_id": 1, "full_name": "Aline Uwase", "email": "aline@example.com"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_lists_six_scholarships_in_screen_shape():
    rows = client.get("/scholarships").json()
    assert len(rows) == 6
    for k in ("id", "name", "field", "benefit", "timeline", "eligibility", "campusLogistics", "remainingSlots"):
        assert k in rows[0]
    assert rows[0]["name"] == "INES-Ruhengeri"
    assert rows[0]["timeline"].startswith("Closes: October 31, 2026")


def test_detail_and_404():
    assert client.get("/scholarships/3").json()["name"] == "University of Rwanda"
    assert client.get("/scholarships/99").status_code == 404


def test_apply_then_pending_status():
    r = client.post("/applications", json=GOOD)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending" and body["already_applied"] is False
    got = client.get(f"/applications/{body['id']}").json()
    assert got["status"] == "pending" and got["scholarship"]["name"] == "INES-Ruhengeri"


def test_apply_twice_is_idempotent_and_uses_one_slot():
    before = client.get("/scholarships/2").json()["slotsLeft"]
    a = {**GOOD, "scholarship_id": 2, "email": "twice@example.com"}
    first = client.post("/applications", json=a).json()
    second = client.post("/applications", json=a).json()
    assert second["id"] == first["id"] and second["already_applied"] is True
    assert client.get("/scholarships/2").json()["slotsLeft"] == before - 1


def test_bad_input_refused():
    for bad in ({**GOOD, "email": "nope"}, {**GOOD, "full_name": "A"}, {**GOOD, "scholarship_id": 0}):
        assert client.post("/applications", json=bad).status_code == 422
    assert client.post("/applications", json={**GOOD, "scholarship_id": 99}).status_code == 404


def test_full_scholarship_refuses():
    for i in range(2):
        assert client.post("/applications", json={**GOOD, "scholarship_id": 4, "email": f"u{i}@x.com"}).status_code == 200
    r = client.post("/applications", json={**GOOD, "scholarship_id": 4, "email": "late@x.com"})
    assert r.status_code == 409


def test_board_decision_needs_key():
    a = client.post("/applications", json={**GOOD, "scholarship_id": 5, "email": "d@x.com"}).json()
    assert client.patch(f"/applications/{a['id']}", json={"status": "accepted"}).status_code == 401
    r = client.patch(f"/applications/{a['id']}", json={"status": "accepted"}, headers={"X-Admin-Key": "k"})
    assert r.json()["status"] == "accepted"
    assert client.get(f"/applications/{a['id']}").json()["status"] == "accepted"
