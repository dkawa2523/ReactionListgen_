# 半導体製造装置向けガス・状態・反応式 拡張計画

## 1. 位置づけ

この計画は、**2026-04-07 時点**で確認できた公開情報と、現在のコードベースの制約を踏まえて作成したものです。

重要な前提:

- 現在のプロジェクト方針では、**表面反応・壁損失・3体反応は含めない**
- したがって、成膜プロセスについては、まず **ガス相 / プラズマ相の活性化・分解・イオン化** を先に整備する
- **膜成長そのものの half-cycle や adsorption / desorption** は、第2段階の拡張対象とする

この前提により、本計画は次の2層で進めます。

1. **今すぐ実装する層**
   - エッチングで直接効く気相・プラズマ反応
   - PECVD / PEALD / CVD で前駆体がプラズマ中で受ける気相反応
2. **後で拡張する層**
   - 表面吸着
   - 表面還元 / 表面酸化
   - 成膜 half-cycle
   - chamber wall / wafer surface interaction

## 2. 調査から見た優先ガス群

### 2.1 エッチング系で優先度が高いガス

#### A. フッ素系・酸化膜エッチ系

- `CF4`
- `CHF3`
- `CH2F2`
- `CH3F`
- `C2F6`
- `C4F8`
- `C5F8`
- `SF6`
- `NF3`
- `O2`
- `Ar`
- `He`

理由:

- Air Liquide Electronics Systems は、deep oxide etch の代表例として `C4F8`, `CF4`, `CHF3`, `CH3F`, `CH2F2`, `C5F8` を挙げています。
- 同ページは silicon / polysilicon etch に `SF6`, `CF4`, `CH2F2`, `CHF3`, `C2F6` を挙げています。
- Air Liquide は `SF6` を high density plasma etching のフッ素源として説明しています。
- Air Liquide は `NF3` を CVD reactor clean のフッ素源かつ selective SiO2 etch reagent と説明しています。

#### B. 塩素・臭素系コンダクタ / シリコン系エッチ

- `Cl2`
- `HBr`
- `BCl3`
- `HCl`
- `O2`
- `N2`
- `Ar`
- `He`
- `H2`

理由:

- Entegris は dry etch / epitaxial process 向け腐食性ガスの例として `Cl2`, `HBr`, `HCl`, `BCl3`, `SF6`, `CF4` を挙げています。
- Air Liquide は `HCl` を native oxide etch、CVD reactor cleaning、moisture getter 用途として説明しています。
- `Ar`, `He`, `H2`, `N2`, `O2` は希釈・搬送・プラズマ安定化・選択性制御で頻出する補助ガスです。

### 2.2 成膜系で優先度が高いガス

#### C. Si 系 PECVD / CVD / Epi

- `SiH4`
- `NH3`
- `N2O`
- `O2`
- `H2`
- `Ar`
- `He`
- `DCS` (`SiH2Cl2`)
- `TCS` (`SiHCl3`)
- `HCl`

理由:

- Air Liquide は `SiH4` を polysilicon、epitaxial silicon、`SiO2`、`Si3N4` の CVD ソースとして説明しています。
- Air Liquide は `NH3` を silicon nitride deposition に使うと説明しています。
- Air Liquide は `N2O` を silicon oxynitride と `SiO2` の CVD 酸素源として説明しています。
- Air Liquide は `H2` を silicon epitaxy と (PE)ALD の reactant と説明しています。
- Entegris の purifier documentation には `DCS`, `TCS`, `HCl` が半導体向け腐食性ガスとして含まれています。これらは塩化シラン系 CVD / epi の実務上重要な候補です。

#### D. 酸化膜・絶縁膜系 CVD / ALD

- `TEOS` ただし formula は `C8H20O4Si` で保持
- `O2`
- `O3`
- `N2O`
- `He`
- `N2`

理由:

- Entegris は `TEOS` を CVD による doped / undoped `SiO2` film deposition 用途として説明しています。
- Air Liquide は `O3` を (PE)ALD oxide deposition の oxidant と説明しています。

#### E. High-k / metal-halide 系

- `HfCl4`
- `WF6`
- `O3`
- `H2`
- `NH3`
- `H2O` 将来候補

理由:

- Entegris は `HfCl4` を HKMG transistor / capacitor structure 向け ALD precursor とし、酸素源として `H2O` または `O3` を挙げています。
- Air Liquide Electronics Systems は tungsten etch の例として `WF6`, `SF6` を挙げています。
- `WF6` は tungsten 系プロセスで重要で、気相フラグメント・ハロゲン化学の観点からも優先度が高いです。

