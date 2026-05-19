import io


def _setup_agent_with_sops(client, file_payloads: list[tuple[str, bytes, str]]):
    """Create a factory + agent + upload `file_payloads` as SOPSources.

    file_payloads is a list of (filename, bytes, sop_type) tuples.
    """
    factory_id = client.post(
        "/factories", json={"name": "F1", "deployment_type": "on_prem"}
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={
            "factory_id": factory_id,
            "name": "RCA Agent",
            "purpose": "Diagnose yield drop on test floor across IT and OT",
            "runtime_status": "pending",
        },
    ).json()["id"]
    sop_ids: list[str] = []
    for name, content, sop_type in file_payloads:
        resp = client.post(
            f"/factories/{factory_id}/sop-uploads",
            files={"file": (name, io.BytesIO(content), "text/markdown")},
            data={"type": sop_type},
        )
        assert resp.status_code == 201, resp.text
        sop_ids.append(resp.json()["id"])
    return factory_id, agent_id, sop_ids


def test_generate_skill_from_one_md(client):
    md = (
        b"# Yield Drop RCA\n\n## Steps\n\n1. Check Bin 5 spike\n2. Inspect probe card\n"
    )
    _, agent_id, sop_ids = _setup_agent_with_sops(client, [("rca.md", md, "qc_spec")])

    response = client.post(
        "/skill-generations",
        json={"agent_id": agent_id, "sop_source_ids": sop_ids},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["agent_id"] == agent_id
    assert body["version"] == 1
    assert body["status"] == "draft"
    # generated_by_run_id is a relative path like "skills/f2a-<hex>/<skill-name>"
    assert body["generated_by_run_id"].startswith("skills/f2a-")
    # Prompt should mention something from the SOP
    assert "yield" in body["prompt"].lower() or "rca" in body["prompt"].lower()


def test_generate_skill_increments_version(client):
    md = b"# Yield Drop RCA\n\nStep 1.\n"
    _, agent_id, sop_ids = _setup_agent_with_sops(client, [("rca.md", md, "qc_spec")])

    v1 = client.post(
        "/skill-generations",
        json={"agent_id": agent_id, "sop_source_ids": sop_ids},
    ).json()
    v2 = client.post(
        "/skill-generations",
        json={"agent_id": agent_id, "sop_source_ids": sop_ids},
    ).json()
    assert v1["version"] == 1
    assert v2["version"] == 2


def test_generate_skill_requires_agent_to_exist(client):
    response = client.post(
        "/skill-generations",
        json={"agent_id": "00000000-0000-0000-0000-000000000000", "sop_source_ids": []},
    )
    assert response.status_code == 404


def test_generate_skill_requires_at_least_one_sop(client):
    _, agent_id, _ = _setup_agent_with_sops(client, [])
    response = client.post(
        "/skill-generations",
        json={"agent_id": agent_id, "sop_source_ids": []},
    )
    assert response.status_code == 400
