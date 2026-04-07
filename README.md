# plasma-reaction-builder v0.10

対象ガスと projectile を入れると、気相プラズマ反応ネットワークの状態リストと反応式リストを出力するツールです。  
user-facing preset は既定で `max_generation: 3` を使うので、1 次反応だけでなく、生成物がさらに反応する 2 次・3 次反応まで展開します。

## 何ができるか

- 入力: `config.yaml` に対象ガス、projectile、使う catalog / DB snapshot を指定
- 出力: `network.json`、`build_lock.json`、状態リスト CSV、反応式リスト CSV、監査 JSON
- 監査: build 前は `audit-config`、build 後は `audit-network` で fallback / promotion / source を追跡

## すぐ使えるプリセット

| 用途 | Config | 主な対象ガス | 既定 projectile |
| --- | --- | --- | --- |
| 支援ガス | `examples/production_blueprint/config_etch_common_support_runtime.yaml` | Ar, He, N2, H2, O2 | `e-`, `Ar+` |
| フルオロカーボン | `examples/production_blueprint/config_etch_fluorocarbon_runtime.yaml` | CF4, CHF3, CH2F2, CH3F, C2F6, c-C4F8, C5F8 | `e-` |
| 無機フッ化物 | `examples/production_blueprint/config_etch_inorganic_fluoride_runtime.yaml` | SF6, NF3 | `e-` |
| ハロゲン | `examples/production_blueprint/config_etch_halogen_runtime.yaml` | Cl2, HCl, Br2, HBr, BCl3 | `e-` |
| シラン系前駆体 | `examples/production_blueprint/config_deposition_silane_gas_phase_runtime.yaml` | SiH4, SiH2Cl2, SiHCl3 | `e-` |
| 成膜反応ガス | `examples/production_blueprint/config_deposition_reactant_gas_phase_runtime.yaml` | NH3, N2O, O3, H2, O2 | `e-` |
| 高度前駆体 | `examples/production_blueprint/config_advanced_precursor_runtime.yaml` | WF6, TEOS (`C8H20O4Si`) | `e-` |
| O2 + Ar+ 例 | `examples/production_blueprint/config_o2_electron_argon_ion_runtime.yaml` | O2 | `e-`, `Ar+` |
| CF4 + Ar+ 例 | `examples/production_blueprint/config_cf4_electron_argon_ion_runtime.yaml` | CF4 | `e-`, `Ar+` |
| CHF3 + Ar+ 例 | `examples/production_blueprint/config_chf3_electron_argon_ion_runtime.yaml` | CHF3 | `e-`, `Ar+` |

## 最短セットアップ

```powershell
uv sync --extra dev
```

以降の実行例は、sync 後に作られる `.venv` を直接使う前提です。

## 基本の実行方法

1. config の妥当性確認

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe validate-config `
  examples/production_blueprint/config_etch_halogen_runtime.yaml
```

2. build 前の監査

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe audit-config `
  examples/production_blueprint/config_etch_halogen_runtime.yaml `
  --output runs/example_halogen/config_audit.json
```

3. ネットワーク生成

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe build `
  examples/production_blueprint/config_etch_halogen_runtime.yaml `
  --output runs/example_halogen/network.json `
  --lock-output runs/example_halogen/build_lock.json
```

4. 状態リストと反応式リストの出力

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe visualize `
  runs/example_halogen/network.json `
  --config examples/production_blueprint/config_etch_halogen_runtime.yaml `
  --output-dir runs/example_halogen/visuals
```

主な一覧は次に出ます。

- `runs/example_halogen/visuals/lists/generated_species.csv`
- `runs/example_halogen/visuals/lists/generated_reactions.csv`

5. build 後の監査

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe audit-network `
  runs/example_halogen/network.json `
  --output runs/example_halogen/network_audit.json
```

## O2 / CF4 / CHF3 を `e-`, `Ar+` で実行するコマンド

### O2

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe build `
  examples/production_blueprint/config_o2_electron_argon_ion_runtime.yaml `
  --output runs/o2_electron_argon_ion_case/network.json `
  --lock-output runs/o2_electron_argon_ion_case/build_lock.json

.\.venv\Scripts\plasma-rxn-builder.exe visualize `
  runs/o2_electron_argon_ion_case/network.json `
  --config examples/production_blueprint/config_o2_electron_argon_ion_runtime.yaml `
  --output-dir runs/o2_electron_argon_ion_case/visuals
```

### CF4

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe build `
  examples/production_blueprint/config_cf4_electron_argon_ion_runtime.yaml `
  --output runs/cf4_electron_argon_ion_case/network.json `
  --lock-output runs/cf4_electron_argon_ion_case/build_lock.json

.\.venv\Scripts\plasma-rxn-builder.exe visualize `
  runs/cf4_electron_argon_ion_case/network.json `
  --config examples/production_blueprint/config_cf4_electron_argon_ion_runtime.yaml `
  --output-dir runs/cf4_electron_argon_ion_case/visuals
```