#### F. 先端 precursor 群

- `Si2H6`
- `GeH4`
- `B2H6`
- organometallic precursor 群
  - 例: `TMA`, `TEMAH`, `TDMAT`, Co / Ru precursor など

理由:

- Air Liquide Voltaix は `Si2H6`, `GeH4`, `B2H6` を CVD / ALD 向け key material としています。
- Air Liquide ALOHA は Ru / W / Co precursor を先端デバイス向け deposition material と位置づけています。

ただし:

- organometallic precursor は species 登録自体は可能
- 反応テンプレートは surface chemistry 依存が大きいため、**第3段階以降**が妥当

## 3. このコードベースで追加すべき family

### 3.1 追加すべき species family

優先順:

1. `hydrogen`
2. `chlorine`
3. `bromine`
4. `silicon`
5. `boron`
6. `tungsten`
7. `hafnium`
8. `impurity_common` overlay

理由:

- `hydrogen`, `chlorine`, `bromine` は etch と deposition の両方にまたがる
- `silicon` は `SiH4`, `DCS`, `TCS`, `TEOS` 由来 fragment を受ける核 family になる
- `tungsten`, `hafnium` は metal-halide deposition / etch の入口として必要
- `impurity_common` は `H2O`, `CO`, `CO2`, `NO`, `NO2` を整理するために必要

### 3.2 追加すべき template pack

species family とは別に、template は process pack として分けるのがよいです。

推奨 pack:

1. `etch_fluorocarbon_oxide`
2. `etch_halogen_conductor`
3. `etch_silicon_poly`
4. `deposition_silane_nitride_oxide_gas_phase`
5. `deposition_chlorosilane_epi_gas_phase`
6. `deposition_teos_oxide_gas_phase`
7. `deposition_high_k_halide_gas_phase`
8. `clean_nf3_sf6`

## 4. ガス群ごとの state 設計方針

### 4.1 エッチ系フッ素化学

対象親ガス:

- `CF4`, `CHF3`, `CH2F2`, `CH3F`, `C2F6`, `C4F8`, `C5F8`, `SF6`, `NF3`

最低限の状態:

- 親分子 neutral
- 親分子 cation / anion
- primary radical
  - `CF3`, `CF2`, `CF`, `F`
  - `SF5`, `SF4`, `SF3`, `F`
  - `NF2`, `NF`, `F`
- primary ion
  - `CF4+`, `CF3+`, `CF2+`, `CF+`
  - `F-`
  - `SF5+`, `SF4+`, `NF2+`
- 必要なら二次中間体
  - `COF2`, `CF2O`, `HF`, `FO`, `OF`

### 4.2 塩素・臭素系

対象親ガス:

- `Cl2`, `HBr`, `BCl3`, `HCl`

最低限の状態:

- `Cl2`, `Cl`, `Cl+`, `Cl-`, `Cl2+`
- `Br`, `Br+`, `Br-`
- `HBr`, `HBr+`, `HBr-`
- `HCl`, `HCl+`, `HCl-`
- `BCl3`, `BCl2`, `BCl`, `B`, `BCl3+`
- `H`, `H+`, `H-`

### 4.3 Si 系 deposition / etch 共通

対象親ガス:

- `SiH4`, `SiH2Cl2`, `SiHCl3`

最低限の状態:

- `SiH4`, `SiH3`, `SiH2`, `SiH`, `Si`
- `SiH4+`, `SiH3+`, `SiH2+`
- `SiH2Cl2`, `SiHCl2`, `SiCl2`, `SiCl`, `SiCl4`
- `SiHCl3`, `SiCl3`, `SiCl2`
- `H2`, `H`, `H-`

### 4.4 酸化膜・窒化膜・高-k 系 oxidant / reactant

対象親ガス:

- `NH3`, `N2O`, `O2`, `O3`, `H2`

最低限の状態:

- `NH3`, `NH2`, `NH`, `N`
- `NH3+`, `NH2+`, `NH+`
- `N2O`, `NO`, `N2`, `O`
- `O2`, `O`, `O-`, `O2-`, `O+`
- `O3`
- `H2`, `H`

### 4.5 TEOS / halide / advanced precursor

対象親ガス:

- `TEOS`, `HfCl4`, `WF6`, `Si2H6`, `GeH4`, `B2H6`

state 方針:

