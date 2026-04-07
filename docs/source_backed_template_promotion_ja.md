# source-backed template promotion 設計

## 1. 目的

`source-backed template promotion` は、外部 evidence にある反応をそのまま generic family に落とすのではなく、
既存の curated chemistry-family pack に沿った `ReactionTemplate` として catalog に昇格する仕組みです。

今回の実装では、`bromine` と `silicon` family に対して、

- `ion_neutral_followup`
- `dissociative_recombination`
- `radical_neutral_reaction`

の一部を source-backed に追加できるようにしています。

## 2. config

新しい設定は `template_promotions.source_backed_templates` です。

主な項目:

- `enabled`
- `source_systems`
- `target_families`
- `allowed_reaction_families`
- `min_support_score`
- `max_templates_per_family`
- `require_catalog_species`

## 3. 昇格条件

外部 evidence entry は次の条件を満たすと template に昇格します。

1. `source_system` が許可されている
2. `support_score` が閾値以上
3. `process_family` などから curated reaction family へ解決できる
4. `promotion_family` か state_master overlap から chemistry-family を決められる
5. 反応式が balanced
6. 反応に出てくる tracked species が catalog に存在する
7. 既存 curated template と equation 重複しない

## 4. 今回の sample

- bromine promotion config: [config_bromine_family_promotion_runtime.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/config_bromine_family_promotion_runtime.yaml#L1)
- silicon promotion config: [config_silicon_family_promotion_runtime.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/config_silicon_family_promotion_runtime.yaml#L1)
- multi-family promotion config: [config_multi_family_template_promotion_runtime.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/config_multi_family_template_promotion_runtime.yaml#L1)
- halogen / fluorocarbon promotion config: [config_halogen_fluorocarbon_template_promotion_runtime.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/config_halogen_fluorocarbon_template_promotion_runtime.yaml#L1)
- bromine evidence snapshot: [qdb_bromine_template_promotion_snapshot.json](/c:/Users/user/Desktop/prb_v10_visuals/examples/snapshots/qdb_bromine_template_promotion_snapshot.json#L1)
- silicon evidence snapshot: [qdb_silicon_template_promotion_snapshot.json](/c:/Users/user/Desktop/prb_v10_visuals/examples/snapshots/qdb_silicon_template_promotion_snapshot.json#L1)
- multi-family evidence snapshot: [qdb_multi_family_template_promotion_snapshot.json](/c:/Users/user/Desktop/prb_v10_visuals/examples/snapshots/qdb_multi_family_template_promotion_snapshot.json#L1)
- halogen / fluorocarbon evidence snapshot: [qdb_halogen_fluorocarbon_template_promotion_snapshot.json](/c:/Users/user/Desktop/prb_v10_visuals/examples/snapshots/qdb_halogen_fluorocarbon_template_promotion_snapshot.json#L1)

## 5. runtime 接続点

runtime では、

1. catalog を組み立てる
2. alias / source profile / evidence index を読む
3. `molecular_excited_state promotion` を必要なら適用する
4. `source_backed template promotion` を適用して catalog に merge する

という順で処理します。

## 6. 今後の拡張

- `source-backed` から `reference_ids` を自動付与する
- family ごとに promotion policy を切り替える
- promoted template を lock / manifest に明示記録する
