# 可視化ガイド

この版の可視化は、**build 済みネットワーク**と**現在の状態/反応辞書**を、役割別に読みやすく出すためのものです。

## 役割別ビュー

### 半導体エンジニア向け

- `engineer_process_dag`
  - feed gas から fragment / ion / radical へどう枝分かれしたかを generation DAG で見せます。
  - 色は species role、横方向は generation です。
- `engineer_inventory_summary`
  - 状態 role 数、反応 family 数、主要 hub species をまとめます。

### プラズマ物理学者向け

- `plasma_bipartite_dag`
  - reaction node を残した DAG です。
  - 種ノードは charge / excitation 系、反応ノードは family で色分けします。
- `plasma_threshold_map`
  - generation ごとの threshold と thermochemistry annotation の入り方を見ます。

### データサイエンティスト向け

- `datasci_dataset_summary`
  - evidence source、field coverage、confidence tier、family count をまとめます。
- `generated_*_pages`
  - 生成状態/反応リストのページ画像と CSV です。
- `dictionary_*_pages`
  - 現在の状態辞書/反応辞書のページ画像と CSV です。

## 実行方法

```bash
plasma-rxn-builder visualize \
  examples/output_network.json \
  --config examples/config.yaml \
  --output-dir examples/visuals
```

特定 audience だけ出したい場合:

```bash
plasma-rxn-builder visualize \
  examples/output_network.json \
  --config examples/config.yaml \
  --output-dir examples/visuals_engineer \
  --views engineer
```

特定 view id だけ出したい場合:

```bash
plasma-rxn-builder visualize \
  examples/output_network.json \
  --config examples/config.yaml \
  --output-dir examples/visuals_tables \
  --views generated_state_pages generated_reaction_pages
```

## 出力構成

- `network/`
  - DAG や summary figure
- `tables/`
  - ページ化した表画像
- `lists/`
  - CSV export
- `visual_manifest.json`
  - 生成 artifact の一覧

## 追加方法

追加口は 1 つです。

1. `visualization/network_views.py` または `visualization/table_views.py` に関数を追加
2. `@register_view(...)` を付ける
3. `FigureArtifact` を返す

renderer 関数は `VisualizationContext` を受け取り、**network が必要か、catalog が必要か**だけを見れば済みます。

## 編集しやすさのための設計

- core では registry と manifest だけを管理
- network 系と table 系を分離
- current dictionary は build 本体ではなく catalog からそのまま読む
- CSV export を常に同時に出して、画像だけでは不足する detail を補う
