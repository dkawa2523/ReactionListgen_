from plasma_reaction_builder.formula import parse_formula, parse_species_token, tracked_signature


def test_parse_formula():
    assert parse_formula("CH4") == {"C": 1, "H": 4}
    assert parse_formula("C2F4") == {"C": 2, "F": 4}


def test_parse_species_token():
    parsed = parse_species_token("CH4+")
    assert parsed.formula == "CH4"
    assert parsed.charge == 1
    assert parsed.state_class == "cation"


def test_tracked_signature_ignores_electron():
    lhs = tracked_signature(["e-", "CH4"])
    rhs = tracked_signature(["CH4"])
    assert lhs == rhs
