import io
from pathlib import Path


def _create_factory(client):
    resp = client.post("/factories", json={"name": "F1", "deployment_type": "on_prem"})
    return resp.json()["id"]


def test_upload_pdf_creates_sop_source(client, tmp_path: Path):
    factory_id = _create_factory(client)
    file_content = b"%PDF-1.4 fake pdf bytes"
    response = client.post(
        f"/factories/{factory_id}/sop-uploads",
        files={
            "file": ("refund-flow.pdf", io.BytesIO(file_content), "application/pdf")
        },
        data={"type": "pdf"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type"] == "pdf"
    assert body["factory_id"] == factory_id
    assert body["storage_ref"].startswith("sop/")
    assert body["storage_ref"].endswith("-refund-flow.pdf")

    saved = tmp_path / body["storage_ref"]
    assert saved.exists()
    assert saved.read_bytes() == file_content


def test_upload_transcript_txt(client):
    factory_id = _create_factory(client)
    content = "老師傅訪談記錄: probe card 壽命約 200 萬次\n".encode()
    response = client.post(
        f"/factories/{factory_id}/sop-uploads",
        files={"file": ("master-interview.txt", io.BytesIO(content), "text/plain")},
        data={"type": "transcript"},
    )
    assert response.status_code == 201
    assert response.json()["type"] == "transcript"


def test_upload_with_unknown_type_returns_422(client):
    factory_id = _create_factory(client)
    response = client.post(
        f"/factories/{factory_id}/sop-uploads",
        files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")},
        data={"type": "not_a_valid_type"},
    )
    assert response.status_code == 422


def test_upload_to_unknown_factory_returns_404(client):
    response = client.post(
        "/factories/00000000-0000-0000-0000-000000000000/sop-uploads",
        files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")},
        data={"type": "pdf"},
    )
    assert response.status_code == 404
