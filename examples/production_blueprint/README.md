# Production Blueprint

This directory contains production-design blueprints.

- `state_master_base.yaml` is a design-only file.
- `state_master_base.yaml` can now carry curated `excited_states` and source-backed `atomic_asd` expansion rules.
- `catalog_*.yaml` files are runtime-compatible examples that show the intended split.
- `config_state_master_runtime.yaml` shows how to wire `state_masters` into the normal build flow.
- `config_state_promotion_runtime.yaml` shows how to promote molecular excited states from external evidence.
- `config_state_promotion_template_runtime.yaml` adds automatic template generation for promoted molecular excited states.
- `config_gas_phase_target_runtime.yaml` materializes the broader semiconductor gas-phase feedstock set.
- `config_gas_phase_target_db_first_runtime.yaml` runs the broader semiconductor gas-phase target set in a DB-first, curated-minimal mode.
- `config_process_gas_secondary_runtime.yaml` focuses on secondary gas-phase chemistry for SF6, NF3, BCl3, NH3, N2O, and O3.
- `config_advanced_precursor_runtime.yaml` focuses on WF6, TEOS, and silicon-halide precursor chemistry.
- `config_etch_common_support_runtime.yaml` is the user-facing preset for Ar, He, N2, H2, and O2 support-gas chemistry.
- `config_etch_fluorocarbon_runtime.yaml` is the user-facing preset for CF4, CHF3, CH2F2, CH3F, C2F6, c-C4F8, and C5F8 fluorocarbon chemistry.
- `config_etch_inorganic_fluoride_runtime.yaml` is the user-facing preset for SF6 / NF3 gas-phase etch chemistry with DB-backed excited-state expansion.
- `config_etch_halogen_runtime.yaml` is the user-facing preset for Cl2, HCl, Br2, HBr, and BCl3 halogen chemistry.
- `config_deposition_silane_gas_phase_runtime.yaml` is the user-facing preset for SiH4, SiH2Cl2, and SiHCl3 gas-phase precursor chemistry.
- `config_deposition_reactant_gas_phase_runtime.yaml` is the user-facing preset for NH3, N2O, O3, H2, and O2 deposition-reactant chemistry.
- `config_chlorine_family_runtime.yaml` is a minimal family-scoped example for chlorine chemistry.
- `config_bromine_family_runtime.yaml` is the bromine family example in promotion-first mode with curated fallback catalogs.
- `config_silicon_family_runtime.yaml` is the silicon precursor example in promotion-first mode with curated fallback catalogs.
- `config_cf4_electron_argon_ion_runtime.yaml` is the focused CF4 example for `e-` and `Ar+`.
- `config_chf3_electron_argon_ion_runtime.yaml` is the focused CHF3 example for `e-` and `Ar+`.
- `config_bromine_family_promotion_runtime.yaml` is a compatibility alias that resolves to the bromine runtime above.
- `config_silicon_family_promotion_runtime.yaml` is a compatibility alias that resolves to the silicon runtime above.
- `config_multi_family_template_promotion_runtime.yaml` shows source-backed template promotion generalized across hydrocarbon, oxygen, and nitrogen families.
- `config_halogen_fluorocarbon_template_promotion_runtime.yaml` extends source-backed template promotion coverage across fluorocarbon, chlorine, and bromine families.
- `config_process_precursor_template_promotion_runtime.yaml` connects source-backed promotion to SF6, NF3, BCl3, SiH2Cl2, SiHCl3, WF6, and TEOS process/precursor packs.
- `config_excited_precursor_template_promotion_runtime.yaml` couples precursor excited-state promotion, auto-generated excited-state templates, and source-backed excited follow-up channels.
- `config_excited_fluoride_precursor_template_promotion_runtime.yaml` does the same for the fluoride precursor set built around SF6, NF3, and WF6.
- `config_o2_electron_argon_ion_runtime.yaml` is a focused O2 example for electron-impact channels plus `Ar+` charge transfer.
- `catalog_66_reactions_followup_oxygen_argon.yaml` extends the focused O2 example with representative `O`, `O2+`, `O-`, and `O2-` follow-up reactions.
- `excited_state_registry.yaml` normalizes database-specific excited-state labels onto canonical keys.
- `config_focused_runtime_base.yaml` centralizes the shared focused-runtime defaults and is intended to be loaded via `extends`.
- These files are scaffolding examples and are not wired into `examples/config.yaml`.

The runtime config loader now supports `extends`, so focused configs can share one base policy while keeping family-specific feeds, catalogs, and limits small.

`catalog_policy.reaction_conflict_policy: prefer_higher_priority` is the DB-first fallback switch used by these focused examples. It keeps curated packs available, but lets higher-priority promoted templates replace same-equation curated templates when both exist.

The user-facing presets in this directory now default to `max_generation: 3`, so generated outputs include second- and third-generation gas-phase follow-up reactions when compatible templates exist.

Suggested loading policy:

1. keep design master in `state_master_base.yaml`
2. materialize explicit species into `catalog_10_*`
3. materialize curated reaction templates into `catalog_20_*`, `catalog_30_*`, `catalog_40_*`
4. keep project-specific changes in `catalog_90_*`

