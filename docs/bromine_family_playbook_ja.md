# Bromine Family プレイブック

## 1. 対象

`bromine family` を最小構成で追加するときの具体例です。今回の対象は次の 3 種です。

- `Br`
- `Br2`
- `HBr`

補助 family:

- `hydrogen`
- `core_plasma`

## 2. どの DB から何を取るか

| DB / source | 取るもの | bromine family での用途 |
| --- | --- | --- |
| `PubChem` | formula, synonym, CID | `Br2`, `HBr` の canonical key と alias 整理 |
| `ATcT` | 熱化学 | `Br`, `H`, `HBr` を含む反応の sanity check |
| `QDB` | 電子衝突 evidence | `electron_attachment`, `electron_ionization`, `electron_dissociation` の優先根拠 |
| `NIST Chemical Kinetics` | 気相反応 evidence | `Br + H2 -> HBr + H` のような follow-up の根拠 |
| `UMIST`, `KIDA` | ラジカル・中性反応 | neutral / radical follow-up の補強 |
| `VAMDC`, `IDEADB` | 付着・状態ラベル | DEA や label variation の補助 evidence |

## 3. state_master をどう書くか

最初に入れるべき親状態は `Br`, `Br2`, `HBr` です。実装済みの blueprint では次を使えます。

- `Br`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L430)
- `Br2`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L445)
- `HBr`: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L460)

設計方針:

- `allowed_charges` はまず `-1, 0, +1`
- `Br` は atom / fragment として保持
- `Br2`, `HBr` は `feed_candidate`
- 励起状態は bromine family 単体ではまだ持たず、まず charge と fragment を優先

## 4. template をどの順に作るか

推奨順は次の 6 段です。

1. `electron_attachment`
2. `electron_ionization`
3. `electron_dissociation`
4. `radical_neutral_reaction`
5. `ion_neutral_followup`
6. `dissociative_recombination`

今回の実装例:

- attachment: [catalog_49_reactions_electron_attachment_bromine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_49_reactions_electron_attachment_bromine.yaml#L1)
- ionization: [catalog_50_reactions_electron_ionization_bromine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_50_reactions_electron_ionization_bromine.yaml#L1)
- dissociation: [catalog_51_reactions_electron_dissociation_bromine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_51_reactions_electron_dissociation_bromine.yaml#L1)
- radical-neutral: [catalog_52_reactions_radical_neutral_reaction_bromine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_52_reactions_radical_neutral_reaction_bromine.yaml#L1)
- ion-neutral follow-up: [catalog_56_reactions_ion_neutral_followup_bromine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_56_reactions_ion_neutral_followup_bromine.yaml#L1)
- dissociative recombination: [catalog_57_reactions_dissociative_recombination_bromine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_57_reactions_dissociative_recombination_bromine.yaml#L1)

順序の理由:

- まず `Br2-`, `Br2+`, `HBr+` を作って charge channel を閉じる
- 次に `Br`, `H` を作って fragment pool を開く
- 最後に `Br + H2 -> HBr + H` と `H + Br2 -> HBr + Br` で chain propagation をつなぐ

## 5. sample config

family 単体の確認用 config:

- [config_bromine_family_runtime.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/config_bromine_family_runtime.yaml#L1)

この config では次を使います。

- `feeds`: `Br2`, `HBr`, `H2`
- `state_masters`: `core_plasma`, `hydrogen`, `bromine`
- `catalog_paths`: bromine family template pack

## 6. 次の拡張

次に増やすならこの順が自然です。

1. `BBr3` や mixed halogen gas を含む halogen overlay
2. excited-state / metastable label の導入
3. source-backed template promotion
