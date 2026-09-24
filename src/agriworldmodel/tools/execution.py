from agriworldmodel.decisions.schemas import DecisionContext, DecisionType
from agriworldmodel.tools.nutrient import NutrientCalculationError, calculate_fertilizer_for_context
from agriworldmodel.tools.schemas import (
    CalculatedFact,
    ToolExecutionPacket, ToolExecutionRecord, ToolExecutionStatus,
)

NUTRIENT_TOOL_NAME = "fertilizer_application_normalizer"
NUTRIENT_TOOL_VERSION = "1.0"

class ToolExecutionError(ValueError):
    pass

def execute_nutrient_context_tools(context: DecisionContext) -> ToolExecutionPacket:
    """
    Execute deterministic N1 calculations from the current
    farm context.

    No LLM reasoning occurs here.
    """
    if context.decision_type != DecisionType.NUTRIENT:
        raise ToolExecutionError("Nutrient tools require an N1 decision context.")

    if context.nutrient_state is None:
        raise ToolExecutionError("N1 context has no nutrient state.")

    application = context.nutrient_state.last_application

    # No previous application means there is simply
    # nothing to normalize.
    if application is None:
        return ToolExecutionPacket(executions=[], calculated_facts=[])

    source_event_ids = [application.event_id]

    inputs = {
        "amount": application.amount,
        "amount_unit": application.amount_unit,
        "basis": application.basis,

        "area_m2": context.area_m2,
        "tree_count": context.tree_count,

        "n_pct": application.n_pct,
        "p2o5_pct": application.p2o5_pct,
        "k2o_pct": application.k2o_pct,
    }

    try:
        result = calculate_fertilizer_for_context(
            context,
            amount=application.amount,
            amount_unit=application.amount_unit,
            basis=application.basis,
            n_pct=application.n_pct,
            p2o5_pct=application.p2o5_pct,
            k2o_pct=application.k2o_pct,
        )

    except NutrientCalculationError as exc:
        return ToolExecutionPacket(
            executions=[
                ToolExecutionRecord(
                    tool_name=NUTRIENT_TOOL_NAME,
                    tool_version=NUTRIENT_TOOL_VERSION,
                    status=ToolExecutionStatus.BLOCKED,
                    inputs=inputs, outputs={},
                    source_event_ids=source_event_ids,
                    message=str(exc),
                )
            ],
            calculated_facts=[],
        )

    outputs = result.model_dump()

    execution = ToolExecutionRecord(
        tool_name=NUTRIENT_TOOL_NAME,
        tool_version=NUTRIENT_TOOL_VERSION,
        status=ToolExecutionStatus.SUCCESS,
        inputs=inputs, outputs=outputs,
        source_event_ids=source_event_ids,
    )

    facts: list[CalculatedFact] = []

    fact_units = {
        "product_kg_total": "kg",
        "product_kg_per_tree": "kg/tree",
        "product_kg_per_ha": "kg/ha",
        "n_kg_total": "kg N",
        "p2o5_kg_total": "kg P2O5",
        "k2o_kg_total": "kg K2O",
    }

    for name, unit in fact_units.items():
        value = outputs[name]

        if value is None:
            continue

        facts.append(
            CalculatedFact(
                name=name, value=float(value), unit=unit,
                source_tool=NUTRIENT_TOOL_NAME,
                source_event_ids=source_event_ids,
            )
        )

    return ToolExecutionPacket(
        executions=[execution],
        calculated_facts=facts,
    )