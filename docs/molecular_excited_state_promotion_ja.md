# molecular excited-state promotion 設計

## 1. 目的

`state_master` に手で書いた `excited_states` だけでなく、QDB / IDEADB / VAMDC 由来の evidence から
**molecular excited state を runtime catalog に自動昇格**する。

今回の実装では、reaction template への昇格ではなく、
まず `SpeciesPrototype` への昇格を対象にしている。

## 2. 現在の実装点

- config:
  - `state_promotions.molecular_excited_states`
- runtime:
  - base catalog 構築
  - alias 正規化済み evidence index 構築
  - evidence から promoted excited state を抽出
  - `catalog.species_library` へ merge
- promoted species には `metadata` を保持する

主要ファイル:

- `src/plasma_reaction_builder/state_promotion.py`
- `src/plasma_reaction_builder/runtime.py`
- `src/plasma_reaction_builder/config.py`

## 3. config schema

```yaml
state_promotions:
  molecular_excited_states:
    enabled: true
    source_systems: [qdb, ideadb, vamdc]
    min_support_score: 0.8
    max_states_per_species: 3
    require_electron_signal: true
```

## 4. 昇格対象

`state_master` entry のうち、以下を対象にする。

- `excitation_policy in {molecular_curated, molecular_promoted, bucket_only}`
- 原子ではない species

## 5. 候補抽出ルール

### 5.1 explicit product token

evidence record の product に、以下のような excited token が直接入っている場合。

- `CH4(V14)`
- `O2(c1Sigma_u_minus)`
- `N2(B3Pi_g)`

token parser で `formula`, `charge`, `excitation_label` を読み取り、
base species と formula が一致すれば候補化する。

### 5.2 metadata-driven promotion

evidence metadata に `promoted_excited_states` を持つ場合。

```json
{
  "promoted_excited_states": [
    {
      "token": "CH4(V14)",
      "label": "V14",
      "energy_ev": 0.374,
      "display_name": "CH4(v14)"
    }
  ]
}
```

## 6. electron signal 判定

`require_electron_signal: true` の場合、以下のいずれかを満たす必要がある。

- reactants に `e-` がある
- `note`, `citation`, `metadata`, `evidence_kind` に `electron` / `excitation` / `vibrational` が含まれる

QDB の normalized snapshot が electron を reactants に持たない場合でも、
`process_family` や `note` から昇格できるようにしている。

## 7. source 別想定

### 7.1 QDB

- JSON snapshot
- explicit product token または `promoted_excited_states` metadata を使う
- 例: `examples/snapshots/qdb_molecular_excited_snapshot.json`

### 7.2 IDEADB

- XSAMS 経由
- molecule の `ChemicalName` に state label を含める
- 例: `N2(B3Pi_g)`
- 例: `examples/snapshots/vamdc_ideadb_molecular_excitation_sample.xsams`

### 7.3 VAMDC

- XSAMS 経由
- species label 抽出時に `(...)`, `[...]`, `*` を含む値を優先して stateful token として扱う
- 例: `examples/snapshots/vamdc_molecular_excitation_sample.xsams`

## 8. promoted species metadata

promoted species には以下を `metadata` に保持する。

- `promotion_kind`
- `base_species_key`
- `source_system`
- `source_name`
- `support_score`
- `citation`
- `source_url`
- `note`
- source record 由来の追加 metadata

## 9. 現在の制約

- molecular excited state の**species 昇格**まで
- reaction template の自動生成まではまだ行わない
- de-excitation / quenching / excited-state-specific fragmentation の自動昇格は未実装
- bucket promotion は schema 上可能だが、今は explicit label 중심

## 10. 次の段階

1. promoted excited state を使う reaction template 自動生成
2. excited-state-specific `electron_excitation`, `quenching`, `detachment`, `follow-up` の family 化
3. promoted species の lock / manifest 出力
4. QDB raw export から normalized excited-state snapshot を作る変換器