- 第1段階は parent neutral / cation と primary fragment までに限定
- `TEOS` は empirical formula を `C8H20O4Si` として持たせる
- `HfCl4`, `WF6` は halide fragmentation を先に入れる
- `Si2H6`, `GeH4`, `B2H6` は hydride fragmentation を先に入れる
- organometallic precursor は parent + major ligand-loss bucket を先に入れる

## 5. 反応式テンプレートを埋める順序

### 5.1 Phase 1: ドライエッチ immediate pack

対象ガス:

- `CF4`, `CHF3`, `CH2F2`, `C2F6`, `C4F8`, `SF6`, `Cl2`, `HBr`, `BCl3`, `HCl`, `O2`, `Ar`, `He`, `H2`, `N2`

追加する template family:

- `electron_attachment`
- `electron_detachment`
- `electron_excitation`
- `electron_dissociation`
- `electron_ionization`
- `electron_dissociative_ionization`
- `charge_transfer`
- `ion_neutral_followup`
- `neutral_fragmentation`
- `radical_fragmentation`
- `radical_neutral_reaction`
- `dissociative_recombination`

重点反応:

- `Cl2 + e- -> Cl + Cl + e-`
- `HBr + e- -> H + Br + e-`
- `BCl3 + e- -> BCl2 + Cl + e-`
- `CF4 + e- -> CF3 + F + e-`
- `CHF3 + e- -> CF2 + HF + e-`
- `SF6 + e- -> SF5 + F + e-`
- `O2 + e- -> O + O + e-`
- `Ar + e- -> Ar+ + 2e-`

### 5.2 Phase 2: PECVD / CVD gas-phase pack

対象ガス:

- `SiH4`, `NH3`, `N2O`, `O2`, `H2`, `Ar`, `He`, `SiH2Cl2`, `SiHCl3`, `HCl`

追加する template family:

- `electron_dissociation`
- `electron_ionization`
- `electron_excitation`
- `ion_neutral_followup`
- `radical_neutral_reaction`
- `exchange_reaction`

重点反応:

- `SiH4 + e- -> SiH3 + H + e-`
- `NH3 + e- -> NH2 + H + e-`
- `N2O + e- -> N2 + O + e-`
- `SiH2Cl2 + e- -> SiHCl2 + H + e-`
- `SiHCl3 + e- -> SiCl3 + H + e-`
- `H2 + e- -> H + H + e-`

### 5.3 Phase 3: TEOS / high-k / metal-halide gas-phase pack

対象ガス:

- `TEOS`, `O3`, `HfCl4`, `WF6`, `H2`, `NH3`, `Si2H6`, `GeH4`, `B2H6`

追加する template family:

- `electron_dissociation`
- `electron_ionization`
- `ligand_loss_bucket`
- `halide_reduction_followup`
- `oxidant_activation`

重点反応:

- `O3 + e- -> O2 + O + e-`
- `WF6 + e- -> WF5 + F + e-`
- `HfCl4 + e- -> HfCl3 + Cl + e-`
- `Si2H6 + e- -> SiH3 + SiH3 + e-`
- `GeH4 + e- -> GeH3 + H + e-`
- `B2H6 + e- -> BH3 + BH3 + e-`

### 5.4 Phase 4: 表面反応モデル拡張

この phase で初めて、成膜プロセスの本丸を扱います。

追加する template family:

- `surface_adsorption`
- `surface_ligand_elimination`
- `surface_fluorination`
- `surface_chlorination`
- `surface_oxidation`
- `surface_reduction`
- `surface_growth_half_cycle`
- `surface_byproduct_desorption`

## 6. 実装バックログ

### Sprint 1

- `hydrogen`, `chlorine`, `bromine` family の state_master 追加
- `etch_halogen_conductor` template pack 追加
- `clean_nf3_sf6` template pack 追加
- alias / registry に `Cl2`, `HBr`, `BCl3`, `HCl`, `SiH2Cl2`, `SiHCl3` を追加

### Sprint 2

- `silicon` family の state_master 追加
- `deposition_silane_nitride_oxide_gas_phase` pack 追加
- `deposition_chlorosilane_epi_gas_phase` pack 追加
- `impurity_common` overlay 追加

### Sprint 3

- `boron`, `tungsten`, `hafnium` family 追加
- `deposition_teos_oxide_gas_phase` pack 追加
- `deposition_high_k_halide_gas_phase` pack 追加
- `TEOS`, `WF6`, `HfCl4`, `Si2H6`, `GeH4`, `B2H6` を registry / catalog に追加

