from plasma_reaction_builder.runtime import build_runtime


def test_runtime_generates_templates_from_promoted_excited_states():
    runtime = build_runtime(
        "examples/production_blueprint/config_state_promotion_template_runtime.yaml",
        include_evidence_indexes=False,
    )

    catalog_equations = {template.equation(): template.family for template in runtime.catalog.templates}

    assert "state_promotion:molecular_excited_states" in runtime.catalog.loaded_resources
    assert "template_promotion:molecular_excited_state_templates" in runtime.catalog.loaded_resources
    assert "e- + CH4 -> e- + CH4(V14)" in catalog_equations
    assert catalog_equations["e- + CH4 -> e- + CH4(V14)"] == "electron_excitation_vibrational"
    assert "e- + O2 -> e- + O2(c1Sigma_u_minus)" in catalog_equations
    assert catalog_equations["e- + O2 -> e- + O2(c1Sigma_u_minus)"] == "electron_excitation"
    assert "e- + N2 -> e- + N2(B3Pi_g)" in catalog_equations
    assert catalog_equations["e- + N2 -> e- + N2(B3Pi_g)"] == "electron_excitation"
    assert "CH4(V14) -> CH4" in catalog_equations
    assert catalog_equations["CH4(V14) -> CH4"] == "radiative_relaxation"
    assert "CH4(V14) + CH4 -> CH4 + CH4" in catalog_equations
    assert catalog_equations["CH4(V14) + CH4 -> CH4 + CH4"] == "collisional_quenching"
    assert "e- + CH4(V14) -> e- + CH4" in catalog_equations
    assert catalog_equations["e- + CH4(V14) -> e- + CH4"] == "superelastic_deexcitation"
    assert "O2(c1Sigma_u_minus) + N2 -> O2 + N2" in catalog_equations
    assert catalog_equations["O2(c1Sigma_u_minus) + N2 -> O2 + N2"] == "collisional_quenching"
    assert "e- + N2(B3Pi_g) -> e- + N2" in catalog_equations
    assert catalog_equations["e- + N2(B3Pi_g) -> e- + N2"] == "superelastic_deexcitation"

    result = runtime.build_network_builder().build()
    reaction_equations = {reaction.equation for reaction in result.reactions}

    assert "e- + CH4 -> e- + CH4(V14)" in reaction_equations
    assert "e- + O2 -> e- + O2(c1Sigma_u_minus)" in reaction_equations
    assert "e- + N2 -> e- + N2(B3Pi_g)" in reaction_equations
    assert "CH4(V14) -> CH4" in reaction_equations
    assert "CH4(V14) + CH4 -> CH4 + CH4" in reaction_equations
    assert "e- + CH4(V14) -> e- + CH4" in reaction_equations


