import pytest

from agriworldmodel.tools.nutrient import NutrientCalculationError, calculate_fertilizer_application

# -------------------------------------------------------------------
# 1. Mass units should normalize deterministically to kilograms.
# -------------------------------------------------------------------
def test_grams_are_normalized_to_kilograms():
    result = calculate_fertilizer_application(
        amount=2500,
        amount_unit="g",
        basis="total",
    )
    assert result.product_kg_total == pytest.approx(2.5)

# -------------------------------------------------------------------
# 2. Per-tree applications should convert to total farm quantity.
# -------------------------------------------------------------------
def test_per_tree_application_uses_tree_count():
    result = calculate_fertilizer_application(
        amount=2.0, amount_unit="kg",
        basis="per_tree", tree_count=100,
    )

    assert result.product_kg_total == pytest.approx(200.0)
    assert result.product_kg_per_tree == pytest.approx(2.0)

# -------------------------------------------------------------------
# 3. Per-hectare applications should use management-unit area.
# -------------------------------------------------------------------
def test_per_hectare_application_uses_area():
    result = calculate_fertilizer_application(
        amount=100.0, amount_unit="kg",
        basis="per_ha", area_m2=25_000,
    )

    assert result.product_kg_total == pytest.approx(250.0)
    assert result.product_kg_per_ha == pytest.approx(100.0)

# -------------------------------------------------------------------
# 4. Nutrient percentages should produce nutrient mass totals.
# -------------------------------------------------------------------
def test_nutrient_percentages_produce_mass_totals():
    result = calculate_fertilizer_application(
        amount=100.0, amount_unit="kg",
        basis="total",
        n_pct=20.0, p2o5_pct=10.0, k2o_pct=5.0,
    )

    assert result.n_kg_total == pytest.approx(20.0)
    assert result.p2o5_kg_total == pytest.approx(10.0)
    assert result.k2o_kg_total == pytest.approx(5.0)

# -------------------------------------------------------------------
# 5. Liquid fertilizer must not be treated as kilograms without density.
# -------------------------------------------------------------------
def test_liquid_mass_conversion_requires_density():
    with pytest.raises(NutrientCalculationError):
        calculate_fertilizer_application(
            amount=10.0,
            amount_unit="L",
            basis="total",
        )

# -------------------------------------------------------------------
# 6. Basis-specific physical data must be present.
# -------------------------------------------------------------------
def test_per_tree_requires_tree_count():
    with pytest.raises(NutrientCalculationError):
        calculate_fertilizer_application(
            amount=2.0,
            amount_unit="kg",
            basis="per_tree",
            tree_count=None,
        )