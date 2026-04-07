# Chlorine Family 作成プレイブック

## 1. 目的

この資料は、`chlorine family` を具体例にして

- どのDBから何を取るか
- `state_master` をどう書くか
- template をどの順に作るか

を、**このコードベースの実ファイルに合わせて**落としたものです。

対象 family:

- `chlorine`

対象ガス:

- `Cl`
- `Cl2`
- `HCl`

補助 family:

- `hydrogen`
- `core_plasma`

## 2. DBごとの役割

### 2.1 まず使うDB

| DB / source | 取るもの | chlorine family での使い道 |
| --- | --- | --- |
| `PubChem` | 分子名、formula、synonym、構造名 | `Cl2`, `HCl` の canonical 化、alias 整理 |
| `ATcT` | 熱化学 | `Cl`, `HCl` を含む反応の endothermic sanity check |
| `QDB` | 電子衝突系 reaction evidence | `electron_attachment`, `electron_ionization`, `electron_dissociation` の根拠候補 |
| `NIST Chemical Kinetics` | 気相 reaction evidence | `H + Cl2 -> HCl + Cl`、`Cl + H2 -> HCl + H` などの follow-up 候補 |
| `UMIST`, `KIDA` | ラジカル・中性反応補完 | 中性 / ラジカル follow-up の補助根拠 |
| `VAMDC`, `IDEADB` | 付着・衝突・state label | DEAや label variation がある場合の補助 evidence |

### 2.2 DBごとに何を実際に取るか

#### `PubChem`

最低限取る対象:

- `Cl2`
- `HCl`

取りたい属性:

- `title`
- `formula`
- `synonyms`
- `CID`
- `SMILES / InChI / InChIKey`

使い方:

- `preferred_key` と `aliases` の候補にする
- `chlorine` / `hydrogen_chloride` の display 名を整える

#### `ATcT`

最低限取る対象:

- `Cl`
- `H`
- `HCl`

使い方:

- `H + Cl2 -> HCl + Cl`
- `Cl + H2 -> HCl + H`

のような neutral / radical channel の熱的に無理がないかを見る

#### `QDB`

最低限拾いたい channel:

- `e- + Cl2 -> Cl2-`
- `e- + Cl2 -> Cl + Cl + e-`
- `e- + Cl2 -> Cl2+ + 2e-`
- `e- + HCl -> HCl-`
- `e- + HCl -> H + Cl + e-`
- `e- + HCl -> HCl+ + 2e-`

使い方:

- 最初の curated template 候補を作る primary source

#### `NIST Chemical Kinetics`, `UMIST`, `KIDA`

最低限拾きたい channel:

- `Cl + H2 -> HCl + H`
- `H + Cl2 -> HCl + Cl`

使い方:

- `radical_neutral_reaction` の根拠 source
- QDB にない neutral follow-up を補完

## 3. state_master をどう書くか

### 3.1 最小構成

`chlorine family` 単体なら、まず必要なのは次の3つです。

1. `Cl`
2. `Cl2`
3. `HCl`

すでに blueprint には入っています。

