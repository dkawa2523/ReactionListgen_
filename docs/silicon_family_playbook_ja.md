# Silicon Family プレイブック

## 1. 対象

`silicon family` を気相 precursor family として追加するときの具体例です。今回の対象は次の親種と一次フラグメントです。

親種:

- `SiH4`
- `SiH2Cl2`
- `SiHCl3`

一次フラグメント:

- `SiH3`
- `SiH2`
- `SiH`
- `SiHCl2`
- `SiCl3`
- `SiCl2`

補助 family:

- `hydrogen`
- `chlorine`
- `core_plasma`

## 2. どの DB から何を取るか

| DB / source | 取るもの | silicon family での用途 |
| --- | --- | --- |
| `PubChem` | formula, synonym, CID | `SiH4`, `SiH2Cl2`, `SiHCl3` の canonical key と alias 整理 |
| `ATcT` | 熱化学 | `SiH3`, `SiCl3` などフラグメント反応の sanity check |
| `QDB` | 電子衝突 evidence | 親分子の ionization / dissociation の優先根拠 |
| `NIST Chemical Kinetics` | 気相反応 evidence | `SiH3 + H -> SiH4` のような closure 反応の補強 |
| `UMIST`, `KIDA` | ラジカル・中性反応 | precursor follow-up を補助 |
| `VAMDC` | 補助的な状態情報 | 将来の excited state や ionic follow-up の整理に利用 |

## 3. state_master をどう書くか

実装済みの blueprint では次の state を使えます。

- `Si`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L505)
- `SiH3`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L520)
- `SiH2`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L535)
- `SiH`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L550)
- `SiH4`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L565)
- `SiH2Cl2`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L595)
- `SiHCl2`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L610)
- `SiHCl3`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L640)
- `SiCl3`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L625)

設計方針:

- 親種は `feed_candidate`
- フラグメントは `fragment`, `radical`, `precursor_intermediate`
- `allowed_charges` はまず `0, +1`
- halogenated precursor でもまずは `anion` より `cation + neutral fragment` を優先

## 4. template をどの順に作るか

推奨順は次の 5 段です。

1. `electron_ionization`
2. `electron_dissociation`
3. `radical_neutral_reaction`
4. `ion_neutral_followup`
5. `dissociative_recombination`

今回の実装例:

- ionization: [catalog_53_reactions_electron_ionization_silicon.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_53_reactions_electron_ionization_silicon.yaml#L1)
- dissociation: [catalog_54_reactions_electron_dissociation_silicon.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_54_reactions_electron_dissociation_silicon.yaml#L1)
- radical-neutral: [catalog_55_reactions_radical_neutral_reaction_silicon.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_55_reactions_radical_neutral_reaction_silicon.yaml#L1)
- ion-neutral follow-up: [catalog_58_reactions_ion_neutral_followup_silicon.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_58_reactions_ion_neutral_followup_silicon.yaml#L1)
- dissociative recombination: [catalog_59_reactions_dissociative_recombination_silicon.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_59_reactions_dissociative_recombination_silicon.yaml#L1)

順序の理由:

- まず `SiH4+`, `SiH2Cl2+`, `SiHCl3+` を作って primary plasma activation を置く
- 次に `SiH3`, `SiHCl2`, `SiCl3` を開いて fragment chemistry の入口を作る
- 最後に `+ H` closure を置いて precursor recovery / follow-up をつなぐ

## 5. sample config

family 単体の確認用 config:

- [config_silicon_family_runtime.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/config_silicon_family_runtime.yaml#L1)

この config では次を使います。

- `feeds`: `SiH4`, `SiH2Cl2`, `SiHCl3`, `H2`
- `state_masters`: `core_plasma`, `hydrogen`, `chlorine`, `silicon`
- `catalog_paths`: silicon family template pack

## 6. 次の拡張

次に増やすならこの順が自然です。

1. `SiCl4`, `SiF4`, `TEOS` を含む silicon overlay
2. fragment cation を含む二次分解
3. source-backed template promotion
