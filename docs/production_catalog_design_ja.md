# 本番用カタログ設計: chemistry-family / state マスタ / template 分割

## 1. 目的

本資料は、本番用の状態ライブラリと反応テンプレートライブラリを
「網羅的に取得し、あとで選択して使う」ための標準設計を定義する。

今回の前提は以下とする。

- 気相反応を対象とする
- 電子エネルギー上限は 10 keV
- 表面反応、壁損失、3 体反応は含めない
- charge range は `-2 .. +2`
- ただし state は範囲内で自動生成しない
- 明示 state は source-backed または curated なものだけを登録する

## 2. chemistry-family 一覧の確定

### 2.1 固定する base family

以下を本番用の固定 chemistry-family とする。

| family_id | 役割 | 代表種 |
| --- | --- | --- |
| `core_plasma` | family 横断で共通に必要な基盤種 | `e-`, `H`, `H+`, `H-`, `O`, `O+`, `N`, `N+`, `F`, `F-`, `Cl`, `Cl-`, `Ar`, `Ar+`, `Ar++` |
| `hydrogen` | H/H2 系の反応群 | `H2`, `H2+`, `H2-`, `H3+` |
| `hydrocarbon` | C/H 系の炭化水素群 | `CH4`, `CH3`, `CH2`, `C2H2`, `C2H4`, `C2H6` |
| `oxygen` | O 系 / 酸素分子系 | `O2`, `O3`, `O-`, `O2-`, `O+`, `O2+` |
| `nitrogen` | N 系 / 窒素分子系 | `N2`, `N`, `N+`, `N2+`, `N2-` |
| `fluorocarbon` | C/F 系のフルオロカーボン群 | `CF4`, `CF3`, `CF2`, `C2F4`, `c-C4F8` |
| `chlorine` | Cl 系 / 塩素化学 | `Cl2`, `Cl`, `Cl-`, `Cl+`, `HCl` |
| `bromine` | Br 系 / 臭素化学 | `Br2`, `Br`, `Br-`, `Br+`, `HBr` |
| `sulfur` | S 系 / 硫黄化学 | `S`, `S2`, `SO`, `SO2`, `SFx` |
| `silicon` | Si 系 / シラン系 | `SiH4`, `Si`, `SiH2`, `SiF4`, `SiCl4` |
| `phosphorus` | P 系 / リン化学 | `PH3`, `P`, `PxHy` |
| `noble_gas` | 希ガス / 励起・イオンキャリア | `He`, `Ne`, `Ar`, `Kr`, `Xe` |

### 2.2 overlay family

base family だけで扱いにくい交差系は overlay family として扱う。
overlay family は base family を置き換えず、追加ロードする前提とする。

| overlay_id | 用途 |
| --- | --- |
| `impurity_common` | `H2O`, `CO`, `CO2`, `NO`, `NO2` などの汎用不純物 |
| `mix_oxy_hydrocarbon` | `CHxOy`, `CxHyOz` |
| `mix_nitro_hydrocarbon` | `HCN`, `CN`, `NHxCy` |
| `mix_oxy_nitrogen` | `NO`, `N2O`, `NO2`, `NO+` |
| `mix_halide_silicon` | `SiFx`, `SiClx`, `SiFxClz` |
| `mix_halide_hydrocarbon` | `CHxFy`, `CHxClz`, `CFxClz` |

### 2.3 ロード単位

本番では以下のロード単位を標準とする。

1. `core_plasma`
2. 主要 gas chemistry-family
3. 必要な overlay family
4. project override

例:

- CH4/O2/N2 系: `core_plasma`, `hydrogen`, `hydrocarbon`, `oxygen`, `nitrogen`, `impurity_common`, `mix_oxy_hydrocarbon`, `mix_oxy_nitrogen`
- c-C4F8/Ar 系: `core_plasma`, `fluorocarbon`, `noble_gas`, `impurity_common`, `mix_halide_hydrocarbon`

## 3. state マスタ設計

### 3.1 二層構造

本番用 state マスタは二層に分ける。

1. `state_master_base`
   - 設計用の上位マスタ
   - family, alias, allowed charge range, excitation policy を保持する
   - そのまま現在の loader には読ませない
2. `catalog species`
   - 実行時の `SpeciesPrototype` 互換 YAML
   - build で直接読む explicit state

### 3.2 state_master_base の標準項目

`state_master_base.yaml` では以下を標準項目とする。

| key | 意味 |
| --- | --- |
| `family` | chemistry-family |
| `species_id` | base species の安定 ID |
| `preferred_key` | neutral canonical key |
| `display_name` | 表示名 |
| `formula` | neutral formula |
| `aliases` | DB 表記ゆれ |
| `tags` | family / role / composition tags |
| `allowed_charges` | 明示的に許容する charge list |
| `charge_window_min` | 最小 charge |
| `charge_window_max` | 最大 charge |
| `excitation_policy` | `none`, `atomic_asd`, `molecular_curated`, `bucket_only` |
| `priority` | curated 優先度 |
| `required_sources` | 生成根拠候補 |
| `enabled` | 使用可否 |

