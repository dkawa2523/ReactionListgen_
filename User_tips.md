# User Tips

このファイルは、ユーザーが自分で

- 既存テンプレートを修正する
- 新しいガス種を追加する
- 新しい反応リストを追加する
- 外部データベース由来の promotion を追加する
- 励起種の promotion と follow-up を追加する

状態リストと反応式リストを出したいときは、1 次反応だけで終わらせず 2 次・3 次反応まで含めるのが既定です。

ときの実務手順をまとめたものです。

このリポジトリは、単に反応式 YAML を足すだけではなく、

1. `state_master` で種の設計を行う
2. `catalog_*.yaml` で curated template を定義する
3. 必要なら `snapshot` と `promotion config` で外部 evidence をつなぐ
4. `build` と `pytest` で network と回帰を確認する

という流れで使う前提です。

## 1. 最初に見る場所

普段よく触るファイルは次のとおりです。

- `examples/production_blueprint/state_master_base.yaml`
  - ガス種、フラグメント、イオン、励起種の親定義
- `examples/production_blueprint/catalog_00_references.yaml`
  - `reference_ids` の参照元
- `examples/production_blueprint/catalog_*.yaml`
  - curated reaction template
- `examples/production_blueprint/excited_state_registry.yaml`
  - 励起状態の表記ゆれ吸収
- `examples/production_blueprint/config_*.yaml`
  - build 実行用の sample config
- `examples/snapshots/*.json`
  - source-backed promotion 用の normalized evidence
- `examples/production_blueprint/README.md`
  - blueprint 側の実行例

### 1.1 編集すべき正本一覧

「どのファイルを直すべきか」で迷ったら、まずこの表を見てください。

| 目的 | 編集すべき正本 | 形式 | 役割 | 触るタイミング |
| --- | --- | --- | --- | --- |
| ガス種、フラグメント、イオン、親励起種の設計 | `examples/production_blueprint/state_master_base.yaml` | YAML | species 設計の正本 | 新しいガス種や主要 fragment を追加するとき |
| curated reaction template | `examples/production_blueprint/catalog_*_reactions_*.yaml` | YAML | curated 反応式の正本 | 反応式を手修正・新規追加するとき |
| `reference_ids` の辞書 | `examples/production_blueprint/catalog_00_references.yaml` | YAML | template の参照元辞書 | 新しい curated group や citation を追加するとき |
| 励起状態の canonical key と表記ゆれ吸収 | `examples/production_blueprint/excited_state_registry.yaml` | YAML | excited-state 辞書の正本 | 新しい励起状態や別表記を追加するとき |
| source-backed promotion 用の normalized evidence | `examples/snapshots/*.json` | JSON | 外部 DB 由来 evidence の正本 | QDB/VAMDC/IDEADB 由来の反応や励起状態を promotion したいとき |
| 実行レシピ | `examples/production_blueprint/config_*.yaml` | YAML | build/promotion の設定正本 | 新しい family や sample runtime を追加するとき |
| alias の補助辞書 | `examples/aliases.yaml` | YAML | species 表記ゆれの補助辞書 | base species の別名を足したいとき |
| source 優先度の補助辞書 | `src/plasma_reaction_builder/data/source_profiles.yaml` または `examples/source_profiles_override.yaml` | YAML | source の強さ・優先度設定 | evidence の重みや priority を調整したいとき |
| 既定の同梱 species 辞書 | `src/plasma_reaction_builder/data/species_library.yaml` | YAML | パッケージ標準 species | blueprint ではなく同梱デフォルトを直接直すときだけ |
| 既定の同梱 reaction pack | `src/plasma_reaction_builder/data/reactions_*.yaml` | YAML | パッケージ標準 template | blueprint ではなく同梱デフォルトを直接直すときだけ |
| 既定の同梱 references | `src/plasma_reaction_builder/data/references.yaml` | YAML | パッケージ標準 references | 同梱 default を更新するときだけ |

### 1.2 基本的に正本ではないもの

次のファイルは「結果」または「検証用」であり、通常は編集対象ではありません。