Included reaction-family examples in this blueprint:

- hydrocarbon: `electron_attachment`, `electron_ionization`, `electron_excitation_vibrational`, `electron_dissociation`
- fluorocarbon: `electron_attachment`, `electron_dissociative_ionization`, `ion_neutral_followup`, `neutral_fragmentation`, `radical_fragmentation`
- oxygen: `electron_attachment`, `electron_excitation`, `electron_ionization`, `electron_dissociation`
- nitrogen: `electron_excitation`, `electron_ionization`, `electron_dissociation`
- noble_gas: `electron_excitation`, `electron_ionization`, `charge_transfer`
- bromine: `electron_attachment`, `electron_ionization`, `electron_dissociation`, `radical_neutral_reaction`, `ion_neutral_followup`, `dissociative_recombination`
- silicon: `electron_ionization`, `electron_dissociation`, `radical_neutral_reaction`, `ion_neutral_followup`, `dissociative_recombination`
- process_gases: `electron_ionization`, `electron_attachment`, `electron_dissociation`, `ion_neutral_followup`, `dissociative_recombination`
- advanced_precursors: `electron_ionization`, `electron_dissociation`, `ion_neutral_followup`, `dissociative_recombination`

User-ready gas-group presets:

- `config_etch_common_support_runtime.yaml`: Ar / He / N2 / H2 / O2 with `e-` and `Ar+`
- `config_etch_fluorocarbon_runtime.yaml`: CF4 / CHF3 / CH2F2 / CH3F / C2F6 / c-C4F8 / C5F8 with `e-`
- `config_etch_inorganic_fluoride_runtime.yaml`: SF6 / NF3 with `e-`, O2 / H2 support gases, and DB-backed excited-state promotion
- `config_etch_halogen_runtime.yaml`: Cl2 / HCl / Br2 / HBr / BCl3 with `e-`, H2 / O2 support gases, and DB-backed template promotion
- `config_deposition_silane_gas_phase_runtime.yaml`: SiH4 / SiH2Cl2 / SiHCl3 with `e-` and DB-backed excited-state promotion
- `config_deposition_reactant_gas_phase_runtime.yaml`: NH3 / N2O / O3 / H2 / O2 with `e-` and DB-backed excited-state promotion

These presets are intended for list generation, not first-generation-only screening. By default they expand the network up to generation 3.

Materializing a runtime species catalog:

```powershell
py -3.13 -m uv run plasma-rxn-builder materialize-state-catalog `
  examples/production_blueprint/state_master_base.yaml `
  --output examples/production_blueprint/catalog_10_species_generated.yaml `
  --families core_plasma hydrocarbon `
  --charge-window-min 0 `
  --charge-window-max 1 `
  --asd-export-paths examples/snapshots/asd/C_I.csv examples/snapshots/asd/C_II.csv
```

Build-time charge filtering can also be driven from config:

```yaml
state_masters:
  - path: state_master_base.yaml
    families: [core_plasma, oxygen, nitrogen, hydrocarbon, fluorocarbon]

state_filters:
  charge_window_min: 0
  charge_window_max: 1
```

When `bootstrap.nist_asd` export paths are configured, `atomic_asd` entries are expanded automatically during the normal build/runtime catalog assembly.

Sample build using the expanded production blueprint:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_state_master_runtime.yaml `
  --output examples/production_blueprint/output_network.json
```

Sample runtime for molecular excited-state promotion:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_state_promotion_runtime.yaml `
  --output examples/production_blueprint/output_promoted_network.json
```

Sample runtime for auto-generated templates from promoted molecular excited states:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_state_promotion_template_runtime.yaml `
  --output examples/production_blueprint/output_promoted_template_network.json
```

This template-generation sample now includes `collisional_quenching` and `superelastic_deexcitation` in addition to excitation and radiative relaxation.

The promotion sample intentionally uses mixed spellings such as `O2(c1Sigma_u-)`, `O2(c^1Σ_u-)`, and `N2(B^3Π_g)`. `excited_state_registry.yaml` folds them into canonical keys such as `O2[c1Sigma_u_minus]` and `N2[B3Pi_g]`.

Sample runtime for the broader gas-phase target set:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_gas_phase_target_runtime.yaml `
  --output examples/production_blueprint/output_gas_phase_target_network.json
```

DB-first runtime for the broader gas-phase target set:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_gas_phase_target_db_first_runtime.yaml `
  --output examples/production_blueprint/output_gas_phase_target_db_first_network.json
```

This DB-first variant keeps curated reaction catalogs to a minimum and relies on `state_master`, normalized evidence snapshots, source-backed template promotion, and excited-state promotion instead.

`build` / `write-lock` now emit a `catalog_manifest` with template origins, source systems, and equation-conflict decisions, and the reaction CSV exports from `visualize` include the same origin columns for manual review.

If you want to inspect a focused config before building, use `audit-config`. It resolves `extends`, shows which fallback catalogs are still configured, and lists the source systems and snapshots that promotion will read.