### CHF3

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe build `
  examples/production_blueprint/config_chf3_electron_argon_ion_runtime.yaml `
  --output runs/chf3_electron_argon_ion_case/network.json `
  --lock-output runs/chf3_electron_argon_ion_case/build_lock.json

.\.venv\Scripts\plasma-rxn-builder.exe visualize `
  runs/chf3_electron_argon_ion_case/network.json `
  --config examples/production_blueprint/config_chf3_electron_argon_ion_runtime.yaml `
  --output-dir runs/chf3_electron_argon_ion_case/visuals
```

## 現在の土台で multi-step が確認できている主なガス

現状の repo データで、単独 feed + `projectiles: [e-, Ar+]` として generation 2 以上を確認できている主なガスは次です。

- 3 次まで確認: `O2`, `HBr`, `HCl`, `BCl3`, `SiH4`, `SiH2Cl2`, `O3`
- 2 次まで確認: `c-C4F8`, `SF6`, `NF3`, `Cl2`, `SiHCl3`, `NH3`, `N2O`, `WF6`, `C8H20O4Si`

現状は 1 次反応中心のガスもあります。

- `CF4`, `CHF3`, `CH2F2`, `CH3F`, `C2F6`, `C5F8`, `Ar`, `N2`

この差は `max_generation` ではなく、現在入っている template と snapshot の厚みで決まります。

## 上級者向け: 手動でテンプレートを追加する

### 1. state を追加する

- feed や生成物として使いたい種を `examples/production_blueprint/state_master_base.yaml` に追加します
- user-facing runtime では `state_masters` から species を materialize します

### 2. reaction template を追加する

- `examples/production_blueprint/catalog_*.yaml` に反応 family ごとの YAML を追加します
- 1 ファイル 1 family、または 1 つの用途に絞るのがおすすめです

最小テンプレート例:

```yaml
reactions:
  - key: fluorocarbon::electron_dissociation::example
    family: electron_dissociation
    required_projectile: e-
    reactants: [CF4]
    products: [CF3, F]
    lhs_tokens: [e-, CF4]
    rhs_tokens: [e-, CF3, F]
    threshold_ev: 8.0
    base_confidence: 0.80
    reference_ids: [your_reference_id]
    note: "Manual fallback template."
```

### 3. config に組み込む

- `catalog_paths` に追加した YAML を登録します
- 追加後は次を順に実行します

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe validate-config <your_config.yaml>
.\.venv\Scripts\plasma-rxn-builder.exe audit-config <your_config.yaml>
.\.venv\Scripts\plasma-rxn-builder.exe build <your_config.yaml> --output runs/your_case/network.json
.\.venv\Scripts\plasma-rxn-builder.exe visualize runs/your_case/network.json --config <your_config.yaml> --output-dir runs/your_case/visuals
```

## 上級者向け: DB を使ってテンプレートを追加する

### 1. snapshot を用意する

- QDB / VAMDC / IDEADB などの snapshot を `examples/snapshots/` に置きます
- 既存 snapshot を正規化したい場合は `collect-evidence` を使います

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe collect-evidence `
  examples/your_source_config.yaml `
  --output examples/snapshots/your_snapshot.json
```

### 2. config で promotion を有効にする

```yaml
template_promotions:
  source_backed_templates:
    enabled: true
    source_systems: [qdb, vamdc, ideadb]
    target_families: [fluorocarbon]
    allowed_reaction_families:
      [electron_attachment, electron_dissociation, electron_ionization, ion_neutral_followup, dissociative_recombination]
    min_support_score: 0.84
    max_templates_per_family: 8
    require_catalog_species: true

bootstrap:
  reaction_evidence:
    sources:
      - kind: qdb_snapshot
        path: ../snapshots/your_snapshot.json
```

### 3. build 前後の監査で由来を確認する

```powershell
.\.venv\Scripts\plasma-rxn-builder.exe audit-config <your_config.yaml>
.\.venv\Scripts\plasma-rxn-builder.exe inspect-sources <your_config.yaml>
.\.venv\Scripts\plasma-rxn-builder.exe build <your_config.yaml> --output runs/your_case/network.json
.\.venv\Scripts\plasma-rxn-builder.exe audit-network runs/your_case/network.json
```

promotion と fallback の由来は次で追えます。

- `build_lock.json`
- `network.json` 内の `network_manifest`
- `visuals/lists/generated_reactions.csv` の `origin`, `source_system`

## 主な出力

- `network.json`
  最終 network 本体
- `build_lock.json`
  config source、catalog policy、manifest を含む lock
- `visuals/lists/generated_species.csv`
  状態リスト
- `visuals/lists/generated_reactions.csv`
  反応式リスト
- `config_audit.json`
  build 前の入力監査
- `network_audit.json`
  build 後の promotion / fallback 使用監査

## 主なコマンド

- `validate-config`
- `audit-config`
- `inspect-sources`
- `collect-evidence`
- `freeze-pubchem`
- `materialize-state-catalog`
- `build`
- `visualize`
- `audit-network`

## テスト

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 詳細ドキュメント

- `examples/production_blueprint/README.md`
- `docs/architecture_ja.md`
- `docs/operations_ja.md`
- `docs/source_acquisition_ja.md`
- `docs/source_update_recipes_ja.md`
