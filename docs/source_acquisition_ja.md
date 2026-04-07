# source 取得方針

この版の取得方針は、**build 時に brittle な live scraping を増やさない**ことです。

## 1. snapshot first

原則として次を優先します。

- PubChem: identity snapshot
- NIST ASD: export CSV
- ATcT: snapshot CSV
- NIST Chemical Kinetics: normalized snapshot JSON
- QDB: normalized snapshot JSON
- UMIST: official rate file
- KIDA: official network file
- VAMDC: live query も可。ただし preflight を推奨

## 2. live を許す source

### PubChem

- 用途: feed identity の canonicalization
- live 利用: `freeze-pubchem --live`
- 通常 build: frozen snapshot を推奨

### VAMDC

- 用途: collision/state evidence
- live 利用: `vamdc_live`
- 通常 build: node の安定性と rights を確認した上で使う

## 3. local snapshot を推奨する source

### NIST ASD

- 用途: atomic / atomic-ion states
- 入力: export CSV
- build 時は local file のみ

### ATcT

- 用途: thermochem pruning
- 入力: snapshot CSV
- build 時は local file のみ

### NIST Chemical Kinetics / QDB / UMIST / KIDA

- 用途: reaction existence evidence / template seed
- 入力: normalized JSON または official file
- build 時は local file のみ

## 4. why

理由は 3 つです。

1. build の再現性を保ちたい
2. source 側の schema 変更で build が壊れにくくしたい
3. rights と配布運用を分けやすくしたい

## 5. 追加 source の判断基準

新しい DB を足すときは、まず次を決めます。

- build 中に live で使うか
- 事前収集して snapshot 化するか
- alias が必要か
- source profile をどう置くか

判断に迷ったら、まずは **snapshot 化して local file import** に寄せるのが安全です。
