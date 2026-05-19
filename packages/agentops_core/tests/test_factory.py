def test_create_factory(client):
    payload = {
        "name": "ACME Metals Inc.",
        "deployment_type": "on_prem",
        "langfuse_endpoint": "http://localhost:3000",
        "langfuse_project_id": "factory-rca",
        "contact_info": {"contact_name": "Mr. Wang", "phone": "0900-000-000"},
        "kpi_targets": {"yield_pct": 95.0},
    }
    response = client.post("/factories", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "ACME Metals Inc."
    assert body["deployment_type"] == "on_prem"
    assert body["langfuse_project_id"] == "factory-rca"
    assert "id" in body
    assert "created_at" in body


def test_list_factories(client):
    client.post("/factories", json={"name": "F1", "deployment_type": "on_prem"})
    client.post("/factories", json={"name": "F2", "deployment_type": "private_cloud"})
    response = client.get("/factories")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    names = {f["name"] for f in body}
    assert names == {"F1", "F2"}


def test_get_factory_by_id(client):
    created = client.post("/factories", json={"name": "F1", "deployment_type": "on_prem"}).json()
    response = client.get(f"/factories/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "F1"


def test_get_factory_not_found(client):
    response = client.get("/factories/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
