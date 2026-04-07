# アーキテクチャ

この版は、**小さい core に対して source を後付けしやすい**ことを最優先にしています。

## 層構成

```text
config.py
  ├─ load_config
  └─ EvidenceSourceSpec / BuildConfig

catalog.py
  ├─ packaged species / reactions
  └─ 外部 YAML catalog の merge

normalization.py
  └─ alias 正規化

source_profiles.py
  └─ source family / default support / priority

adapters/
  ├─ pubchem_identity.py
  ├─ nist_asd.py
  ├─ atct.py
  ├─ nist_kinetics.py
  ├─ qdb_evidence.py
  ├─ umist.py
  ├─ kida.py
  └─ vamdc.py

adapters/reaction_evidence.py
  ├─ kind -> loader registry
  ├─ alias 正規化適用
  └─ source profile による support 補正

builder.py
  ├─ ASD bootstrap
  ├─ evidence seed templates
  ├─ generation expansion
  ├─ ATcT thermochem pruning
  └─ evidence annotation

source_ops.py
  ├─ inspect-sources
  ├─ freeze-pubchem helper
  ├─ evidence manifest
  ├─ evidence merge
  └─ source lock
```

## 今回の整理方針

### 1. build core はできるだけ触らない

新しい DB を足すときは、原則 `adapters/` と `ReactionEvidenceFactory` だけを触ります。

### 2. runtime と運用補助を分ける

- `builder.py` は状態/反応生成に集中
- `source_ops.py` は点検、凍結、lock、差分更新に集中

### 3. alias と source weight を独立させる

外部 source を増やすほど、表記揺れと source 強度差が効いてきます。
そのため、

- `normalization.py`
- `source_profiles.py`

を小さく独立させています。

これにより、DB parser 側は「どう読むか」だけに集中できます。

## 新しい source を追加する手順

最小手順は次の 3 ステップです。

1. `adapters/` に parser を追加
2. `ReactionEvidenceFactory._loaders` に `kind` を追加
3. `data/source_profiles.yaml` に profile を追加

必要なら project 固有 alias を `alias_path` に追加します。

## なぜ lock を別コマンドにしたか

build 自体に lock の細かい制御を埋め込むと CLI が重くなります。
そこで、

- `inspect-sources`
- `write-lock`

を独立させ、必要なときだけ詳細点検と記録を行う設計にしています。

## なぜ差分更新を `merge` に留めたか

自動更新を強くしすぎると、source ごとの更新ロジックが入り乱れて保守しづらくなります。
そこで今回は、

- PubChem は `--only-missing`
- evidence は `--merge`

という**単純な差分更新**に留めています。

このレベルでも、普段の更新運用では十分効果があります。


## visualization 層

可視化は `src/plasma_reaction_builder/visualization/` に切り出しています。

- `core.py`
  - registry / context / manifest
- `network_views.py`
  - DAG / summary figure
- `table_views.py`
  - ページ化 table と CSV export
- `utils.py`
  - layout / table render / color helper

新しい view は registry に 1 件増やすだけで追加できます。