| 種別 | 代表ファイル | 扱い |
| --- | --- | --- |
| build 出力 | `output_network.json`, `.tmp_*/network.json` | 実行結果。手で直さず、入力側を直して再生成する |
| source inspection / lock | `examples/source_inspection.json`, `examples/source_lock.json`, `examples/build_lock.json` | 監査・再現用。手編集せず再出力する |
| README / report | `examples/production_blueprint/README.md`, `docs/*.md`, `prb_v10_report_revised/*.md` | 手順書や説明資料。仕様変更に合わせて更新するが、データ正本ではない |
| packaged egg-info | `src/plasma_reaction_builder.egg-info/*` | 生成物なので通常は触らない |

### 1.3 まずどこを直すべきかの判断

最短で言うと、次の使い分けです。

- species を増やすなら `state_master_base.yaml`
- 手で反応式を増やすなら `catalog_*_reactions_*.yaml`
- citation を足すなら `catalog_00_references.yaml`
- DB の別表記を吸収するなら `excited_state_registry.yaml` または `aliases.yaml`
- DB 由来データをつなぐなら `examples/snapshots/*.json` と `config_*.yaml`
- 実行結果が気に入らないからといって `.tmp_*` や `output_network.json` は直さない

## 2. 作業パターンの選び方

### パターンA: 既存テンプレートを少し直す

対象:

- 反応式の生成物を 1 つ修正したい
- `base_confidence` や `reference_ids` を直したい
- note を補足したい

触る場所:

- 既存の `catalog_*.yaml`

追加でやること:

- そのテンプレートを使う sample config で `build`
- 関連する test を更新

### パターンB: 新しいガス種を追加したい

対象:

- feed gas を追加したい
- そのガスの親分子、フラグメント、イオンを扱いたい

触る場所:

- `state_master_base.yaml`
- 必要に応じて `catalog_*.yaml`
- 実行に使う `config_*.yaml`

### パターンC: 反応リストを curated で追加したい

対象:

- 手元の論文や整理済み反応表をそのまま YAML 化したい

触る場所:

- `catalog_*.yaml`
- `catalog_00_references.yaml`

### パターンD: 外部 DB を promotion でつなぎたい

対象:

- QDB などの evidence を normalized snapshot にして取り込みたい
- curated pack と source-backed promotion を橋渡ししたい

触る場所:

- `examples/snapshots/*.json`
- `config_*.yaml` の `template_promotions.source_backed_templates`

### パターンE: 励起種まで扱いたい

対象:

- 分子励起状態を external evidence から昇格したい
- excitation / relaxation / quenching / superelastic / excited follow-up を連動させたい

触る場所:

- `state_master_base.yaml`
- `excited_state_registry.yaml`
- `examples/snapshots/*.json`
- `config_*.yaml` の `state_promotions` と `template_promotions`

## 3. 命名ルール

### species key

- neutral: `CH4`, `SF6`, `WF6`, `c-C4F8`
- cation: `CH4+`, `WF6+`
- anion: `SF6-`, `Cl-`
- excited state canonical key: `CH4[V14]`, `SF6[A1]`, `WF6[B1]`

### reaction family

よく使うもの:

- `electron_attachment`
- `electron_excitation`
- `electron_excitation_vibrational`
- `electron_ionization`
- `electron_dissociation`
- `radical_neutral_reaction`
- `ion_neutral_followup`
- `dissociative_recombination`
- `radiative_relaxation`
- `collisional_quenching`
- `superelastic_deexcitation`

### ファイル名

- species 設計: `state_master_base.yaml`
- curated template: `catalog_<番号>_reactions_<reaction_family>_<group>.yaml`
- sample config: `config_<用途>_runtime.yaml`
- source snapshot: `examples/snapshots/<用途>.json`

## 4. 新しいガス種を追加する手順

ここでは「新しいガス種を 1 つ追加して build できるようにする」最小手順を示します。

### Step 1. family を決める

まず、そのガスをどの chemistry-family に置くか決めます。

例:

- `Cl2`, `HCl` -> `chlorine`
- `SF6` -> `sulfur`
- `WF6` -> `tungsten`
- `TEOS` -> `organosilicon`

新しい family を作る場合は、既存 family の playbook と同じ粒度でそろえるのが安全です。

### Step 2. `state_master_base.yaml` に親状態を書く

最低限、親分子を追加します。

必要項目:

- `family`
- `species_id`
- `preferred_key`
- `display_name`
- `formula`
- `aliases`
- `tags`
- `allowed_charges`
- `excitation_policy`
- `required_sources`

例:

```yaml
  - family: sulfur
    species_id: sulfur_hexafluoride
    preferred_key: SF6
    display_name: Sulfur hexafluoride
    formula: SF6
    aliases: [sulfur_hexafluoride]
    tags: [feed_candidate, sulfur, inorganic_fluoride, etch_gas]
    allowed_charges: [-1, 0, 1]
    charge_window_min: -2
    charge_window_max: 2
    excitation_policy: molecular_promoted
    priority: 99
    required_sources: [pubchem, qdb]
    enabled: true
```

### Step 3. 必要なフラグメントも追加する

親分子だけでは `electron_dissociation` や follow-up で詰まります。

追加の目安:

- 1段目解離で出る主要 fragment
- 主要 cation/anion
- follow-up で再利用される radical

例:

- `SF6` を入れるなら `SF5`, `SF4`, `F`
- `SiH2Cl2` を入れるなら `SiHCl2`, `SiCl2`, `H`, `H2`
- `TEOS` を入れるなら `C6H15O3Si`, `C2H5O`

### Step 4. 実行 config の `feeds` と `state_masters` に入れる

例:

```yaml
feeds:
  - species_key: SF6
    formula: SF6
    display_name: Sulfur hexafluoride

state_masters:
  - path: state_master_base.yaml
    families: [core_plasma, oxygen, sulfur]
```

## 5. curated reaction template を追加する手順

### Step 1. 参照元を `catalog_00_references.yaml` に追加する

新しい group を作るなら、共通 reference block を作っておくと管理しやすいです。

例:

```yaml
  curated_process_gases:
    source_system: template_library
    source_name: production_process_gas_library
    acquisition_method: package_template
    evidence_kind: curated_reaction_family
    support_score: 0.80
    citation: "Production curated process-gas library"
    note: "Shared reference block for process-gas activation channels."
```

### Step 2. `catalog_*.yaml` を作る

最低限必要な項目:

- `key`
- `family`
- `reactants`
- `products`
- `lhs_tokens`
- `rhs_tokens`
- `base_confidence`
- `reference_ids`

例:

```yaml
reactions:
  - key: process_gases::electron_dissociation::sf6_to_sf5_f
    family: electron_dissociation
    required_projectile: e-
    reactants: [SF6]
    products: [SF5, F]
    lhs_tokens: [e-, SF6]
    rhs_tokens: [e-, SF5, F]
    base_confidence: 0.82
    reference_ids: [curated_process_gases]
    note: "Representative sulfur hexafluoride bond-cleavage channel."
```

### Step 3. どの reaction family から埋めるか

新しい family を作るときの推奨順:

1. `electron_attachment` または `electron_ionization`
2. `electron_dissociation`
3. `radical_neutral_reaction`
4. `ion_neutral_followup`
5. `dissociative_recombination`
6. 必要なら `charge_transfer` や `neutral_fragmentation`

理由:

- parent charge state と primary fragment が先にないと、その後続反応が network に乗りにくい

## 6. source-backed template promotion を追加する手順

### Step 1. snapshot を作る

既存の snapshot は normalized 済み JSON を前提にしています。

最小形:

```json
{
  "records": [
    {
      "reactants": ["SF6+", "O2"],
      "products": ["SF4", "F", "F", "O2+"],
      "citation": "Example snapshot",
      "source_url": "https://example.invalid/",
      "support_score": 0.88,
      "note": "Example follow-up channel.",
      "chemistry_id": 1,
      "process_family": "ion_neutral_followup",
      "promotion_family": "sulfur",
      "promotion_stage": "curated_bridge"
    }
  ]
}
```

### Step 2. config に promotion を書く

例:

```yaml
template_promotions:
  source_backed_templates:
    enabled: true
    source_systems: [qdb]
    target_families: [sulfur, tungsten]
    allowed_reaction_families: [electron_dissociation, ion_neutral_followup, dissociative_recombination]
    min_support_score: 0.84
    max_templates_per_family: 4
    require_catalog_species: true
```