def test_runtime_promotes_source_backed_templates_across_multiple_families():
    runtime = build_runtime(
        "examples/production_blueprint/config_multi_family_template_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    catalog_equations = {template.equation(): template.family for template in runtime.catalog.templates}

    assert "state_promotion:molecular_excited_states" in runtime.catalog.loaded_resources
    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "e- + CH4 -> e- + CH4[V14]" in catalog_equations
    assert catalog_equations["e- + CH4 -> e- + CH4[V14]"] == "electron_excitation_vibrational"
    assert "e- + O2 -> e- + O2[c1Sigma_u_minus]" in catalog_equations
    assert catalog_equations["e- + O2 -> e- + O2[c1Sigma_u_minus]"] == "electron_excitation"
    assert "e- + N2 -> e- + N2[B3Pi_g]" in catalog_equations
    assert catalog_equations["e- + N2 -> e- + N2[B3Pi_g]"] == "electron_excitation"

    result = runtime.build_network_builder().build()
    reaction_equations = {reaction.equation for reaction in result.reactions}

    assert "e- + CH4 -> e- + CH4[V14]" in reaction_equations
    assert "e- + O2 -> e- + O2[c1Sigma_u_minus]" in reaction_equations
    assert "e- + N2 -> e- + N2[B3Pi_g]" in reaction_equations


def test_runtime_promotes_source_backed_templates_for_halogen_and_fluorocarbon_families():
    runtime = build_runtime(
        "examples/production_blueprint/config_halogen_fluorocarbon_template_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    catalog_equations = {template.equation(): template.family for template in runtime.catalog.templates}

    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "e- + c-C4F8 -> c-C4F8-" in catalog_equations
    assert catalog_equations["e- + c-C4F8 -> c-C4F8-"] == "electron_attachment"
    assert "e- + CF4 -> e- + CF3 + F" in catalog_equations
    assert catalog_equations["e- + CF4 -> e- + CF3 + F"] == "electron_dissociation"
    assert "e- + HCl -> e- + H + Cl" in catalog_equations
    assert catalog_equations["e- + HCl -> e- + H + Cl"] == "electron_dissociation"
    assert "Cl + HCl -> Cl2 + H" in catalog_equations
    assert catalog_equations["Cl + HCl -> Cl2 + H"] == "radical_neutral_reaction"
    assert "e- + HBr -> e- + H + Br" in catalog_equations
    assert catalog_equations["e- + HBr -> e- + H + Br"] == "electron_dissociation"
    assert "Br + HBr -> Br2 + H" in catalog_equations
    assert catalog_equations["Br + HBr -> Br2 + H"] == "radical_neutral_reaction"

    result = runtime.build_network_builder().build()
    reaction_equations = {reaction.equation for reaction in result.reactions}

    assert "e- + c-C4F8 -> c-C4F8-" in reaction_equations
    assert "e- + CF4 -> e- + CF3 + F" in reaction_equations
    assert "e- + HCl -> e- + H + Cl" in reaction_equations
    assert "Cl + HCl -> Cl2 + H" in reaction_equations
    assert "e- + HBr -> e- + H + Br" in reaction_equations
    assert "Br + HBr -> Br2 + H" in reaction_equations


def test_runtime_couples_excited_state_promotion_and_source_backed_followups_for_precursors():
    runtime = build_runtime(
        "examples/production_blueprint/config_excited_precursor_template_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    catalog_equations = {template.equation(): template.family for template in runtime.catalog.templates}

    assert "state_promotion:molecular_excited_states" in runtime.catalog.loaded_resources
    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "template_promotion:molecular_excited_state_templates" in runtime.catalog.loaded_resources
    assert "e- + BCl3 -> e- + BCl3(A1)" in catalog_equations
    assert catalog_equations["e- + BCl3 -> e- + BCl3(A1)"] == "electron_excitation"
    assert "BCl3(A1) + O2 -> BCl3 + O2" in catalog_equations
    assert catalog_equations["BCl3(A1) + O2 -> BCl3 + O2"] == "collisional_quenching"
    assert "e- + BCl3(A1) -> e- + BCl3" in catalog_equations
    assert catalog_equations["e- + BCl3(A1) -> e- + BCl3"] == "superelastic_deexcitation"
    assert "BCl3[A1] + O2 -> BCl2 + Cl + O2" in catalog_equations
    assert catalog_equations["BCl3[A1] + O2 -> BCl2 + Cl + O2"] == "radical_neutral_reaction"
    assert "SiH2Cl2[A1] + H2 -> SiHCl2 + H + H2" in catalog_equations
    assert catalog_equations["SiH2Cl2[A1] + H2 -> SiHCl2 + H + H2"] == "radical_neutral_reaction"
    assert "SiHCl3[B1] + H2 -> SiCl2 + HCl + H2" in catalog_equations
    assert catalog_equations["SiHCl3[B1] + H2 -> SiCl2 + HCl + H2"] == "radical_neutral_reaction"
    assert "C8H20O4Si[Ryd1] + O2 -> C6H15O3Si + C2H5O + O2" in catalog_equations
    assert catalog_equations["C8H20O4Si[Ryd1] + O2 -> C6H15O3Si + C2H5O + O2"] == "radical_neutral_reaction"

    result = runtime.build_network_builder().build()
    reaction_equations = {reaction.equation for reaction in result.reactions}

    assert "e- + BCl3 -> e- + BCl3(A1)" in reaction_equations
    assert "BCl3(A1) + O2 -> BCl3 + O2" in reaction_equations
    assert "e- + BCl3(A1) -> e- + BCl3" in reaction_equations
    assert "BCl3[A1] + O2 -> BCl2 + Cl + O2" in reaction_equations
    assert "SiH2Cl2[A1] + H2 -> SiHCl2 + H + H2" in reaction_equations
    assert "SiHCl3[B1] + H2 -> SiCl2 + HCl + H2" in reaction_equations
    assert "C8H20O4Si[Ryd1] + O2 -> C6H15O3Si + C2H5O + O2" in reaction_equations


def test_runtime_couples_excited_state_promotion_and_source_backed_followups_for_fluoride_precursors():
    runtime = build_runtime(
        "examples/production_blueprint/config_excited_fluoride_precursor_template_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    catalog_equations = {template.equation(): template.family for template in runtime.catalog.templates}

    assert "state_promotion:molecular_excited_states" in runtime.catalog.loaded_resources
    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "template_promotion:molecular_excited_state_templates" in runtime.catalog.loaded_resources
    assert "e- + SF6 -> e- + SF6(A1)" in catalog_equations
    assert catalog_equations["e- + SF6 -> e- + SF6(A1)"] == "electron_excitation"
    assert "SF6(A1) + O2 -> SF6 + O2" in catalog_equations
    assert catalog_equations["SF6(A1) + O2 -> SF6 + O2"] == "collisional_quenching"
    assert "e- + SF6(A1) -> e- + SF6" in catalog_equations
    assert catalog_equations["e- + SF6(A1) -> e- + SF6"] == "superelastic_deexcitation"
    assert "SF6[A1] + O2 -> SF5 + F + O2" in catalog_equations
    assert catalog_equations["SF6[A1] + O2 -> SF5 + F + O2"] == "radical_neutral_reaction"
    assert "e- + NF3 -> e- + NF3(A1)" in catalog_equations
    assert catalog_equations["e- + NF3 -> e- + NF3(A1)"] == "electron_excitation"
    assert "NF3(A1) + O2 -> NF3 + O2" in catalog_equations
    assert catalog_equations["NF3(A1) + O2 -> NF3 + O2"] == "collisional_quenching"
    assert "NF3[A1] + O2 -> NF2 + F + O2" in catalog_equations
    assert catalog_equations["NF3[A1] + O2 -> NF2 + F + O2"] == "radical_neutral_reaction"
    assert "e- + WF6 -> e- + WF6(B1)" in catalog_equations
    assert catalog_equations["e- + WF6 -> e- + WF6(B1)"] == "electron_excitation"
    assert "WF6(B1) + H2 -> WF6 + H2" in catalog_equations
    assert catalog_equations["WF6(B1) + H2 -> WF6 + H2"] == "collisional_quenching"
    assert "WF6[B1] + H2 -> WF5 + F + H2" in catalog_equations
    assert catalog_equations["WF6[B1] + H2 -> WF5 + F + H2"] == "radical_neutral_reaction"

    result = runtime.build_network_builder().build()
    reaction_equations = {reaction.equation for reaction in result.reactions}

    assert "e- + SF6 -> e- + SF6(A1)" in reaction_equations
    assert "SF6(A1) + O2 -> SF6 + O2" in reaction_equations
    assert "e- + SF6(A1) -> e- + SF6" in reaction_equations
    assert "SF6[A1] + O2 -> SF5 + F + O2" in reaction_equations
    assert "e- + NF3 -> e- + NF3(A1)" in reaction_equations
    assert "NF3(A1) + O2 -> NF3 + O2" in reaction_equations
    assert "NF3[A1] + O2 -> NF2 + F + O2" in reaction_equations
    assert "e- + WF6 -> e- + WF6(B1)" in reaction_equations
    assert "WF6(B1) + H2 -> WF6 + H2" in reaction_equations
    assert "WF6[B1] + H2 -> WF5 + F + H2" in reaction_equations
