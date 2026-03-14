from ml.grid_strain.predict import _strain_level_from_probability


def test_strain_level_from_probability_bands() -> None:
    assert _strain_level_from_probability(0.01) == "low"
    assert _strain_level_from_probability(0.2499) == "low"
    assert _strain_level_from_probability(0.25) == "moderate"
    assert _strain_level_from_probability(0.54) == "moderate"
    assert _strain_level_from_probability(0.55) == "high"
