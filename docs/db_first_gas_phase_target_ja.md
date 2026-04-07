# DB-First Gas-Phase Target Runtime

この構成は、`curated reaction pack` をできるだけ外し、
`state_master + external evidence + promotion` を主軸にして
半導体向け気相反応 network を組み立てるための基準例です。

対象 config:

- `examples/production_blueprint/config_gas_phase_target_db_first_runtime.yaml`

この config の考え方:

- `catalog_paths` は `catalog_00_references.yaml` だけにしている
- species は `state_master_base.yaml` から供給する
- reaction は QDB / VAMDC / IDEADB の normalized snapshot から昇格する
- 励起種は external evidence から state promotion する
- 励起種由来の `electron_excitation / radiative_relaxation / collisional_quenching / superelastic_deexcitation` は自動生成する

この runtime は、以下を同時に有効にしています。

- `state_promotions.molecular_excited_states`
- `template_promotions.source_backed_templates`
- `template_promotions.molecular_excited_state_templates`

使い方:

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_gas_phase_target_db_first_runtime.yaml `
  --output .tmp_gas_phase_target_db_first/network.json
```

この構成が向いている用途:

- curated YAML を増やす前に、外部DB由来だけでどこまで network が立つか見たい
- gas family ごとの reaction coverage を比較したい
- curated pack は fallback に留めて、DB-first の設計意図に寄せたい

注意点:

- 現在の snapshot は実証用の normalized sample を含むため、coverage は family ごとに均一ではありません
- `state_master` に存在しない species は `require_catalog_species: true` の間は template 昇格しません
- 完全自動汎用生成器というより、現状は `DB-driven semi-automatic curation` に近い構成です