```powershell
py -3.13 -m uv run plasma-rxn-builder audit-config `
  examples/production_blueprint/config_bromine_family_runtime.yaml `
  --output examples/production_blueprint/output_bromine_family_config_audit.json
```

`build` also embeds a `network_manifest` in the output JSON so automation can see which fallback catalogs, promoted templates, and evidence systems were actually used in the final network.

If you want to run the same `audit-config -> build -> audit-network` flow across the main focused runtimes, use:

```powershell
.\examples\production_blueprint\run_focused_runtime_audits.ps1
```

By default this writes config audits, built networks, and network audits into `examples/production_blueprint/.generated_runtime_audits`.

If you only want the compact provenance/fallback summary after a build, use:

```powershell
py -3.13 -m uv run plasma-rxn-builder audit-network `
  examples/production_blueprint/output_gas_phase_target_db_first_network.json `
  --output examples/production_blueprint/output_gas_phase_target_db_first_audit.json
```

Focused runtime for secondary process-gas chemistry:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_process_gas_secondary_runtime.yaml `
  --output examples/production_blueprint/output_process_gas_secondary_network.json
```

Focused runtime for WF6, TEOS, and silicon-halide precursor chemistry:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_advanced_precursor_runtime.yaml `
  --output examples/production_blueprint/output_advanced_precursor_network.json
```

Sample runtime for a single family playbook:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_chlorine_family_runtime.yaml `
  --output examples/production_blueprint/output_chlorine_family_network.json
```

Matching bromine-family runtime:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_bromine_family_runtime.yaml `
  --output examples/production_blueprint/output_bromine_family_network.json
```

Matching silicon-family runtime:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_silicon_family_runtime.yaml `
  --output examples/production_blueprint/output_silicon_family_network.json
```

Compatibility alias for the bromine-family runtime:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_bromine_family_promotion_runtime.yaml `
  --output examples/production_blueprint/output_bromine_family_promoted_network.json
```

Compatibility alias for the silicon-family runtime:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_silicon_family_promotion_runtime.yaml `
  --output examples/production_blueprint/output_silicon_family_promoted_network.json
```

Generalized multi-family source-backed template promotion runtime:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_multi_family_template_promotion_runtime.yaml `
  --output examples/production_blueprint/output_multi_family_promoted_network.json
```

Halogen and fluorocarbon source-backed template promotion runtime:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_halogen_fluorocarbon_template_promotion_runtime.yaml `
  --output examples/production_blueprint/output_halogen_fluorocarbon_promoted_network.json
```

Process-gas and precursor source-backed template promotion runtime:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_process_precursor_template_promotion_runtime.yaml `
  --output examples/production_blueprint/output_process_precursor_promoted_network.json
```

Excited-state-coupled precursor promotion runtime:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_excited_precursor_template_promotion_runtime.yaml `
  --output examples/production_blueprint/output_excited_precursor_promoted_network.json
```

Excited-state-coupled fluoride-precursor promotion runtime:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_excited_fluoride_precursor_template_promotion_runtime.yaml `
  --output examples/production_blueprint/output_excited_fluoride_precursor_promoted_network.json
```

Focused O2 runtime with `e-` and `Ar+` projectiles:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_o2_electron_argon_ion_runtime.yaml `
  --output examples/production_blueprint/output_o2_electron_argon_ion_network.json
```

This focused O2 runtime now includes representative follow-up channels for `O`, `O2+`, `O-`, and `O2-`, so `max_generation: 3` can reach oxygen-ion follow-up chemistry instead of stopping at only first-generation products.

Focused CF4 runtime with `e-` and `Ar+` projectiles:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_cf4_electron_argon_ion_runtime.yaml `
  --output runs/cf4_electron_argon_ion_case/network.json
```

Focused CHF3 runtime with `e-` and `Ar+` projectiles:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_chf3_electron_argon_ion_runtime.yaml `
  --output runs/chf3_electron_argon_ion_case/network.json
```

User-facing preset for support-gas chemistry:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_etch_common_support_runtime.yaml `
  --output examples/production_blueprint/output_etch_common_support_network.json
```

User-facing preset for fluorocarbon etch chemistry:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_etch_fluorocarbon_runtime.yaml `
  --output examples/production_blueprint/output_etch_fluorocarbon_network.json
```

User-facing preset for inorganic fluoride etch chemistry:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_etch_inorganic_fluoride_runtime.yaml `
  --output examples/production_blueprint/output_etch_inorganic_fluoride_network.json
```

User-facing preset for halogen etch chemistry:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_etch_halogen_runtime.yaml `
  --output examples/production_blueprint/output_etch_halogen_network.json
```

User-facing preset for silane-family deposition chemistry:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_deposition_silane_gas_phase_runtime.yaml `
  --output examples/production_blueprint/output_deposition_silane_network.json
```

User-facing preset for deposition-reactant chemistry:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_deposition_reactant_gas_phase_runtime.yaml `
  --output examples/production_blueprint/output_deposition_reactant_network.json
```
