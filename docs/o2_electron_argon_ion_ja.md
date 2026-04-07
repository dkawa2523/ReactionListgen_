# O2 Gas with `e-` and `Ar+`

このケースは、`O2` を feed とし、projectile に `e-` と `Ar+` を与えたときの
状態種と反応式を、production blueprint の curated template から生成した一覧です。

対象 config:

- `examples/production_blueprint/config_o2_electron_argon_ion_runtime.yaml`

参照 template:

- `examples/production_blueprint/catalog_30_reactions_charge_transfer_noble_gas.yaml`
- `examples/production_blueprint/catalog_32_reactions_electron_attachment_oxygen.yaml`
- `examples/production_blueprint/catalog_33_reactions_electron_ionization_oxygen.yaml`
- `examples/production_blueprint/catalog_34_reactions_electron_dissociation_oxygen.yaml`
- `examples/production_blueprint/catalog_35_reactions_electron_excitation_oxygen.yaml`
- `examples/production_blueprint/catalog_66_reactions_followup_oxygen_argon.yaml`

実行コマンド:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_o2_electron_argon_ion_runtime.yaml `
  --output .tmp_o2_electron_argon_ion/network.json
```

生成状態種:

1. `Ar+`
2. `O2`
3. `Ar`
4. `O`
5. `O-`
6. `O+`
7. `O2+`
8. `O2-`
9. `O2[a1Delta_g]`
10. `O2[b1Sigma_g_plus]`

生成反応式:

1. `Ar+ + O2 -> Ar + O2+`
2. `e- + O2 -> O- + O`
3. `e- + O2 -> O2-`
4. `e- + O2 -> e- + O + O`
5. `e- + O2 -> e- + O2(a1Delta_g)`
6. `e- + O2 -> e- + O2(b1Sigma_g+)`
7. `e- + O2 -> e- + e- + O2+`
8. `e- + O2+ -> O + O`
9. `e- + O -> O-`
10. `Ar+ + O -> Ar + O+`
11. `Ar+ + O- -> Ar + O`
12. `Ar+ + O2- -> Ar + O2`
13. `O+ + O2 -> O + O2+`

family 内訳:

- `charge_transfer`
- `dissociative_recombination`
- `electron_attachment`
- `electron_dissociation`
- `electron_excitation`
- `electron_ionization`
- `ion_neutral_followup`
- `mutual_neutralization`

今回の build 条件では、`charge_window = -1 .. +1` を使っているため、
`O++` や `Ar++` のような二価種は出力に含めていません。