- `Cl` の定義: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L385)
- `Cl2` の定義: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L400)
- `HCl` の定義: [state_master_base.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/state_master_base.yaml#L415)

### 3.2 実際の書き方

考え方:

- 原子種は `core atom`
- 親ガスは `feed_candidate`
- `allowed_charges` はまず `-1, 0, +1`
- `excitation_policy` は chlorine ではまず `none`
- `required_sources` は、原子なら `atct`、親ガスなら `pubchem, qdb`

例:

```yaml
state_master:
  - family: chlorine
    species_id: chlorine_atom
    preferred_key: Cl
    display_name: Chlorine atom
    formula: Cl
    aliases: [Cl_atom]
    tags: [core, atom, chlorine]
    allowed_charges: [-1, 0, 1]
    charge_window_min: -2
    charge_window_max: 2
    excitation_policy: none
    priority: 90
    required_sources: [atct]
    enabled: true

  - family: chlorine
    species_id: chlorine_molecule
    preferred_key: Cl2
    display_name: Chlorine
    formula: Cl2
    aliases: [chlorine]
    tags: [feed_candidate, chlorine, etch_gas]
    allowed_charges: [-1, 0, 1]
    charge_window_min: -2
    charge_window_max: 2
    excitation_policy: none
    priority: 99
    required_sources: [pubchem, qdb]
    enabled: true

  - family: chlorine
    species_id: hydrogen_chloride
    preferred_key: HCl
    display_name: Hydrogen chloride
    formula: HCl
    aliases: [hydrogen_chloride]
    tags: [feed_candidate, chlorine, etch_gas, clean_gas]
    allowed_charges: [-1, 0, 1]
    charge_window_min: -2
    charge_window_max: 2
    excitation_policy: none
    priority: 98
    required_sources: [pubchem, qdb]
    enabled: true
```

### 3.3 なぜこの書き方か

- `Cl` は fragment / product として頻出するので原子単体を持つ
- `Cl2` は親ガスとして attachment / ionization / dissociation の基点になる
- `HCl` は etch / clean 両方で出やすく、`Cl + H2` 系の中間出力にもなる
- 最初から excited state を入れず、まず `charge` と `fragment` を優先する

## 4. template をどの順に作るか

### 4.1 作成順

`chlorine family` では、次の順番が安全です。

1. `electron_attachment`
2. `electron_ionization`
3. `electron_dissociation`
4. `radical_neutral_reaction`
5. `ion_neutral_followup`
6. `dissociative_recombination`

理由:

- まず親ガスから **アニオン / カチオン / 原子フラグメント** を出せるようにする
- その後に、生成した `Cl` や `H` を使う neutral follow-up を入れる

### 4.2 今回追加した具体ファイル

- attachment: [catalog_45_reactions_electron_attachment_chlorine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_45_reactions_electron_attachment_chlorine.yaml#L1)
- ionization: [catalog_46_reactions_electron_ionization_chlorine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_46_reactions_electron_ionization_chlorine.yaml#L1)
- dissociation: [catalog_47_reactions_electron_dissociation_chlorine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_47_reactions_electron_dissociation_chlorine.yaml#L1)
- radical-neutral: [catalog_48_reactions_radical_neutral_reaction_chlorine.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/catalog_48_reactions_radical_neutral_reaction_chlorine.yaml#L1)

### 4.3 各段階で何を作るか

#### 1. `electron_attachment`

最初に作るもの:

- `e- + Cl2 -> Cl2-`
- `e- + HCl -> HCl-`

狙い:

- electronegative gas の基本挙動を先に入れる
- `charge_window` で anion の挙動を確認しやすい

#### 2. `electron_ionization`

次に作るもの:

- `e- + Cl2 -> Cl2+ + 2e-`
- `e- + HCl -> HCl+ + 2e-`

狙い:

- parent cation を先に作る
- 後続の ion-neutral をつなぎやすくする

#### 3. `electron_dissociation`

次に作るもの:

- `e- + Cl2 -> Cl + Cl + e-`
- `e- + HCl -> H + Cl + e-`

狙い:

- `Cl` と `H` を network に供給する
- radical-neutral family の入口を作る

#### 4. `radical_neutral_reaction`

この段階で作るもの:

- `Cl + H2 -> HCl + H`
- `H + Cl2 -> HCl + Cl`

狙い:

- ガス相 chain propagation を作る
- parent gas と fragment の相互接続を作る

#### 5. `ion_neutral_followup`

あとから作る候補:

- `Cl2+ + H2 -> HCl + Cl+ + H`
- `HCl+ + Cl2 -> Cl2+ + HCl`

狙い:

- cation 生成後の secondary chemistry を足す

ただし:

- ここは evidence が薄い場合が多いので、QDB / kinetics / literature の裏付け後が安全

#### 6. `dissociative_recombination`

最後に足す候補:

- `Cl2+ + e- -> Cl + Cl`
- `HCl+ + e- -> H + Cl`

狙い:

- ion channel を閉じる
- charge balance の出口を作る

## 5. sample config ではどう読むか

今回、`chlorine family` 用の sample config も追加しています。

- [config_chlorine_family_runtime.yaml](/c:/Users/user/Desktop/prb_v10_visuals/examples/production_blueprint/config_chlorine_family_runtime.yaml#L1)

この config は

- `feeds`: `Cl2`, `HCl`, `H2`
- `state_masters`: `core_plasma`, `hydrogen`, `chlorine`
- `catalog_paths`: chlorine family template pack

だけを読みます。

## 6. 実務フロー

実際に新 family を追加するときは、次の順に進めるのが一番事故が少ないです。

1. `state_master` に parent / atom / primary charge state を追加
2. `PubChem` で alias と formula を確定
3. `QDB` で electron-impact channel を拾う
4. `NIST kinetics / UMIST / KIDA` で neutral follow-up を拾う
5. `reactions_electron_*_<family>.yaml` を先に作る
6. build で species / reaction explosion を確認
7. その後に `ion_neutral_followup` と `recombination` を足す

## 7. 今回の例から他 family へ横展開するとき

この `chlorine family` 例は、そのまま

- `bromine family`
- `silicon family`
- `sulfur family`

にも横展開できます。

置き換えるだけの要素:

- 親ガス
- primary fragment
- 主要 anion / cation
- 補助 source

変えずに流用できる要素:

- `state_master` の書式
- template の作成順
- sample config の切り方
- validation の流れ
