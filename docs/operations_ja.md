# 運用ガイド

この版の運用は、**点検 → 凍結/収集 → lock 作成 → build** の 4 段階です。

## 1. source を点検する

```bash
plasma-rxn-builder inspect-sources examples/config.yaml --output examples/source_inspection.json
```

確認できる内容:

- PubChem snapshot の有無と件数
- NIST ASD export の有無、更新時刻、SHA-256
- ATcT snapshot の有無、件数
- reaction evidence source ごとの record 数
- VAMDC live query の展開結果
- `next_step` による更新アクション

VAMDC live を使う場合は preflight を付けます。

```bash
plasma-rxn-builder inspect-sources examples/config.yaml --head-vamdc --output examples/source_inspection.json
```

## 2. identity / evidence を凍結する

### PubChem

```bash
plasma-rxn-builder freeze-pubchem \
  examples/config.yaml \
  --output examples/pubchem_identity_frozen.json
```

不足分だけ更新したい場合:

```bash
plasma-rxn-builder freeze-pubchem \
  examples/config.yaml \
  --live \
  --existing examples/pubchem_identity_frozen.json \
  --only-missing \
  --output examples/pubchem_identity_frozen.json
```

### reaction evidence

```bash
plasma-rxn-builder collect-evidence \
  examples/config.yaml \
  --output examples/combined_evidence_snapshot.json
```

既存 snapshot に差分マージする場合:

```bash
plasma-rxn-builder collect-evidence \
  examples/config.yaml \
  --existing examples/combined_evidence_snapshot.json \
  --merge \
  --output examples/combined_evidence_snapshot.json
```

## 3. lock file を作る

```bash
plasma-rxn-builder write-lock \
  examples/config.yaml \
  --output examples/source_lock.json
```

lock に含まれる内容:

- package version
- config path / config SHA-256
- feed / projectiles / libraries
- alias_path / source_profiles_path
- source 点検結果
- evidence manifest

## 4. build

```bash
plasma-rxn-builder build \
  examples/config.yaml \
  --output examples/output_network.json \
  --lock-output examples/build_lock.json
```

`output_network.json` には、build に使われた source manifest と config hash も metadata に含まれます。

## 典型運用

### 初回

1. `validate-config`
2. `inspect-sources`
3. `freeze-pubchem`
4. `collect-evidence`
5. `write-lock`
6. `build`

### 更新時

1. `inspect-sources`
2. 必要 source だけ更新
3. `freeze-pubchem --existing --only-missing`
4. `collect-evidence --existing --merge`
5. `write-lock`
6. `build`

## 迷いやすい点

### alias はいつ使うか

外部 source が `C4F8`、内部 key が `c-C4F8` のようにずれるときに使います。
`examples/aliases.yaml` が最小例です。

### source profile はいつ上書きするか

通常は packaged profile のままで十分です。
特定の project で source 重みを調整したいときだけ `source_profiles_path` を使います。

### lock はいつ更新するか

- source file を差し替えたとき
- config を変更したとき
- VAMDC live query を変えたとき

その build を再現したいなら、build ごとに lock を残す運用が安全です。


## 5. 可視化

```bash
plasma-rxn-builder visualize \
  examples/output_network.json \
  --config examples/config.yaml \
  --output-dir examples/visuals
```

生成されるもの:

- engineer / plasma / datasci 用の figure
- 生成状態/反応リストのページ画像
- 現在の状態辞書/反応辞書のページ画像
- 同内容の CSV
- `visual_manifest.json`

`--views engineer` のように audience 単位、または `--views engineer_process_dag` のように view id 単位で絞れます。
