# source 更新レシピ

この文書は、source を**全部取り直さずに**更新するための最小レシピです。

## PubChem identity

### 初回作成

```bash
plasma-rxn-builder freeze-pubchem \
  examples/config.yaml \
  --output examples/pubchem_identity_frozen.json
```

### 不足分だけ追加

```bash
plasma-rxn-builder freeze-pubchem \
  examples/config.yaml \
  --live \
  --existing examples/pubchem_identity_frozen.json \
  --only-missing \
  --output examples/pubchem_identity_frozen.json
```

使いどころ:

- feed を 1 種だけ追加した
- 既存 snapshot はそのまま使いたい

## evidence snapshot

### 再収集

```bash
plasma-rxn-builder collect-evidence \
  examples/config.yaml \
  --output examples/combined_evidence_snapshot.json
```

### 差分マージ

```bash
plasma-rxn-builder collect-evidence \
  examples/config.yaml \
  --existing examples/combined_evidence_snapshot.json \
  --merge \
  --output examples/combined_evidence_snapshot.json
```

この merge は、

- `source_system`
- `source_name`
- `reactants`
- `products`
- `citation`
- `source_url`

の組をキーにして重複除去します。

## lock 更新

```bash
plasma-rxn-builder write-lock \
  examples/config.yaml \
  --output examples/source_lock.json
```

更新タイミング:

- snapshot を差し替えた
- alias を変えた
- VAMDC query を変えた
- source profile を上書きした

## VAMDC live の点検

```bash
plasma-rxn-builder inspect-sources \
  examples/config.yaml \
  --head-vamdc \
  --output examples/source_inspection.json
```

確認ポイント:

- query が正しく展開されているか
- `VAMDC-COUNT-*` ヘッダが取れるか
- `Last-Modified` / `ETag` が返るか

## alias を足す

`examples/aliases.yaml` のように書きます。

```yaml
aliases:
  C4F8: c-C4F8
  C4F8-: c-C4F8-
```

追加後は lock を更新し、必要なら evidence snapshot を再収集します。

## source profile を調整する

project 固有で support の既定値を変えたい場合だけ使います。

```yaml
profiles:
  - source_id: umist
    family: astrochemistry
    default_support: 0.45
    priority: 25
```

その場合は config に

```yaml
source_profiles_path: source_profiles_override.yaml
```

を追加します。
