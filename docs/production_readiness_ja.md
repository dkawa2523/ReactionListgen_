# 本番化準備: 取得棚卸し・未取得項目・テンプレート昇格フロー

## 1. 現在の取得済み範囲の棚卸し

### 1.1 全体サマリ

現時点で実装済みなのは、以下の 3 層です。

1. 外部 DB / 外部ファイルからの取得・読込アダプタ
2. サンプルスナップショットを使った build 可能な検証経路
3. CH4 系および c-C4F8 系の curated state / reaction template

本番用としては「取得基盤はあるが、取得カバレッジと curated 資産はまだ限定的」という状態です。

### 1.2 状態データの棚卸し

| 区分 | 現在の取得状況 | 件数 / 範囲 | 本番化判定 |
| --- | --- | --- | --- |
| curated species library | 実装済み | 36 species | 部分完了 |
| state_class 内訳 | ground 14 / cation 11 / anion 6 / atom 3 / excited 2 | `species_library.yaml` | 部分完了 |
| PubChem identity snapshot | 取得済み | 2 entries | サンプル完了 |
| NIST ASD export | 取得済み | 4 spectra / 13 levels / bootstrap 12 species | サンプル完了 |
| ATcT thermochemistry | 取得済み | 7 entries | サンプル完了 |
| 価数レンジ | 実質的には 0, +/-1 中心 | +/-2 は未整備 | 未完 |
| 励起種 | CH4 の振動励起と ASD 由来原子状態のみ | 分子励起・イオン励起は限定的 | 未完 |

### 1.3 反応証拠データの棚卸し

| ソース | 取得経路 | 現在の状態 | 件数 | 本番化判定 |
| --- | --- | --- | --- | --- |
| PubChem | snapshot / live API | 読込可能 | 2 | サンプル完了 |
| NIST ASD | local CSV export | 読込可能 | 4 spectra | サンプル完了 |
| ATcT | local CSV snapshot | 読込可能 | 7 | サンプル完了 |
| NIST Chemical Kinetics | normalized snapshot JSON | 読込可能 | 2 records | サンプル完了 |
| QDB | normalized snapshot JSON | 読込可能 | 3 records | サンプル完了 |
| UMIST | official rate file | 読込可能 | 2 records | サンプル完了 |
| KIDA | official network file | 読込可能 | 2 records | サンプル完了 |
| VAMDC / IDEADB | XSAMS snapshot | 読込可能 | 1 record | サンプル完了 |

### 1.4 curated 反応テンプレートの棚卸し

| ライブラリ | テンプレート数 | 主な family | 本番化判定 |
| --- | --- | --- | --- |
| CH4 | 16 | electron_attachment / electron_ionization / electron_dissociation / electron_excitation_vibrational / ion_fragmentation / radical_fragmentation | 部分完了 |
| c-C4F8 | 15 | electron_attachment / electron_dissociative_ionization / neutral_fragmentation / radical_fragmentation / ion_neutral_followup | 部分完了 |
| 合計 | 31 | 2 系統のみ | 未完 |

### 1.5 build 観点の棚卸し

| 項目 | 現在の状態 |
| --- | --- |
| configured feeds | 2 feeds: CH4, c-C4F8 |
| evidence sources ready | 5 / 5 |
| evidence manifest | total 10 records |
| example build result | 40 species / 32 reactions |
| source traceability | lock / manifest / inspection あり |
| production breadth | なし。検証対象が CH4 / c-C4F8 に偏る |

## 2. 本番化に必要な未取得項目一覧

### 2.1 状態側の未取得

#### 必須

- 化学ファミリごとの初期 state マスタ
  - hydrocarbon
  - fluorocarbon
  - oxygen
  - nitrogen
  - hydrogen
  - halogen
  - inert gas
- 価数 `-2 〜 +2` の state 拡張
  - 既存資産はほぼ `0, +/-1`
- 共通原子・分子フラグメントの整備
  - C, H, O, N, F, Cl, Br 系の atom / radical / cation / anion
- 励起種ポリシーに沿った state 取得
  - 原子励起
  - 分子振動励起
  - 電子励起
  - 必要なら準安定種

#### 任意だが本番で重要

- 不純物標準セット
  - H2O, O2, N2, CO, CO2
- alias の本番用辞書
  - isomer
  - structural name
  - DB 表記ゆれ

### 2.2 反応証拠側の未取得

#### 必須

- サンプルではなく本番対象ガス群に対する source 別スナップショット
- VAMDC live を含む bulk acquisition 設計
- source ごとの取得条件記録
  - query
  - version
  - date
  - node / endpoint
- cross-source 重複統合ルール
- state / reaction の canonicalization ルール拡張

#### 任意だが本番で重要

- source ごとの coverage 指標
- source 間の矛盾検出
- threshold / thermochemistry の補完率レポート

