# 気相反応のみで考えるべき半導体プロセスガス

## 1. 前提

この整理では、**表面反応・壁損失・3体反応を含めません**。
したがって、対象に入れるのは次の条件を満たすガスです。

- プラズマ中での **解離・励起・イオン化・電子付着** を気相反応として表現しやすい
- 生成される **ラジカル・原子・イオン** が、気相 network の中で意味を持つ
- 成膜用途でも、まずは **前駆体の気相活性化** を表現するところまでで価値がある

逆に、次のものは現段階では優先度を下げます。

- 表面 half-cycle が本質の ALD precursor
- ligand exchange / adsorption / desorption を書かないと意味が薄い organometallic precursor

## 2. 結論: まず入れるべきガス

### 2.1 最優先バッチ

このバッチは、**表面反応を除いた条件でも十分に意味がある**ガスです。

| 区分 | ガス |
| --- | --- |
| 共通プラズマ / 希釈 / 搬送 | `Ar`, `He`, `N2`, `H2`, `O2` |
| フッ素系エッチ / クリーニング | `CF4`, `CHF3`, `CH2F2`, `CH3F`, `C2F6`, `C4F8`, `C5F8`, `SF6`, `NF3` |
| 塩素・臭素系エッチ | `Cl2`, `HBr`, `HCl`, `BCl3` |
| 成膜系の気相活性化 | `SiH4`, `NH3`, `N2O`, `O3`, `SiH2Cl2`, `SiHCl3` |

このセットだけで、気相反応として重要な半導体プロセスのかなりの部分をカバーできます。

## 3. ガスを入れる理由

### 3.1 共通プラズマ / 希釈 / 搬送

対象:

- `Ar`
- `He`
- `N2`
- `H2`
- `O2`

理由:

- `Ar`, `He` はプラズマ維持、希釈、イオン衝突、エネルギー移送の基盤になる
- `O2` は酸化膜系、フルオロカーボン系、クリーニング系のどれにも出てくる
- `H2` は還元性・ラジカル補正・ハロゲン化学・成膜系で共通に効く
- `N2` は希釈だけでなく、励起窒素・窒素ラジカル・`N2+` の source にもなる

### 3.2 フッ素系エッチ / クリーニング

対象:

- `CF4`
- `CHF3`
- `CH2F2`
- `CH3F`
- `C2F6`
- `C4F8`
- `C5F8`
- `SF6`
- `NF3`

理由:

- Air Liquide Electronics Systems は、silicon oxide / deep oxide etch に `C4F8`, `CF4`, `CHF3`, `CH3F`, `CH2F2`, `C5F8` を挙げています
- 同社は silicon / polysilicon etch に `SF6`, `CF4`, `CH2F2`, `CHF3`, `C2F6` を挙げています
- `NF3` は CVD reactor clean のフッ素源として広く使われます

気相で重要な生成種:

- `F`
- `F-`
- `CF3`, `CF2`, `CF`
- `C2F5`, `C2F4`, `C2F3`
- `SF5`, `SF4`, `SF3`
- `NF2`, `NF`
- `COF2`, `CF2O`, `HF` は後続で候補

### 3.3 塩素・臭素系エッチ

対象:

- `Cl2`
- `HBr`
- `HCl`
- `BCl3`

理由:

- コンダクタ、poly、metal、hard mask 系では塩素・臭素化学が重要
- `HCl` は native oxide etch や CVD reactor cleaning にも使われます
- `BCl3` は塩素源であるだけでなく、`BClx` fragment chemistry を持つため気相モデル価値が高い

気相で重要な生成種:

- `Cl`
- `Cl-`
- `Cl+`
- `Br`
- `Br-`
- `Br+`
- `BCl2`, `BCl`, `B`
- `H`, `H+`, `H-`

### 3.4 成膜系の気相活性化

対象:

- `SiH4`
- `NH3`
- `N2O`
- `O3`
- `SiH2Cl2`
- `SiHCl3`

理由:

- `SiH4` は polysilicon / epitaxial silicon / `SiO2` / `Si3N4` の気相 source として代表的
- `NH3` は nitride 系の代表 reactant
- `N2O` は oxide / oxynitride 系の酸素 source
- `O3` は ALD/PEALD では表面 oxidant でもあるが、**気相では強い酸化性・解離 source** として独立価値がある
- `SiH2Cl2`, `SiHCl3` は chlorosilane 系 CVD / epi を気相側から表現する上で重要

気相で重要な生成種:

- `SiH3`, `SiH2`, `SiH`
- `NH2`, `NH`, `N`
- `NO`, `N2`, `O`
- `SiHCl2`, `SiCl3`, `SiCl2`

## 4. 条件付きで第2陣に入れるガス

