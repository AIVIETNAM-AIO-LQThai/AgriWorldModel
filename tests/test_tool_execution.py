import datetime

import pytest

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.event import Event
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.decisions.context import build_decision_context
from agriworldmodel.decisions.schemas import DecisionType
from agriworldmodel.tools.execution import execute_nutrient_context_tools
from agriworldmodel.tools.schemas import ToolExecutionStatus


UTC = datetime.timezone.utc

def dt(day: int) -> datetime.datetime:
    return datetime.datetime(
        2026, 9, day, 8, 0, tzinfo=UTC,
    )

def make_context(
    db_session, *, amount=2.0, amount_unit="kg", basis="per_tree",
):
    farm = Farm(name="Tool Fixture Farm", province="Dong Nai")

    unit = ManagementUnit(
        farm=farm,
        name="Block T1",
        area_m2=20_000,
    )

    db_session.add(farm)
    db_session.flush()

    cycle = CropCycle(
        management_unit_id=unit.id,
        crop="durian",
        cultivar="Ri6",
        tree_count=100,
    )

    db_session.add(cycle)
    db_session.flush()

    event = Event(
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        recorded_at=dt(10),
        source="farm_record",
        payload={
            "product_name": "NPK Fixture",
            "amount": amount,
            "amount_unit": amount_unit,
            "basis": basis,
            "n_pct": 20.0,
            "p2o5_pct": 10.0,
            "k2o_pct": 5.0,
        },
    )

    db_session.add(event)
    db_session.flush()

    context = build_decision_context(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

    return context, event

# -------------------------------------------------------------------
# 1. Derived nutrient state must preserve recorded nutrient analysis.
# -------------------------------------------------------------------
def test_context_preserves_fertilizer_analysis(db_session):
    context, _ = make_context(db_session)

    application = (
        context.nutrient_state.last_application
    )

    assert application.n_pct == 20.0
    assert application.p2o5_pct == 10.0
    assert application.k2o_pct == 5.0

# -------------------------------------------------------------------
# 2. Successful tool execution should produce deterministic facts.
# -------------------------------------------------------------------
def test_tool_execution_produces_calculated_facts(db_session):
    context, _ = make_context(db_session)
    packet = execute_nutrient_context_tools(context)

    assert len(packet.executions) == 1

    execution = packet.executions[0]

    assert execution.status == ToolExecutionStatus.SUCCESS

    facts = {
        fact.name: fact
        for fact in packet.calculated_facts
    }

    assert facts["product_kg_total"].value == pytest.approx(200.0)
    assert facts["n_kg_total"].value == pytest.approx(40.0)
    assert facts["p2o5_kg_total"].value == pytest.approx(20.0)
    assert facts["k2o_kg_total"].value == pytest.approx(10.0)

# -------------------------------------------------------------------
# 3. Calculated facts must retain their source farm event.
# -------------------------------------------------------------------
def test_calculated_facts_preserve_event_provenance(db_session):
    context, event = make_context(db_session)

    packet = execute_nutrient_context_tools(context)

    assert packet.executions[0].source_event_ids == [event.id]

    for fact in packet.calculated_facts:
        assert fact.source_event_ids == [event.id]

# -------------------------------------------------------------------
# 4. Tool records should preserve both raw inputs and outputs.
# -------------------------------------------------------------------
def test_tool_execution_is_auditable(db_session):
    context, _ = make_context(db_session)
    packet = execute_nutrient_context_tools(context)

    execution = packet.executions[0]

    assert execution.inputs["amount"] == 2.0
    assert execution.inputs["basis"] == "per_tree"
    assert execution.inputs["tree_count"] == 100
    assert execution.outputs["product_kg_total"] == pytest.approx(200.0)

# -------------------------------------------------------------------
# 5. Unsupported liquid conversion should be recorded as blocked.
# -------------------------------------------------------------------
def test_liquid_tool_execution_is_blocked_without_density(db_session):
    context, _ = make_context(db_session, amount=10.0, amount_unit="L", basis="total")

    packet = execute_nutrient_context_tools(context)

    assert len(packet.executions) == 1

    execution = packet.executions[0]

    assert execution.status == ToolExecutionStatus.BLOCKED
    assert "density" in execution.message.lower()
    assert execution.outputs == {}
    assert packet.calculated_facts == []