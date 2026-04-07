# 現在登録済み Species / Ion 棚卸し

## 1. 前提

この資料は、現在の実装で最も代表的な runtime 構成である
[`examples/production_blueprint/config_state_master_runtime.yaml`](../examples/production_blueprint/config_state_master_runtime.yaml)
を基準にまとめています。

- `state_master` 有効
- `charge_window = -1 .. +1`
- `atomic_asd` 有効
- `molecular excited-state promotion` は未適用

この条件での runtime species 総数は **73 species** です。

補足:

- パッケージ同梱 curated species は別に **36 species** あります。
- `config_state_promotion_runtime.yaml` を使うと、追加で
  `CH4[V14]`, `O2[c1Sigma_u_minus]`, `N2[B3Pi_g]`
  のような promoted excited state が catalog に入ります。

## 2. 現在登録済み Species を Family 別に一覧化

### 2.1 実装済み family

| family | 種数 | 現在登録されている主な species |
| --- | ---: | --- |
| `core_plasma` | 21 | `C+[2P_3/2]`, `C+[4P_1/2]`, `C[1D_2]`, `C[3P_1]`, `F[2P_1/2]`, `F[4P_5/2]`, `H[2P_1/2]`, `H[2S_1/2]`, `N`, `N+`, `N+[1D_2]`, `N+[1S_0]`, `N[2D_5/2]`, `N[2P_3/2]`, `O`, `O+`, `O+[2D_5/2]`, `O+[2P_3/2]`, `O-`, `O[1D_2]`, `O[3P_1]` |
| `noble_gas` | 5 | `Ar`, `Ar+`, `Ar+[4P_5/2]`, `Ar[1s3]`, `Ar[1s5]` |
| `oxygen` | 5 | `O2`, `O2+`, `O2-`, `O2[a1Delta_g]`, `O2[b1Sigma_g_plus]` |
| `nitrogen` | 4 | `N2`, `N2+`, `N2-`, `N2[A3Sigma_u_plus]` |
| `hydrocarbon` | 17 | `CH4`, `CH4+`, `CH4-`, `CH4[V13]`, `CH4[V24]`, `CH3`, `CH3+`, `CH2`, `CH2+`, `CH2-`, `CH`, `CH+`, `C`, `C+`, `H`, `H-`, `H2` |
| `fluorocarbon` | 21 | `c-C4F8`, `c-C4F8+`, `c-C4F8-`, `F`, `F-`, `C4F7`, `CF3`, `CF3+`, `CF3-`, `CF2`, `CF2+`, `CF+`, `C2F3`, `C2F3+`, `C2F4`, `C2F4+`, `C2F5`, `C3F5`, `C3F5+`, `C3F5-`, `C3F6` |

### 2.2 補足

- `hydrocarbon` の多くは、現時点では packaged curated catalog 由来です。
- `core_plasma` は主に `atomic_asd` 由来の atomic ground / ion / excited state が中心です。
- `O2`, `N2`, `CH4`, `c-C4F8` の分子励起種は curated state_master 由来です。
- `-2` と `+2` は schema 上は扱えますが、現状の登録種はほぼ `-1`, `0`, `+1` です。

## 3. 対応済みイオン種だけ抽出した表

### 3.1 Family 別イオン一覧

| family | cation | anion |
| --- | --- | --- |
| `core_plasma` | `C+[2P_3/2]`, `C+[4P_1/2]`, `N+`, `N+[1D_2]`, `N+[1S_0]`, `O+`, `O+[2D_5/2]`, `O+[2P_3/2]` | `O-` |
| `noble_gas` | `Ar+`, `Ar+[4P_5/2]` | なし |
| `oxygen` | `O2+` | `O2-` |
| `nitrogen` | `N2+` | `N2-` |
| `hydrocarbon` | `CH4+`, `CH3+`, `CH2+`, `CH+`, `C+` | `CH4-`, `CH2-`, `H-` |
| `fluorocarbon` | `c-C4F8+`, `CF+`, `CF2+`, `CF3+`, `C2F3+`, `C2F4+`, `C3F5+` | `c-C4F8-`, `F-`, `CF3-`, `C3F5-` |

### 3.2 現状のイオン対応の読み方

- 実質的に現在しっかり入っているのは **一価イオン** です。
- `electron` は species catalog ではなく projectile として扱います。
- 原子イオンの励起状態は `atomic_asd` から自動展開できます。
  例: `Ar+[4P_5/2]`, `O+[2D_5/2]`, `N+[1D_2]`
- 分子多価イオンや `-2 / +2` の curated state はまだ未整備です。

## 4. Promotion 有効時に追加される excited state

[`examples/production_blueprint/config_state_promotion_runtime.yaml`](../examples/production_blueprint/config_state_promotion_runtime.yaml)
を使うと、QDB / IDEADB / VAMDC 由来の外部 evidence から、少なくとも次の分子励起状態が追加されます。

| base species | promoted excited state | source 例 |
| --- | --- | --- |
| `CH4` | `CH4[V14]` | `qdb` |
| `O2` | `O2[c1Sigma_u_minus]` | `qdb`, `vamdc` |
| `N2` | `N2[B3Pi_g]` | `ideadb` |

これらは
[`examples/production_blueprint/excited_state_registry.yaml`](../examples/production_blueprint/excited_state_registry.yaml)
で表記ゆれを canonical key に統一しています。

## 5. 未対応 family を追加する優先順位案

### 5.1 優先順位

| 優先度 | family | 推奨理由 |
| --- | --- | --- |
| 1 | `hydrogen` | 既に `H`, `H2`, `H-` はあるが、family としては未分離。ほぼ全系で共通に効き、反応網の土台になるため。 |
| 2 | `chlorine` | プラズマプロセス用途で重要度が高く、`fluorocarbon` と同じくハロゲン系テンプレートへ展開しやすいため。 |
| 3 | `silicon` | `SiH4`, `SiF4`, `SiCl4` 系が入ると etch / deposition の実務適用範囲が大きく広がるため。 |
| 4 | `impurity_common` overlay | `H2O`, `CO`, `CO2`, `NO`, `NO2` を先に overlay 化すると、既存 family の現実性が一気に上がるため。 |
| 5 | `mix_oxy_hydrocarbon`, `mix_oxy_nitrogen` overlay | `CHxOy`, `NOx` を扱えるようになると、混合系解析の実用度が高くなるため。 |
| 6 | `bromine` | `chlorine` の設計を流用しやすいが、需要の一般性は一段低いため。 |
| 7 | `sulfur` | 応用先はあるが、現在のテンプレート資産との連続性はやや弱いため。 |
| 8 | `phosphorus` | ニッチ寄りで、先にハロゲン系・シリコン系を固めた方が全体価値が高いため。 |

### 5.2 実装の進め方

次に着手するなら、以下の順が安全です。

1. `hydrogen` family の state_master と reaction template を独立化する
2. `chlorine` family を `fluorocarbon` に準じた粒度で追加する
3. `silicon` family を `halide` 系と一緒に追加する
4. `impurity_common` overlay を追加して混合系へ広げる

## 6. 現在の見立て

- **コア実装済み**:
  `core_plasma`, `hydrocarbon`, `fluorocarbon`, `oxygen`, `nitrogen`, `noble_gas`
- **部分対応**:
  `hydrogen`
- **未着手に近い**:
  `chlorine`, `bromine`, `silicon`, `sulfur`, `phosphorus`, overlay family 群