### Step 3. snapshot を `bootstrap.reaction_evidence.sources` につなぐ

```yaml
bootstrap:
  reaction_evidence:
    seed_templates: false
    sources:
      - kind: qdb_snapshot
        path: ../snapshots/qdb_process_precursor_template_promotion_snapshot.json
```

### Step 4. promotion が効かないときの確認項目

- `promotion_family` が `state_master` の family と一致しているか
- `process_family` が許可済み family に入っているか
- `support_score` が `min_support_score` を超えているか
- `require_catalog_species: true` のとき、登場 species が catalog に全部あるか
- 反応式が balance しているか

## 7. excited-state promotion を追加する手順

### Step 1. `excitation_policy` を `molecular_promoted` にする

励起状態を external evidence から昇格したい base species には、`state_master_base.yaml` で次を設定します。

```yaml
excitation_policy: molecular_promoted
```

### Step 2. `excited_state_registry.yaml` に canonical key を追加する

例:

```yaml
  - canonical_key: "SF6[A1]"
    source_aliases:
      qdb: [SF6(A1), SF6(a1)]
    label_synonyms: [A1, a1]
    excitation_energy_ev: 3.30
    energy_tolerance_ev: 0.20
    priority_source: qdb
```

この registry は、DB ごとの表記差を canonical key に畳み込むためのものです。

### Step 3. snapshot に `promoted_excited_states` を入れる

例:

```json
{
  "reactants": ["SF6"],
  "products": ["SF6(a1)"],
  "support_score": 0.90,
  "process_family": "electron_excitation",
  "promotion_family": "sulfur",
  "promoted_excited_states": [
    {
      "token": "SF6(a1)",
      "label": "A1",
      "energy_ev": 3.30,
      "display_name": "SF6(A1)"
    }
  ]
}
```

### Step 4. config で state promotion を有効化する

```yaml
state_promotions:
  molecular_excited_states:
    enabled: true
    source_systems: [qdb]
    min_support_score: 0.84
    max_states_per_species: 2
    require_electron_signal: true
```

## 8. 励起種由来の自動 template を追加する手順

`template_promotions.molecular_excited_state_templates` を使うと、promoted excited state から自動で

- `electron_excitation`
- `radiative_relaxation`
- `collisional_quenching`
- `superelastic_deexcitation`

を生成できます。

例:

```yaml
template_promotions:
  molecular_excited_state_templates:
    enabled: true
    source_systems: [qdb]
    target_families: [sulfur, nitrogen, tungsten]
    min_support_score: 0.84
    include_electron_excitation: true
    include_radiative_relaxation: true
    include_collisional_quenching: true
    include_superelastic_deexcitation: true
    quenching_partners:
      sulfur: [SF6, O2]
      nitrogen: [NF3, O2]
      tungsten: [WF6, H2]
```

## 9. 励起種由来の follow-up を追加する手順

励起状態そのものを反応物に持つ curated/source-backed 反応を追加したい場合は、snapshot にそのまま書きます。

例:

```json
{
  "reactants": ["SF6[A1]", "O2"],
  "products": ["SF5", "F", "O2"],
  "support_score": 0.87,
  "process_family": "radical_neutral_reaction",
  "promotion_family": "sulfur",
  "promotion_stage": "excited_state_followup"
}
```

ポイント:

- excited state を表す token は snapshot 側で `[]` を使って canonical key にしておくのが安全
- `source_backed_templates` の `allowed_reaction_families` にその family を入れる
- `require_catalog_species: true` のとき、励起種が先に `state_promotion` で catalog に入る必要がある

## 10. 実行と検証の基本コマンド

### config の妥当性確認

```powershell
py -3.13 -m uv run plasma-rxn-builder validate-config examples/production_blueprint/config_gas_phase_target_runtime.yaml
```

### state master から species を materialize

```powershell
py -3.13 -m uv run plasma-rxn-builder materialize-state-catalog `
  examples/production_blueprint/state_master_base.yaml `
  --output examples/production_blueprint/catalog_10_species_generated.yaml `
  --families sulfur tungsten `
  --charge-window-min 0 `
  --charge-window-max 1
```

### network build

```powershell
py -3.13 -m uv run plasma-rxn-builder build `
  examples/production_blueprint/config_excited_fluoride_precursor_template_promotion_runtime.yaml `
  --output .tmp_check/network.json