### 3.3 explicit state の標準項目

実行時 catalog では現在の `SpeciesPrototype` と互換な以下の項目だけを使う。

- `key`
- `display_name`
- `formula`
- `charge`
- `state_class`
- `multiplicity`
- `structure_id`
- `excitation_label`
- `excitation_energy_ev`
- `nist_query`
- `aliases`
- `tags`

### 3.4 key naming 規約

| 状態 | 規約 | 例 |
| --- | --- | --- |
| neutral | formula or curated structural key | `CH4`, `c-C4F8`, `SiF4` |
| cation q=+1 | trailing `+` | `CH4+`, `Ar+` |
| cation q=+2 | trailing `++` | `Ar++`, `O++` |
| anion q=-1 | trailing `-` | `O-`, `Cl-` |
| anion q=-2 | trailing `--` | `O--`, `C2F4--` |
| excited explicit | square-bracket suffix | `CH4[V13]`, `Ar[1s5]` |
| excited bucket | star or bucket label | `CF4*`, `CF4[high_e_excited]` |

注意:

- `-2 .. +2` は schema 上の許容範囲であり、全 species に対して自動展開しない
- doubly charged anion / cation は source-backed または明示 curated の場合のみ explicit state にする

### 3.5 state_class 規約

| 条件 | state_class |
| --- | --- |
| electron | `electron` |
| charge > 0 | `cation` |
| charge < 0 | `anion` |
| neutral atomic species | `atom` |
| neutral molecular / radical ground | `ground` |
| excitation_label あり | `excited` |
| 粗い励起バケット | `excited_bucket` |

### 3.6 family ごとの最小 state block

以下を各 family の最低 curated block とする。

| family | 必須 block |
| --- | --- |
| `core_plasma` | `e-`, atomic neutrals, primary atomic cations, representative atomic dianions/dications only if source-backed |
| `hydrogen` | `H2`, `H`, `H+`, `H-`, `H2+`, `H2-`, `H3+` |
| `hydrocarbon` | `C`, `CH`, `CH2`, `CH3`, `CH4`, plus major `+/-` fragments |
| `oxygen` | `O`, `O2`, `O3`, `O-`, `O2-`, `O+`, `O2+`, representative `O++` |
| `nitrogen` | `N`, `N2`, `N+`, `N2+`, `N2-`, representative metastables |
| `fluorocarbon` | `F`, `F-`, `CFx`, `C2Fx`, `C3Fx`, `C4Fx`, major cations/anions |
| `chlorine` | `Cl`, `Cl2`, `Cl-`, `Cl+`, `Cl2+`, `HCl`, `ClO` |
| `bromine` | `Br`, `Br2`, `Br-`, `Br+`, `HBr` |
| `silicon` | `Si`, `SiH4`, `SiFx`, `SiClx`, major cations |
| `sulfur` | `S`, `S2`, `SO`, `SO2`, `SFx`, major ions |
| `phosphorus` | `P`, `PH3`, `PxHy`, major ions |
| `noble_gas` | `He`, `Ne`, `Ar`, `Kr`, `Xe` and `+`, `++`, curated metastables |

### 3.7 推奨ファイル分割

state は以下の単位で分割する。

```text
catalog/
  00_references/
  10_species/
    species_core_plasma.yaml
    species_hydrogen.yaml
    species_hydrocarbon.yaml
    species_oxygen.yaml
    species_nitrogen.yaml
    species_fluorocarbon.yaml
    species_chlorine.yaml
    species_bromine.yaml
    species_sulfur.yaml
    species_silicon.yaml
    species_phosphorus.yaml
    species_noble_gas.yaml
    species_overlay_impurity_common.yaml
    species_overlay_mix_oxy_hydrocarbon.yaml
    species_overlay_mix_oxy_nitrogen.yaml
```

## 4. family ごとの template YAML 分割案

### 4.1 分割原則

reaction template は以下の 2 軸で分割する。

1. reaction family
2. chemistry-family

ファイル名は以下に固定する。

`reactions_<reaction_family>_<chemistry_family>.yaml`

例:

- `reactions_electron_attachment_hydrocarbon.yaml`
- `reactions_electron_ionization_fluorocarbon.yaml`
- `reactions_charge_transfer_noble_gas.yaml`

### 4.2 採用する reaction family

