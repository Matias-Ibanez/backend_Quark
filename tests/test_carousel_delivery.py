import json
from PIL import Image
from backend import agent, store


def test_carousel_exports_share_group_and_keep_narrative_order(tmp_path):
    store.init_db()
    pid = store.create_project("Carrusel")["id"]
    for index in range(1, 4):
        (tmp_path / f"final-{index:02}.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320"><text x="20" y="40">Hola</text></svg>')
        Image.new("RGB", (320, 320), "black").save(tmp_path / f"final-{index:02}.png")
    urls = agent.import_hermes_media(pid, tmp_path, {}, require_vector=True, slides=3, dimensions=[320, 320])
    assert len(urls) == 3
    with store.connection() as db:
        rows = db.execute("SELECT payload,result FROM jobs WHERE project_id=? ORDER BY rowid", (pid,)).fetchall()
    payloads = [json.loads(row["payload"]) for row in rows]
    assert len({payload["carouselId"] for payload in payloads}) == 1
    assert [payload["slideIndex"] for payload in payloads] == [1, 2, 3]
    assert all(payload["slideCount"] == 3 for payload in payloads)
    assert [json.loads(row["result"])["vectorUrl"] for row in rows] == urls
    assert all((store.DATA / "exports" / json.loads(row["result"])["filename"]).is_file() for row in rows)