```

### source inspection

```powershell
py -3.13 -m uv run plasma-rxn-builder inspect-sources `
  examples/production_blueprint/config_process_precursor_template_promotion_runtime.yaml `
  --output .tmp_check/inspect_sources.json
```

### テスト

全部回す:

```powershell
py -3.13 -m uv run pytest -q
```

部分的に回す:

```powershell
py -3.13 -m uv run pytest tests/test_state_promotion.py tests/test_template_promotion.py tests/test_excited_template_promotion.py -q
```

## 11. 追加時のチェックリスト

### 新しいガス種を追加したとき

- `state_master_base.yaml` に親種がある
- 必要な fragment がある
- 必要な charge state が `allowed_charges` に入っている
- sample config の `feeds` に入っている
- sample config の `state_masters.families` に family が入っている

### 新しい curated template を追加したとき

- 参照する species が catalog に存在する
- `lhs_tokens` と `rhs_tokens` が表示したい式と一致している
- `reference_ids` が `catalog_00_references.yaml` にある
- build で実際に network に乗る

### source-backed promotion を追加したとき

- snapshot の token が canonical key と整合している
- `promotion_family` が正しい
- `process_family` が allowed list に入っている
- `support_score` が閾値以上
- network に promoted equation が入る

### excited-state coupling を追加したとき

- `excitation_policy: molecular_promoted` にしている
- registry に canonical key がある
- `promoted_excited_states` が snapshot にある
- quenching partner が config または default にある
- excited follow-up が source-backed promotion で拾われている

## 12. よくある失敗

### 1. `NO` が false 扱いされる

YAML では `NO` が boolean に解釈されることがあります。

安全策:

- `"NO"` のようにダブルクォートする

これは `preferred_key`, `formula`, `products`, `rhs_tokens` でも同じです。

### 2. reaction は書いたのに build で出てこない

主な原因:

- feed に必要な reactant がいない
- generation depth が浅い
- `charge_window` で必要 species が落ちている
- species はあるが、その前段反応がなくて state が生成されていない

### 3. promotion が効かない

主な原因:

- `require_catalog_species: true` で species 不足
- `promotion_family` 不一致
- `support_score` 不足
- `allowed_reaction_families` に入っていない

### 4. excited state が別物として増殖する

主な原因:

- registry 未登録
- `A1`, `a1`, `A^1` のような label variation が吸収されていない

対策:

- `excited_state_registry.yaml` に canonical key と alias を追加する

## 13. 迷ったときの推奨順

1. まず `state_master_base.yaml` を足す
2. 次に curated template を少数追加する
3. `build` で network が出るか確認する
4. その後に source-backed promotion をつなぐ
5. 最後に excited-state promotion と coupling を足す

この順だと、どの段階で壊れたかを切り分けやすいです。

## 14. 参考にしやすい sample

- 単純な family 追加
  - `examples/production_blueprint/config_chlorine_family_runtime.yaml`
  - `examples/production_blueprint/config_bromine_family_runtime.yaml`
  - `examples/production_blueprint/config_silicon_family_runtime.yaml`

- source-backed promotion
  - `examples/production_blueprint/config_halogen_fluorocarbon_template_promotion_runtime.yaml`
  - `examples/production_blueprint/config_process_precursor_template_promotion_runtime.yaml`

- excited-state promotion
  - `examples/production_blueprint/config_state_promotion_runtime.yaml`
  - `examples/production_blueprint/config_state_promotion_template_runtime.yaml`

- excited-state coupling
  - `examples/production_blueprint/config_excited_precursor_template_promotion_runtime.yaml`
  - `examples/production_blueprint/config_excited_fluoride_precursor_template_promotion_runtime.yaml`

## 15. 変更後に最低限やること

変更が終わったら、最低限これを実行してください。

```powershell
py -3.13 -m uv run plasma-rxn-builder build <config.yaml> --output .tmp_check/network.json
py -3.13 -m uv run pytest -q
```

これで通らない場合は、

- species が足りない
- family の結線が足りない
- promotion 条件が厳しすぎる
- YAML の token 表記が崩れている

のどれかであることがほとんどです。
