"""Map flows2agents.ir.SkillIR to a Skill entity payload (prompt / tool_specs / tests)."""
from __future__ import annotations

from typing import Any

from flows2agents.ir import SkillIR


def skill_ir_to_skill_payload(ir: SkillIR) -> dict[str, Any]:
    """Translate the flows2agents IR into the dict shape SkillCreate expects.

    Mapping decisions for v0.1:
    - `prompt`: human-readable rendering of display_name + description + triggers + procedure.
      This is what an agent runtime would receive as its system prompt.
    - `tool_specs`: empty list for now. flows2agents doesn't emit tool schemas
      directly; Plan 3+ will derive these from procedure.body when we integrate
      with Claude Skill / MCP target adapters.
    - `golden_test_cases`: one per Example in the IR.
    """
    prompt = _render_prompt(ir)
    golden = [{"q": e.query, "a": e.response_outline} for e in ir.examples]
    return {
        "prompt": prompt,
        "tool_specs": [],
        "golden_test_cases": golden,
    }


def _render_prompt(ir: SkillIR) -> str:
    lines: list[str] = []
    lines.append(f"# {ir.display_name}")
    lines.append("")
    lines.append(ir.description)
    if ir.triggers:
        lines.append("")
        lines.append("## Triggers")
        for t in ir.triggers:
            lines.append(f"- {t}")
    if ir.procedure:
        lines.append("")
        lines.append("## Procedure")
        for i, step in enumerate(ir.procedure, start=1):
            lines.append(f"### {i}. {step.title}")
            if step.body:
                lines.append(step.body)
    if ir.pitfalls:
        lines.append("")
        lines.append("## Pitfalls")
        for p in ir.pitfalls:
            lines.append(f"- {p}")
    return "\n".join(lines).strip() + "\n"