### 2.3 テンプレート側の未取得

#### 必須

- CH4, c-C4F8 以外の chemistry-family curated templates
- 本番で必要な family の追加
  - electron_excitation
  - electron_detachment
  - dissociative_recombination
  - ion_ion_neutralization
  - charge_transfer
  - ion_neutral_reaction
  - radical_neutral_reaction
  - associative_ionization
- `required_projectile = e-` 以外のテンプレート戦略
  - 現状は電子衝突中心
- `-2 〜 +2` charge window を持つテンプレート標準
- source evidence から curated template へ昇格する審査基準

#### 今回は除外

- 表面反応
- 壁損失
- 3 体反応

## 3. DB 取得後にテンプレートへ昇格させる判定フロー

以下は本番用の標準フローです。

### 3.1 ステージ定義

| ステージ | 名前 | 内容 |
| --- | --- | --- |
| S0 | raw acquired | DB / file から取得した未整形データ |
| S1 | normalized evidence | reactants / products / source metadata を正規化した record |
| S2 | canonical matched | species alias, formula, charge を canonical key に変換済み |
| S3 | promotable candidate | バランス・除外条件・重複統合を通過した候補 |
| S4 | curated template | human review または自動昇格基準を満たした template |

### 3.2 判定フロー

1. source 取得
   - source ごとに raw payload を保存する
   - query, endpoint, retrieved_at, source version を記録する
2. normalized evidence 化
   - `reactants`, `products`, `source_system`, `citation`, `support_score` を抽出する
   - source 固有の schema はこの段階で吸収する
3. canonical species 化
   - alias 解決
   - isomer 名統一
   - charge 記法統一
   - formula と label の整合確認
4. 除外条件チェック
   - 表面反応を除外
   - 壁損失を除外
   - 3 体反応を除外
   - species 不明で補完不能なものを保留
5. 反応成立性チェック
   - 質量保存
   - 電荷保存
   - projectile の整合
   - charge range `-2 〜 +2` 以内
6. family 分類
   - electron_attachment
   - electron_dissociation
   - electron_ionization
   - ion_fragmentation
   - charge_transfer
   - recombination
   - などへ分類
7. source 統合
   - 同一反応式を source 横断で集約
   - 逆反応は別 candidate として扱う
   - source 数、優先 source、support の分布を付与する
8. 昇格判定
   - 下記の昇格条件を満たす場合に template 候補にする
9. curated 化
   - `key`
   - `family`
   - `required_projectile`
   - `threshold_ev`
   - `base_confidence`
   - `reference_ids`
   - `note`
   - `missing_products`
   を確定して YAML 化する
10. build 回帰確認
   - build
   - manifest
   - visualization
   - reaction explosion の有無
   - 重要チャネル保持

### 3.3 自動昇格条件

#### 昇格可

- canonical 化後に species が解決可能
- 質量・電荷保存が取れる
- 除外対象ではない
- family 分類が確定できる
- 少なくとも 1 source に直接根拠がある
- source metadata を保持できる

#### 強昇格

- 複数 source で同一方向の反応が確認できる
- threshold または thermochemistry が取得できる
- 既存 curated family と矛盾しない
- 本番対象 chemistry-family の主要チャネルである

#### 保留

- species が未定義
- charge state が policy 外
- 生成物が省略されていて `missing_products` 補完が必要
- source はあるが逆反応か順反応か曖昧
- DB 間で競合がある

#### 却下

- 表面 / 壁 / 3 体反応
- 質量・電荷不整合
- canonicalization 不能
- source traceability を残せない

### 3.4 curated template 化するときの必須属性

- `key`
- `family`
- `reactants`
- `products`
- `lhs_tokens`
- `rhs_tokens`
- `required_projectile`
- `threshold_ev`
- `base_confidence`
- `reference_ids`
- `note`
- `inferred_balance`
- `missing_products`
- 将来追加候補: `charge_window_min`, `charge_window_max`, `source_count`

## 4. 次の具体アクション

1. chemistry-family 一覧を確定する
2. family ごとの初期 state マスタを作る
3. source ごとの bulk acquisition recipe を作る
4. S0 -> S4 昇格フローに沿って curated candidate を生成する
5. curated candidate から production library を分割配置する

## 5. 現時点でまだ必要な追加情報

- 優先して本番化する chemistry-family
- 標準で含める不純物セット
- 励起種の深さ
  - 代表励起のみ
  - 広く保持する
- `projectiles` を電子のみで開始するか
  - それともイオン・準安定種も初期対象に含めるか

## 6. 関連資料

- `docs/production_catalog_design_ja.md`
  - chemistry-family 一覧
  - `-2 .. +2` を含む state マスタ設計
  - template YAML 分割案
- `examples/production_blueprint/`
  - 設計ブループリント YAML
