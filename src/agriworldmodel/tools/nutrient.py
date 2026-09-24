from typing import Literal

from pydantic import BaseModel

from agriworldmodel.decisions.schemas import DecisionContext

class NutrientCalculationError(ValueError):
    pass

class FertilizerCalculationResult(BaseModel):
    product_kg_total: float
    product_kg_per_tree: float | None
    product_kg_per_ha: float | None
    n_kg_total: float | None
    p2o5_kg_total: float | None
    k2o_kg_total: float | None

def _mass_to_kg(
    *, amount: float, amount_unit: str,
) -> float:
    if amount <= 0:
        raise NutrientCalculationError("Fertilizer amount must be positive.")

    if amount_unit == "kg":
        return amount
    if amount_unit == "g":
        return amount / 1000.0

    if amount_unit in {"L", "mL"}:
        raise NutrientCalculationError(
            "Liquid fertilizer cannot be converted to mass without product density."
        )

    raise NutrientCalculationError(f"Unsupported fertilizer unit: {amount_unit}")

def _validate_percent(value: float | None, *, name: str) -> None:
    if value is None:
        return
    if value < 0 or value > 100:
        raise NutrientCalculationError(f"{name} must be between 0 and 100.")

def calculate_fertilizer_application(
    *, amount: float, amount_unit: Literal["kg", "g", "L", "mL"],
    basis: Literal["total", "per_tree", "per_ha"],
    area_m2: float | None = None,
    tree_count: int | None = None,
    n_pct: float | None = None, p2o5_pct: float | None = None, k2o_pct: float | None = None,
) -> FertilizerCalculationResult:
    """
    Normalize one fertilizer application to deterministic
    mass-based quantities.

    V1 supports kg/g fertilizer amounts only.

    Liquid amounts require product density and are therefore
    deliberately rejected rather than approximated.
    """
    for value, name in [
        (n_pct, "n_pct"),
        (p2o5_pct, "p2o5_pct"),
        (k2o_pct, "k2o_pct"),
    ]:
        _validate_percent(value, name=name)

    amount_kg = _mass_to_kg(amount=amount, amount_unit=amount_unit)

    if tree_count is not None and tree_count <= 0:
        raise NutrientCalculationError("tree_count must be positive.")
    if area_m2 is not None and area_m2 <= 0:
        raise NutrientCalculationError("area_m2 must be positive.")

    if basis == "total":
        total_kg = amount_kg
    elif basis == "per_tree":
        if tree_count is None:
            raise NutrientCalculationError("tree_count is required for per_tree basis.")
        total_kg = amount_kg * tree_count
    elif basis == "per_ha":
        if area_m2 is None:
            raise NutrientCalculationError("area_m2 is required for per_ha basis.")
        area_ha = area_m2 / 10_000.0
        total_kg = amount_kg * area_ha
    else:
        raise NutrientCalculationError(f"Unsupported fertilizer basis: {basis}")

    product_kg_per_tree = None

    if tree_count is not None:
        product_kg_per_tree = total_kg / tree_count

    product_kg_per_ha = None

    if area_m2 is not None:
        area_ha = area_m2 / 10_000.0
        product_kg_per_ha = total_kg / area_ha

    def nutrient_mass(pct: float | None) -> float | None:
        if pct is None:
            return None
        return total_kg * pct / 100.0

    return FertilizerCalculationResult(
        product_kg_total=total_kg,
        product_kg_per_tree=product_kg_per_tree,
        product_kg_per_ha=product_kg_per_ha,

        n_kg_total=nutrient_mass(n_pct),
        p2o5_kg_total=nutrient_mass(p2o5_pct),
        k2o_kg_total=nutrient_mass(k2o_pct),
    )

def calculate_fertilizer_for_context(
    context: DecisionContext,
    *, amount: float, amount_unit: Literal["kg", "g", "L", "mL"],
    basis: Literal["total", "per_tree", "per_ha"],
    n_pct: float | None = None, p2o5_pct: float | None = None, k2o_pct: float | None = None,
) -> FertilizerCalculationResult:
    """
    Run the deterministic fertilizer calculator using
    physical farm facts already present in DecisionContext.
    """

    return calculate_fertilizer_application(
        amount=amount,
        amount_unit=amount_unit,
        basis=basis,
        area_m2=context.area_m2,
        tree_count=context.tree_count,
        n_pct=n_pct,
        p2o5_pct=p2o5_pct,
        k2o_pct=k2o_pct,
    )