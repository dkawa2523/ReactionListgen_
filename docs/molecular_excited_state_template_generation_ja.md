# molecular excited-state template generation 設計

## 1. 目的

`molecular excited-state template generation` は、外部 evidence から昇格した molecular excited species を
species のままで止めず、runtime catalog で使える `ReactionTemplate` に自動展開する仕組みです。

今回の実装では、promoted state から次を生成します。

- `electron_excitation`
- `electron_excitation_vibrational`
- `radiative_relaxation`
- `collisional_quenching`
- `superelastic_deexcitation`

## 2. config

設定は `template_promotions.molecular_excited_state_templates` です。

主な項目:

- `enabled`
- `source_systems`
- `target_families`
- `min_support_score`
- `include_electron_excitation`
- `include_radiative_relaxation`
- `include_collisional_quenching`
- `include_superelastic_deexcitation`
- `quenching_partners`

## 3. 生成条件

template は次の条件を満たす promoted species から生成されます。

1. `promotion_kind == molecular_excited_state`
2. `source_system` が許可リスト内
3. `support_score` が閾値以上
4. `base_species_key` が catalog に存在する
5. family が target scope に入る

## 4. family 判定

family は基本的に `state_master` の `preferred_key -> family` を使って解決します。
fallback として species `tags` も見ます。

## 5. reaction family 判定

- label が `V...` なら `electron_excitation_vibrational`
- それ以外は `electron_excitation`
- 緩和は `radiative_relaxation`
- quenching は `collisional_quenching`
- 電子との逆過程は `superelastic_deexcitation`

## 6. sample

- config: [config_state_promotion_template_runtime.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/config_state_promotion_template_runtime.yaml#L1)
- source snapshot: [qdb_molecular_excited_snapshot.json](/c:/Users/user/Desktop/prb_v10_visuals/examples/snapshots/qdb_molecular_excited_snapshot.json#L1)

この sample では `CH4[V14]`, `O2[c1Sigma_u_minus]`, `N2[B3Pi_g]` から
対応する excitation / relaxation / quenching / superelastic template を自動生成します。
