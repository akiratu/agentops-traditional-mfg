def _create_factory(client):
    return client.post("/factories", json={"name": "F1", "deployment_type": "on_prem"}).json()["id"]


def test_create_sop_source(client):
    factory_id = _create_factory(client)
    payload = {
        "factory_id": factory_id,
        "type": "pdf",
        "storage_ref": "/data/sop/refund.pdf",
        "metadata": {"original_filename": "refund.pdf", "pages": 12},
    }
    response = client.post("/sop-sources", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type"] == "pdf"
    assert body["storage_ref"] == "/data/sop/refund.pdf"
    assert body["metadata"]["pages"] == 12


def test_list_sop_sources(client):
    factory_id = _create_factory(client)
    client.post("/sop-sources", json={"factory_id": factory_id, "type": "pdf", "storage_ref": "/a.pdf", "metadata": {}})
    client.post("/sop-sources", json={"factory_id": factory_id, "type": "transcript", "storage_ref": "/b.txt", "metadata": {}})
    response = client.get(f"/sop-sources?factory_id={factory_id}")
    assert response.status_code == 200
    assert len(response.json()) == 2