### Sprint 4

- surface reaction schema 設計
- builder / scoring / visualization の surface support 拡張
- PEALD / ALD / CVD の surface template を追加

## 7. 受け入れ基準

### 7.1 Phase 1 完了条件

- `Cl2`, `HBr`, `BCl3`, `CF4`, `CHF3`, `SF6`, `NF3`, `HCl` が state catalog に入る
- 主要 fragment / ion が入る
- `build` 結果でハロゲン・フッ素・水素の primary chemistry が途切れない
- `inspect-sources` に追加 family が反映される

### 7.2 Phase 2 完了条件

- `SiH4`, `NH3`, `N2O`, `DCS`, `TCS`, `H2` が state / template 両方に入る
- PECVD/CVD gas activation network が単体 build で生成できる
- charge window と excited-state registry が新ガス群にも効く

### 7.3 Phase 3 完了条件

- `TEOS`, `WF6`, `HfCl4`, `Si2H6`, `GeH4`, `B2H6` が source-backed または curated で catalog 化される
- large precursor でも alias / formula / canonical key が壊れない
- gas-phase の fragmentation template が最低限そろう

## 8. まず着手すべき最小セット

最初の1バッチで入れるなら、次のセットが最も費用対効果が高いです。

### エッチ immediate

- `Cl2`
- `HBr`
- `BCl3`
- `HCl`
- `CF4`
- `CHF3`
- `CH2F2`
- `C2F6`
- `C4F8`
- `SF6`
- `NF3`
- `O2`
- `Ar`
- `He`
- `H2`
- `N2`

### 成膜 immediate

- `SiH4`
- `NH3`
- `N2O`
- `O3`
- `SiH2Cl2`
- `SiHCl3`
- `TEOS`
- `H2`
- `Ar`
- `He`

### 後続 immediate

- `WF6`
- `HfCl4`
- `Si2H6`
- `GeH4`
- `B2H6`

## 9. 情報源

以下は今回の計画立案に使った一次情報です。

- Lam Research etch process overview  
  https://www.lamresearch.com/ja/products/our-processes/etch/
- Air Liquide Electronics Systems, process examples for semiconductor abatement  
  https://ales.airliquide.com/universal-plasma-abatement-system
- Entegris corrosive gas purifier release  
  https://www.entegris.com/content/dam/web/about-us/news/documents/gatekeeper-corrosive-gases-gpu.pdf
- Entegris corrosive gas purifier specifications  
  https://www.entegris.com/content/dam/shared-product-assets/gatekeeper-shared/datasheet-gatekeeper-eds0414-ja.pdf
- Air Liquide Gas Encyclopedia: Silane  
  https://encyclopedia.airliquide.com/silane
- Air Liquide Gas Encyclopedia: Ammonia  
  https://encyclopedia.airliquide.com/ammonia
- Air Liquide Gas Encyclopedia: Nitrous Oxide  
  https://encyclopedia.airliquide.com/fr/protoxyde-azote
- Air Liquide Gas Encyclopedia: Ozone  
  https://encyclopedia.airliquide.com/ozone
- Air Liquide Gas Encyclopedia: Hydrogen Chloride  
  https://encyclopedia.airliquide.com/hydrogen-chloride
- Air Liquide Gas Encyclopedia: Hydrogen  
  https://encyclopedia.airliquide.com/fr/hydrogene
- Air Liquide Gas Encyclopedia: Helium  
  https://encyclopedia.airliquide.com/helium
- Air Liquide Gas Encyclopedia: Argon  
  https://encyclopedia.airliquide.com/argon
- Air Liquide Gas Encyclopedia: Sulfur Hexafluoride  
  https://encyclopedia.airliquide.com/sulfur-hexafluoride
- Air Liquide Gas Encyclopedia: Nitrogen Trifluoride  
  https://encyclopedia.airliquide.com/nitrogen-trifluoride
- Entegris UltraPur TEOS datasheet  
  https://www.entegris.com/content/dam/product-assets/teos/datasheet-ultrapur-teos-8039.pdf
- Entegris HfCl4 product page  
  https://www.entegris.com/shop/en/USD/products/chemistries/specialty-chemicals/precursors/advanced-deposition-materials-%28adm%29-ald-cvd-precursors/HfCl4/p/HfCl4
- Air Liquide Electronics Voltaix  
  https://electronics.airliquide.com/voltaixtm