| reaction_family | 内容 |
| --- | --- |
| `electron_attachment` | 電子付着 / 解離性電子付着を含む |
| `electron_excitation` | 電子励起 |
| `electron_excitation_vibrational` | 分子振動励起 |
| `electron_dissociation` | 電子解離 |
| `electron_ionization` | 親イオン化 |
| `electron_dissociative_ionization` | 解離性イオン化 |
| `electron_detachment` | 負イオンからの電子脱離 |
| `neutral_fragmentation` | 中性種の分解 |
| `radical_fragmentation` | ラジカルの分解 |
| `ion_fragmentation` | イオン分解 |
| `ion_neutral_followup` | イオン-中性後続 |
| `ion_neutral_reaction` | イオン-中性反応一般 |
| `charge_transfer` | 電荷移動 |
| `dissociative_recombination` | 解離性再結合 |
| `ion_ion_neutralization` | イオン-イオン中和 |
| `radical_neutral_reaction` | ラジカル-中性反応 |
| `exchange_reaction` | 置換・交換 |

### 4.3 推奨ディレクトリ構成

```text
catalog/
  00_references/
    references_core.yaml
    references_source_mappings.yaml

  10_species/
    species_core_plasma.yaml
    species_hydrogen.yaml
    species_hydrocarbon.yaml
    species_oxygen.yaml
    species_nitrogen.yaml
    species_fluorocarbon.yaml
    species_chlorine.yaml
    species_bromine.yaml
    species_sulfur.yaml
    species_silicon.yaml
    species_phosphorus.yaml
    species_noble_gas.yaml

  20_reactions_electron/
    reactions_electron_attachment_hydrogen.yaml
    reactions_electron_attachment_hydrocarbon.yaml
    reactions_electron_attachment_fluorocarbon.yaml
    reactions_electron_excitation_noble_gas.yaml
    reactions_electron_excitation_hydrocarbon.yaml
    reactions_electron_excitation_vibrational_hydrocarbon.yaml
    reactions_electron_dissociation_hydrocarbon.yaml
    reactions_electron_dissociation_fluorocarbon.yaml
    reactions_electron_ionization_core_plasma.yaml
    reactions_electron_ionization_hydrocarbon.yaml
    reactions_electron_dissociative_ionization_hydrocarbon.yaml
    reactions_electron_dissociative_ionization_fluorocarbon.yaml
    reactions_electron_detachment_halogen.yaml

  30_reactions_ion/
    reactions_ion_fragmentation_hydrocarbon.yaml
    reactions_ion_fragmentation_fluorocarbon.yaml
    reactions_ion_neutral_followup_hydrocarbon.yaml
    reactions_ion_neutral_followup_fluorocarbon.yaml
    reactions_ion_neutral_reaction_oxygen.yaml
    reactions_charge_transfer_noble_gas.yaml
    reactions_charge_transfer_halogen.yaml
    reactions_dissociative_recombination_core_plasma.yaml
    reactions_ion_ion_neutralization_core_plasma.yaml

  40_reactions_neutral/
    reactions_neutral_fragmentation_hydrocarbon.yaml
    reactions_neutral_fragmentation_fluorocarbon.yaml
    reactions_radical_fragmentation_hydrocarbon.yaml
    reactions_radical_fragmentation_fluorocarbon.yaml
    reactions_radical_neutral_reaction_oxygen.yaml
    reactions_exchange_reaction_nitrogen.yaml

  90_overrides/
    overrides_project_specific.yaml
```

### 4.4 template の key 規約

template key は以下に固定する。

`<chemistry_family>::<reaction_family>::<channel_name>`

例:

- `hydrocarbon::electron_attachment::ch4_h_minus`
- `fluorocarbon::electron_dissociative_ionization::cc4f8_cf2_plus_c3f6`
- `noble_gas::charge_transfer::ar_plus_o2`

### 4.5 template の標準属性

現在の runtime 互換属性:

- `key`
- `family`
- `required_projectile`
- `reactants`
- `products`
- `lhs_tokens`
- `rhs_tokens`
- `threshold_ev`
- `delta_h_kj_mol`
- `base_confidence`
- `reference_ids`
- `note`
- `inferred_balance`
- `missing_products`

将来拡張候補:

- `charge_window_min`
- `charge_window_max`
- `source_count`
- `promotion_stage`
- `review_status`

## 5. 生成・運用フロー

1. `state_master_base.yaml` を保守する
2. `state_masters` を config に指定して build 時に materialize する
3. 必要に応じて same input から source-backed な explicit state を `species_*.yaml` に出力する
4. DB evidence を reaction-family ごとに整理する
5. 昇格判定を通したものだけを `reactions_<family>_<chemistry>.yaml` に入れる
6. project ごとの追加は `90_overrides` に置く

## 6. 今回追加したブループリント

以下の雛形を `examples/production_blueprint/` に追加する。

- `state_master_base.yaml`
- `catalog_00_references.yaml`
- `catalog_10_species_core_plasma.yaml`
- `catalog_11_species_hydrocarbon.yaml`
- `catalog_20_reactions_electron_attachment_hydrocarbon.yaml`
- `catalog_21_reactions_electron_ionization_hydrocarbon.yaml`

これらは設計の具体例であり、本番 curated 資産そのものではない。