以下は有用ですが、最初の実装バッチには入れなくてもよい候補です。

| ガス | 理由 |
| --- | --- |
| `TEOS` | 気相フラグメントは意味があるが、最終的な価値は表面反応とセットになりやすい |
| `WF6` | tungsten 系で重要だが、family 追加が必要 |
| `HfCl4` | high-k precursor として重要だが、surface chemistry 依存度が高い |
| `Si2H6` | Si 系成膜で有用、ただし `SiH4` より優先は低い |
| `GeH4` | 応用先は明確だが対象範囲が少し狭い |
| `B2H6` | ドーピング・特殊用途で重要だが汎用優先度は低い |

## 5. 今は外してよいガス

次は**気相だけでは中途半端になりやすい**ため、いまは外してよいです。

- `TMA`
- `TEMAH`
- `TDMAT`
- Co / Ru / W の organometallic precursor 群
- 表面吸着・リガンド脱離を書かないと意味が薄い大型 precursor

外す理由:

- species 登録だけはできる
- しかし、反応ネットワークとして価値が出るのは表面反応を入れてから

## 6. 実装に落とすときの具体単位

### 6.1 すぐ実装する gas family backlog

1. `etch_common_support`
   - `Ar`, `He`, `N2`, `H2`, `O2`
2. `etch_fluorocarbon`
   - `CF4`, `CHF3`, `CH2F2`, `CH3F`, `C2F6`, `C4F8`, `C5F8`
3. `etch_inorganic_fluoride`
   - `SF6`, `NF3`
4. `etch_halogen`
   - `Cl2`, `HBr`, `HCl`, `BCl3`
5. `deposition_silane_gas_phase`
   - `SiH4`, `SiH2Cl2`, `SiHCl3`
6. `deposition_reactant_gas_phase`
   - `NH3`, `N2O`, `O3`, `H2`, `O2`

### 6.2 各ガスに最低限必要な state

各親ガスごとに最低限持つべき state は次のとおりです。

- neutral parent
- parent cation
- parent anion
  ただし実在性が弱いものは source-backed のみ
- primary dissociation fragment
- primary fragment cation
- 主要な electronegative fragment anion

例:

- `CF4`:
  `CF4`, `CF4+`, `CF3`, `CF3+`, `CF2`, `CF2+`, `CF`, `CF+`, `F`, `F-`
- `Cl2`:
  `Cl2`, `Cl2+`, `Cl`, `Cl+`, `Cl-`
- `HBr`:
  `HBr`, `HBr+`, `Br`, `Br+`, `Br-`, `H`, `H+`, `H-`
- `SiH4`:
  `SiH4`, `SiH4+`, `SiH3`, `SiH3+`, `SiH2`, `SiH2+`, `SiH`, `Si`
- `N2O`:
  `N2O`, `N2O+`, `N2`, `O`, `NO`

## 7. 反応 family も気相だけに絞る

このスコープで使う reaction family は次だけで十分です。

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

除外:

- `surface_adsorption`
- `surface_growth_half_cycle`
- `surface_ligand_elimination`
- `wall_loss`

## 8. 最終提案

表面反応を除くなら、**まず本当に入れるべきガス**は次の 20 種です。

### 必須 20 ガス

- `Ar`
- `He`
- `N2`
- `H2`
- `O2`
- `CF4`
- `CHF3`
- `CH2F2`
- `CH3F`
- `C2F6`
- `C4F8`
- `C5F8`
- `SF6`
- `NF3`
- `Cl2`
- `HBr`
- `HCl`
- `BCl3`
- `SiH4`
- `NH3`

### その次に入れる 6 ガス

- `N2O`
- `O3`
- `SiH2Cl2`
- `SiHCl3`
- `WF6`
- `TEOS`

## 9. 出典

- Air Liquide Electronics Systems, UPAS  
  https://ales.airliquide.com/universal-plasma-abatement-system
- Air Liquide Gas Encyclopedia, Silane  
  https://encyclopedia.airliquide.com/silane
- Air Liquide Gas Encyclopedia, Ammonia  
  https://encyclopedia.airliquide.com/ammonia
- Air Liquide Gas Encyclopedia, Ozone  
  https://encyclopedia.airliquide.com/ozone
- Air Liquide Gas Encyclopedia, Hydrogen Chloride  
  https://encyclopedia.airliquide.com/hydrogen-chloride
- Air Liquide Gas Encyclopedia, Hydrogen  
  https://encyclopedia.airliquide.com/fr/hydrogene
- Air Liquide Gas Encyclopedia, Nitrous Oxide  
  https://encyclopedia.airliquide.com/fr/protoxyde-azote
- Air Liquide Gas Encyclopedia, Nitrogen Trifluoride  
  https://encyclopedia.airliquide.com/nitrogen-trifluoride
