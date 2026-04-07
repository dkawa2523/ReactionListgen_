from plasma_reaction_builder.runtime import build_runtime


def test_runtime_promotes_source_backed_templates_for_bromine_family():
    runtime = build_runtime(
        "examples/production_blueprint/config_bromine_family_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    catalog_equations = {template.equation(): template.family for template in runtime.catalog.templates}
    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "Br2+ + HBr -> HBr+ + Br2" in catalog_equations
    assert catalog_equations["Br2+ + HBr -> HBr+ + Br2"] == "ion_neutral_followup"
    assert "Br + HBr -> Br2 + H" in catalog_equations
    assert catalog_equations["Br + HBr -> Br2 + H"] == "radical_neutral_reaction"

    result = runtime.build_network_builder().build()
    reaction_equations = {reaction.equation for reaction in result.reactions}

    assert "Br2+ + HBr -> HBr+ + Br2" in reaction_equations
    assert "Br + HBr -> Br2 + H" in reaction_equations


def test_runtime_promotes_source_backed_templates_for_silicon_family():
    runtime = build_runtime(
        "examples/production_blueprint/config_silicon_family_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    catalog_equations = {template.equation(): template.family for template in runtime.catalog.templates}
    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "e- + SiH4+ -> SiH2 + H2" in catalog_equations
    assert catalog_equations["e- + SiH4+ -> SiH2 + H2"] == "dissociative_recombination"
    assert "SiH4+ + H2 -> SiH4 + H2+" in catalog_equations
    assert catalog_equations["SiH4+ + H2 -> SiH4 + H2+"] == "ion_neutral_followup"

    result = runtime.build_network_builder().build()
    reaction_equations = {reaction.equation for reaction in result.reactions}

    assert "e- + SiH4+ -> SiH2 + H2" in reaction_equations
    assert "e- + SiH2Cl2+ -> SiCl2 + H2" in reaction_equations
    assert "SiH4+ + H2 -> SiH4 + H2+" in reaction_equations


def test_runtime_promotes_source_backed_templates_for_process_and_precursor_families():
    runtime = build_runtime(
        "examples/production_blueprint/config_process_precursor_template_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    catalog_equations = {template.equation(): template.family for template in runtime.catalog.templates}
    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "e- + SF6 -> e- + SF4 + F + F" in catalog_equations
    assert catalog_equations["e- + SF6 -> e- + SF4 + F + F"] == "electron_dissociation"
    assert "SF6+ + O2 -> SF4 + F + F + O2+" in catalog_equations
    assert catalog_equations["SF6+ + O2 -> SF4 + F + F + O2+"] == "ion_neutral_followup"
    assert "e- + SF6+ -> SF4 + F + F" in catalog_equations
    assert catalog_equations["e- + SF6+ -> SF4 + F + F"] == "dissociative_recombination"
    assert "e- + NF3 -> e- + N + F + F + F" in catalog_equations
    assert catalog_equations["e- + NF3 -> e- + N + F + F + F"] == "electron_dissociation"
    assert "NF3+ + O2 -> N + F + F + F + O2+" in catalog_equations
    assert catalog_equations["NF3+ + O2 -> N + F + F + F + O2+"] == "ion_neutral_followup"
    assert "e- + NF3+ -> N + F + F + F" in catalog_equations
    assert catalog_equations["e- + NF3+ -> N + F + F + F"] == "dissociative_recombination"
    assert "e- + WF6 -> e- + WF4 + F + F" in catalog_equations
    assert catalog_equations["e- + WF6 -> e- + WF4 + F + F"] == "electron_dissociation"
    assert "WF6+ + H2 -> WF4 + F + F + H2+" in catalog_equations
    assert catalog_equations["WF6+ + H2 -> WF4 + F + F + H2+"] == "ion_neutral_followup"
    assert "e- + WF6+ -> WF4 + F + F" in catalog_equations
    assert catalog_equations["e- + WF6+ -> WF4 + F + F"] == "dissociative_recombination"
    assert "e- + BCl3 -> e- + B + Cl + Cl2" in catalog_equations
    assert catalog_equations["e- + BCl3 -> e- + B + Cl + Cl2"] == "electron_dissociation"
    assert "BCl3+ + O2 -> B + Cl + Cl2 + O2+" in catalog_equations
    assert catalog_equations["BCl3+ + O2 -> B + Cl + Cl2 + O2+"] == "ion_neutral_followup"
    assert "e- + BCl3+ -> B + Cl + Cl2" in catalog_equations
    assert catalog_equations["e- + BCl3+ -> B + Cl + Cl2"] == "dissociative_recombination"
    assert "e- + SiH2Cl2 -> e- + SiH + H + Cl2" in catalog_equations
    assert catalog_equations["e- + SiH2Cl2 -> e- + SiH + H + Cl2"] == "electron_dissociation"
    assert "SiH2Cl2+ + H2 -> SiH + H + Cl2 + H2+" in catalog_equations
    assert catalog_equations["SiH2Cl2+ + H2 -> SiH + H + Cl2 + H2+"] == "ion_neutral_followup"
    assert "e- + SiH2Cl2+ -> SiH + H + Cl2" in catalog_equations
    assert catalog_equations["e- + SiH2Cl2+ -> SiH + H + Cl2"] == "dissociative_recombination"
    assert "e- + SiHCl3 -> e- + Si + HCl + Cl2" in catalog_equations
    assert catalog_equations["e- + SiHCl3 -> e- + Si + HCl + Cl2"] == "electron_dissociation"
    assert "SiHCl3+ + H2 -> Si + HCl + Cl2 + H2+" in catalog_equations
    assert catalog_equations["SiHCl3+ + H2 -> Si + HCl + Cl2 + H2+"] == "ion_neutral_followup"
    assert "e- + SiHCl3+ -> Si + HCl + Cl2" in catalog_equations
    assert catalog_equations["e- + SiHCl3+ -> Si + HCl + Cl2"] == "dissociative_recombination"
    assert "C8H20O4Si+ + H2 -> C6H15O3Si + C2H5O + H2+" in catalog_equations
    assert catalog_equations["C8H20O4Si+ + H2 -> C6H15O3Si + C2H5O + H2+"] == "ion_neutral_followup"

    result = runtime.build_network_builder().build()
    reaction_equations = {reaction.equation for reaction in result.reactions}

    assert "e- + SF6 -> e- + SF4 + F + F" in reaction_equations
    assert "SF6+ + O2 -> SF4 + F + F + O2+" in reaction_equations
    assert "e- + SF6+ -> SF4 + F + F" in reaction_equations
    assert "e- + NF3 -> e- + N + F + F + F" in reaction_equations
    assert "NF3+ + O2 -> N + F + F + F + O2+" in reaction_equations
    assert "e- + NF3+ -> N + F + F + F" in reaction_equations
    assert "e- + WF6 -> e- + WF4 + F + F" in reaction_equations
    assert "WF6+ + H2 -> WF4 + F + F + H2+" in reaction_equations
    assert "e- + WF6+ -> WF4 + F + F" in reaction_equations
    assert "e- + BCl3 -> e- + B + Cl + Cl2" in reaction_equations
    assert "BCl3+ + O2 -> B + Cl + Cl2 + O2+" in reaction_equations
    assert "e- + BCl3+ -> B + Cl + Cl2" in reaction_equations
    assert "e- + SiH2Cl2 -> e- + SiH + H + Cl2" in reaction_equations
    assert "SiH2Cl2+ + H2 -> SiH + H + Cl2 + H2+" in reaction_equations
    assert "e- + SiH2Cl2+ -> SiH + H + Cl2" in reaction_equations
    assert "e- + SiHCl3 -> e- + Si + HCl + Cl2" in reaction_equations
    assert "SiHCl3+ + H2 -> Si + HCl + Cl2 + H2+" in reaction_equations
    assert "e- + SiHCl3+ -> Si + HCl + Cl2" in reaction_equations
    assert "C8H20O4Si+ + H2 -> C6H15O3Si + C2H5O + H2+" in reaction_equations
