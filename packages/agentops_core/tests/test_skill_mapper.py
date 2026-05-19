from flows2agents.ir import Example, ProcedureStep, Provenance, Resource, SkillIR

from agentops_core.services.skill_mapper import skill_ir_to_skill_payload


def _make_ir() -> SkillIR:
    return SkillIR(
        name="rca-yield-drop",
        display_name="Yield Drop RCA",
        description="Diagnose yield drop on the test floor across IT and OT signals.",
        triggers=["yield 突然下降", "Bin 5 spike"],
        procedure=[
            ProcedureStep(
                title="Check MES bin distribution",
                body="query_mes(bin_distribution, last_4h)",
                traces_to=["wf-001"],
            ),
            ProcedureStep(
                title="Inspect probe card touchdown count",
                body="query_probe_card(card_id)",
                traces_to=["kn-001"],
            ),
        ],
        examples=[
            Example(query="Yield 從 95% 掉到 78%", response_outline="Check Bin 5 spike → tester #7 → probe card 接觸電阻"),
        ],
        resources=[Resource(filename="probe_card_lifespan.md", content="...")],
        provenance=Provenance(from_description=True),
    )


def test_skill_ir_maps_to_payload():
    ir = _make_ir()
    payload = skill_ir_to_skill_payload(ir)
    assert "Yield Drop RCA" in payload["prompt"]
    assert "yield 突然下降" in payload["prompt"]
    assert "Check MES bin distribution" in payload["prompt"]
    assert isinstance(payload["tool_specs"], list)
    assert isinstance(payload["golden_test_cases"], list)
    # examples → golden test cases
    assert len(payload["golden_test_cases"]) == 1
    assert payload["golden_test_cases"][0]["q"] == "Yield 從 95% 掉到 78%"


def test_skill_payload_empty_procedure_still_works():
    ir = SkillIR(
        name="empty-skill",
        display_name="Empty",
        description="No procedure.",
        triggers=[],
        provenance=Provenance(),
    )
    payload = skill_ir_to_skill_payload(ir)
    assert payload["prompt"]  # non-empty
    assert payload["tool_specs"] == []
    assert payload["golden_test_cases"] == []
