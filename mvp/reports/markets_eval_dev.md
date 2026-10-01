# 多市场评测报告（自动生成）

- 真实地址：各城市留出的 20% 商户（不在参考库里）的自填地址，标准答案为商户坐标（弱标注）
- 合成地址：按各市场写法渲染的测试部分道路（AI 解析器训练时没见过），标准答案已知
- 解析方式：rules = 规则 + 地名表；crf = 机器学习（条件随机场）；hybrid = 两者都出候选，由参考数据裁决
- 判对标准（真实地址）：门牌级 ≤ 250 米、楼宇级 ≤ 400 米、道路级为该道路经过商户 250 米内；"偏差 >1 公里"的静默错误不是商户坐标不准能解释的，是真正的错

## 真实商户地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 600 | 75.3% | 3.3% | 1.0% | 12.8% | 4.8% | 2.7% | 1.5% | 86.8% | 2 |
| 澳大利亚（AU） | A | crf | 600 | 69.5% | 2.7% | 2.8% | 17.5% | 4.8% | 2.7% | 1.5% | 85.8% | 1 |
| 澳大利亚（AU） | A | hybrid | 600 | 76.0% | 2.7% | 1.0% | 12.3% | 5.2% | 2.8% | 1.7% | 86.3% | 2 |
| 德国（DE） | A | rules | 600 | 92.7% | 1.7% | 0.2% | 2.2% | 2.3% | 1.0% | 0.7% | 96.8% | 1 |
| 德国（DE） | A | crf | 600 | 86.2% | 1.7% | 0.3% | 9.3% | 1.8% | 0.7% | 0.5% | 95.0% | 1 |
| 德国（DE） | A | hybrid | 600 | 94.2% | 1.7% | 0.0% | 2.2% | 1.0% | 1.0% | 0.7% | 98.2% | 2 |
| 法国（FR） | A | rules | 600 | 86.8% | 3.3% | 0.3% | 6.7% | 1.0% | 1.8% | 1.0% | 95.0% | 1 |
| 法国（FR） | A | crf | 600 | 85.2% | 4.0% | 0.5% | 6.3% | 2.0% | 2.0% | 1.2% | 94.0% | 1 |
| 法国（FR） | A | hybrid | 600 | 87.2% | 3.3% | 0.0% | 6.7% | 0.8% | 2.0% | 1.2% | 95.5% | 2 |
| 荷兰（NL） | A | rules | 600 | 82.0% | 7.0% | 1.2% | 8.0% | 0.5% | 1.3% | 0.7% | 95.8% | 2 |
| 荷兰（NL） | A | crf | 600 | 73.2% | 1.5% | 0.5% | 22.7% | 1.2% | 1.0% | 0.5% | 91.2% | 1 |
| 荷兰（NL） | A | hybrid | 600 | 84.7% | 4.7% | 0.8% | 7.8% | 0.7% | 1.3% | 0.7% | 96.3% | 2 |
| 阿联酋（AE） | B | rules | 600 | 1.7% | 30.3% | 11.7% | 25.3% | 30.0% | 1.0% | 0.2% | 19.5% | 3 |
| 阿联酋（AE） | B | crf | 600 | 0.5% | 19.3% | 7.7% | 52.0% | 20.2% | 0.3% | 0.2% | 11.3% | 2 |
| 阿联酋（AE） | B | hybrid | 600 | 1.7% | 30.5% | 10.7% | 22.0% | 34.2% | 1.0% | 0.2% | 20.0% | 4 |
| 沙特（SA） | B | rules | 600 | 2.0% | 29.2% | 11.2% | 14.3% | 42.8% | 0.5% | 0.5% | 16.7% | 2 |
| 沙特（SA） | B | crf | 600 | 1.8% | 28.2% | 15.7% | 26.8% | 26.8% | 0.7% | 0.7% | 17.8% | 2 |
| 沙特（SA） | B | hybrid | 600 | 2.2% | 33.5% | 8.8% | 13.5% | 41.5% | 0.5% | 0.5% | 19.5% | 4 |
| 马来西亚（MY） | C | rules | 600 | 33.2% | 35.3% | 4.2% | 5.0% | 19.3% | 3.0% | 1.2% | 54.5% | 2 |
| 马来西亚（MY） | C | crf | 600 | 27.8% | 39.5% | 11.8% | 7.0% | 11.0% | 2.8% | 1.2% | 57.2% | 2 |
| 马来西亚（MY） | C | hybrid | 600 | 33.2% | 38.7% | 3.7% | 3.3% | 18.0% | 3.2% | 1.2% | 58.2% | 4 |
| 印尼（ID） | C | rules | 600 | 26.5% | 30.2% | 1.7% | 3.8% | 34.3% | 3.5% | 0.3% | 40.3% | 2 |
| 印尼（ID） | C | crf | 600 | 11.7% | 37.5% | 20.7% | 7.7% | 20.8% | 1.7% | 0.3% | 47.5% | 4 |
| 印尼（ID） | C | hybrid | 600 | 26.5% | 33.2% | 1.7% | 3.3% | 31.7% | 3.7% | 0.5% | 43.3% | 6 |
| 泰国（TH） | C | rules | 600 | 15.8% | 41.7% | 11.5% | 8.3% | 20.5% | 2.2% | 0.7% | 27.7% | 5 |
| 泰国（TH） | C | crf | 600 | 12.3% | 28.0% | 26.2% | 20.3% | 12.0% | 1.2% | 0.3% | 19.0% | 2 |
| 泰国（TH） | C | hybrid | 600 | 15.8% | 41.2% | 10.7% | 8.2% | 21.8% | 2.3% | 0.7% | 27.5% | 7 |
| 越南（VN） | C | rules | 600 | 8.7% | 53.5% | 2.0% | 4.5% | 29.3% | 2.0% | 0.7% | 48.0% | 2 |
| 越南（VN） | C | crf | 600 | 8.8% | 38.7% | 18.7% | 15.7% | 17.0% | 1.2% | 0.7% | 41.2% | 2 |
| 越南（VN） | C | hybrid | 600 | 11.5% | 52.5% | 1.5% | 4.2% | 28.2% | 2.2% | 0.8% | 48.7% | 4 |
| 菲律宾（PH） | C | rules | 600 | 20.3% | 35.5% | 13.8% | 6.7% | 21.3% | 2.3% | 1.2% | 39.2% | 2 |
| 菲律宾（PH） | C | crf | 600 | 11.3% | 40.0% | 24.3% | 8.3% | 15.5% | 0.5% | 0.2% | 43.2% | 2 |
| 菲律宾（PH） | C | hybrid | 600 | 21.8% | 42.3% | 7.0% | 3.8% | 22.7% | 2.3% | 1.2% | 46.3% | 4 |

## 合成地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 600 | 81.8% | 8.8% | 0.0% | 4.8% | 4.0% | 0.5% | 0.0% | 95.7% | 1 |
| 澳大利亚（AU） | A | crf | 600 | 86.7% | 6.7% | 0.0% | 4.7% | 1.5% | 0.5% | 0.0% | 98.2% | 1 |
| 澳大利亚（AU） | A | hybrid | 600 | 86.7% | 6.3% | 0.0% | 4.7% | 1.8% | 0.5% | 0.0% | 97.8% | 2 |
| 德国（DE） | A | rules | 600 | 83.2% | 6.8% | 0.0% | 4.2% | 3.7% | 2.2% | 0.2% | 95.5% | 1 |
| 德国（DE） | A | crf | 600 | 86.5% | 8.0% | 0.0% | 4.2% | 1.2% | 0.2% | 0.2% | 98.3% | 1 |
| 德国（DE） | A | hybrid | 600 | 85.5% | 7.7% | 0.0% | 3.3% | 1.3% | 2.2% | 0.2% | 98.3% | 2 |
| 法国（FR） | A | rules | 600 | 88.3% | 4.7% | 0.0% | 5.2% | 1.2% | 0.7% | 0.0% | 98.0% | 1 |
| 法国（FR） | A | crf | 600 | 87.2% | 7.3% | 0.0% | 4.0% | 1.5% | 0.0% | 0.0% | 99.2% | 1 |
| 法国（FR） | A | hybrid | 600 | 89.3% | 5.5% | 0.0% | 4.0% | 0.5% | 0.7% | 0.0% | 99.5% | 2 |
| 荷兰（NL） | A | rules | 600 | 84.2% | 8.5% | 0.0% | 5.3% | 0.8% | 1.2% | 0.0% | 99.8% | 2 |
| 荷兰（NL） | A | crf | 600 | 86.5% | 7.8% | 0.0% | 5.2% | 0.0% | 0.5% | 0.0% | 100.0% | 1 |
| 荷兰（NL） | A | hybrid | 600 | 86.2% | 7.5% | 0.0% | 4.7% | 0.5% | 1.2% | 0.0% | 100.0% | 3 |
| 阿联酋（AE） | B | rules | 600 | 1.5% | 49.5% | 0.0% | 31.3% | 17.3% | 0.3% | 0.0% | 52.5% | 2 |
| 阿联酋（AE） | B | crf | 600 | 4.8% | 72.0% | 0.0% | 0.8% | 22.3% | 0.0% | 0.0% | 72.7% | 1 |
| 阿联酋（AE） | B | hybrid | 600 | 4.8% | 72.2% | 0.0% | 0.3% | 22.7% | 0.0% | 0.0% | 72.7% | 2 |
| 沙特（SA） | B | rules | 600 | 9.3% | 67.3% | 0.0% | 6.7% | 16.7% | 0.0% | 0.0% | 75.3% | 2 |
| 沙特（SA） | B | crf | 600 | 11.5% | 80.0% | 0.0% | 0.7% | 7.8% | 0.0% | 0.0% | 88.8% | 1 |
| 沙特（SA） | B | hybrid | 600 | 11.7% | 80.2% | 0.0% | 0.0% | 8.2% | 0.0% | 0.0% | 89.2% | 3 |
| 马来西亚（MY） | C | rules | 600 | 19.8% | 69.7% | 0.0% | 1.3% | 9.2% | 0.0% | 0.0% | 89.3% | 2 |
| 马来西亚（MY） | C | crf | 600 | 25.0% | 71.8% | 0.0% | 0.2% | 3.0% | 0.0% | 0.0% | 96.2% | 1 |
| 马来西亚（MY） | C | hybrid | 600 | 24.7% | 71.3% | 0.0% | 0.0% | 4.0% | 0.0% | 0.0% | 95.2% | 3 |
| 印尼（ID） | C | rules | 600 | 21.8% | 65.2% | 0.0% | 0.7% | 12.2% | 0.2% | 0.0% | 87.0% | 1 |
| 印尼（ID） | C | crf | 600 | 31.5% | 61.2% | 0.0% | 0.0% | 7.3% | 0.0% | 0.0% | 92.0% | 1 |
| 印尼（ID） | C | hybrid | 600 | 31.8% | 60.7% | 0.0% | 0.0% | 7.3% | 0.2% | 0.0% | 91.8% | 3 |
| 泰国（TH） | C | rules | 600 | 16.5% | 77.7% | 0.0% | 2.0% | 3.5% | 0.3% | 0.2% | 93.0% | 3 |
| 泰国（TH） | C | crf | 600 | 20.2% | 77.7% | 0.0% | 0.3% | 1.7% | 0.2% | 0.0% | 96.0% | 1 |
| 泰国（TH） | C | hybrid | 600 | 20.7% | 76.7% | 0.0% | 0.2% | 2.3% | 0.2% | 0.0% | 95.7% | 4 |
| 越南（VN） | C | rules | 600 | 30.8% | 60.0% | 0.0% | 0.8% | 8.2% | 0.2% | 0.0% | 90.7% | 2 |
| 越南（VN） | C | crf | 600 | 40.0% | 56.3% | 0.0% | 0.0% | 3.7% | 0.0% | 0.0% | 95.0% | 2 |
| 越南（VN） | C | hybrid | 600 | 40.2% | 56.0% | 0.0% | 0.0% | 3.7% | 0.2% | 0.0% | 95.0% | 4 |
| 菲律宾（PH） | C | rules | 600 | 21.7% | 61.7% | 0.0% | 4.8% | 11.8% | 0.0% | 0.0% | 82.5% | 2 |
| 菲律宾（PH） | C | crf | 600 | 28.0% | 60.0% | 0.0% | 0.3% | 11.7% | 0.0% | 0.0% | 86.3% | 1 |
| 菲律宾（PH） | C | hybrid | 600 | 28.2% | 62.0% | 0.0% | 0.0% | 9.8% | 0.0% | 0.0% | 87.7% | 3 |

## 错误样例（规则解析，真实地址）

**澳大利亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 141-151 Taren Point Rd Unit 13, Taren Point, 2229 | ACCEPT | PREMISE | Unit 13, 141-151 Taren Point Road, Taren Point NSW 2229 |
| 1 Coggins Pl, Mascot, 2020 | CONFIRM_ADD_SUBPREMISES | PREMISE | 1 Coggins Place, Mascot NSW 2020 |
| 113 Railway St, Sydney, 2216 | ACCEPT | PREMISE | 113 Railway Street, Sydney NSW 2216 |
| 55 Crockford St, Port Melbourne, 3207 | ACCEPT | PREMISE | 55 Crockford Street, Port Melbourne VIC 3207 |

**澳大利亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Ground Level Chatswood Chase Shopping Centre outside entrance David Jones, Sydney, 2067 | FIX | ROUTE | Ground Floor, Entrance, Sydney NSW 2067 |
| Keith Burrows Theatre, UNSW, Sydney, 2033 | FIX | LOCALITY |  |
| Shop/10 Rockdale Plaza Dr, Sydney, 2216 | FIX | ROUTE | Shop 10, Rockdale Plaza Drive, Sydney NSW 2216 |
| Jells Road, Wheelers Hill, 3150 | FIX | ROUTE | Jells Road, Wheelers Hill VIC 3150 |

**澳大利亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Cabramatta Rd, Cabramatta, 2166 | CONFIRM | ROUTE | Cabramatta Road, NSW 2166 |
| 282 Oxford St Suite 202, Bondi Junction, 2022 | CONFIRM | PREMISE | Suite 202, 282 Oxford Street, Bondi Junction NSW 2021 |
| Brushbox Drive, Melbourne, 3072 | CONFIRM | ROUTE | Brushbox Street, Melbourne VIC 3072 |
| Shop 1, Ground Floor/96 Parramatta Rd, Sydney, 2050 | CONFIRM | PREMISE | Shop 1, 96 Parramatta Road, Sydney NSW 2140 |

**德国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Heinrich-Hertz-Straße 3D, Kleinmachnow, 14532 | FIX | ROUTE | Heinrich-Hertz-Straße 3D, 14532 Kleinmachnow |
| Am Zwirngraben 6-7, Berlin, 10178 | FIX | ROUTE | Am Zwirngraben 6-7, 10178 |
| Brommystraße 1, Berlin, 10997 | FIX | ROUTE | Brommystraße 1, 10997 |
| Heidestr. 65-68, Berlin, 10557 | FIX | ROUTE | Heidestraße 65-68, 10557 |

**德国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Kastanienallee 55, Berlin, 12627 | CONFIRM | PREMISE | Nossener Straße 55, 12627 Hellersdorf |
| Hauptbahnhof 1, Berlin, 10557 | CONFIRM | PREMISE | Bartningallee 1, 10557 Hansaviertel |
| Mierendorffplatz 12, Berlin, 10589 | CONFIRM | PREMISE | Bonhoefferufer 12, 10589 Charlottenburg |
| Reischstrasse 13, Berlin, 14052 | CONFIRM | PREMISE | Reichsstraße 13, 14052 Westend |

**德国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Turmstr. 21/Haus M, Berlin, 10559 | ACCEPT | PREMISE | Turmstraße 21, 10559 Moabit |
| Unitb Consulting, Brunnenstraße 156, Berlin, 10115 | ACCEPT | PREMISE | Brunnenstraße 156, 10115 Mitte |
| Spenerstraße 15, Berlin, 10557 | ACCEPT | PREMISE | Spenerstraße 15, 10557 Moabit |
| Hardenbergstraße 9a, Berlin, 10623 | ACCEPT | PREMISE | Hardenbergstraße 9 A, 10623 Charlottenburg |

**法国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 10 Rue de Sévigné, Paris, 75004 | FIX | ROUTE | 10 Rue de Sévigné, 75004 |
| 60 Rue François 1er, Paris, 75008 | FIX | ROUTE | 60 Rue François 1er, 75008 |
| 1 Cour du Havre, Paris, 75008 | FIX | ROUTE | 1 Cour du Havre, 75008 |
| Rue Viala, Paris, 75015 | FIX | ROUTE | Rue Viala, 75015 |

**法国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Rives de Seine Habitat, 6 Rue Jacques Mazaud, Levallois-Perret, 92300 | ACCEPT | PREMISE | 6 Rue Jacques Mazaud, 92300 Levallois-Perret |
| 6 place de Belgique, Courbevoie, 92400 | ACCEPT | PREMISE | 6 Place de Belgique, 92400 Courbevoie |
| 6 Rue Rataud, Paris, 75005 | ACCEPT | PREMISE | 6 Rue Rataud, 75005 Paris 5e Arrondissement |
| Les Films du Cap, 20 Rue Oberkampf, Paris, 75011 | ACCEPT | PREMISE | 20 Rue Oberkampf, 75011 Paris 11e Arrondissement |

**法国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 2 Place Charles de Gaulle, Paris, 75017 | CONFIRM | ROUTE | 2 Place Charles de Gaulle, 75017 |
| Synthelabo Recherche, 31 Ave Paul Vaillant-Couturier, Bagneux, 92220 | CONFIRM | PREMISE | 31 Avenue Paul Vaillant-Couturier, 94250 Gentilly |
| 99/101 Rue de Sèvres, Paris, 75272 | CONFIRM | ROUTE | 99/101 Rue de Sèvres, 75272 |
| Centre Commercial Saint-Lazare Paris, 1 Cour de Rome, Paris, 75003 | CONFIRM | PREMISE | 1 Cour de Rome, 75003 Paris 3e Arrondissement |

**荷兰 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Wethouder Driessenstraat, Amsterdam | FIX | ROUTE | Wethouder Driessenstraat |
| Joop Woortmanplein, Amsterdam, 1069 PT | FIX | ROUTE | Joop Woortmanplein, 1069 PT |
| Schiphol Airport, Amsterdam | FIX | LOCALITY |  |
| Staalmeesterslaan, Amsterdam, 1057 NV | FIX | ROUTE | Staalmeesterslaan, 1057 NV |

**荷兰 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Nico Broekhuysenweg 22, Amsterdam, 1067 HT | ACCEPT | PREMISE | Nico Broekhuysenweg 22, 1067 HT Amsterdam |
| Herengracht 449A, Amsterdam, 1017 BR | ACCEPT | PREMISE | Herengracht 449A, 1017 BR Amsterdam |
| Herengracht 514, Amsterdam, 1017 CC | ACCEPT | PREMISE | Herengracht 514, 1017 CC Amsterdam |
| Oosteinderweg 287F-02, Aalsmeer, 1432 AW | ACCEPT | PREMISE | Oosteinderweg 287F, 1432 AW Aalsmeer |

**荷兰 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Distelweg 93, Amsterdam, 1031 | CONFIRM | ROUTE | Distelweg 93 |
| Wingerdweg, Amsterdam | CONFIRM | ROUTE | Wingerdweg |
| Evert V/D Beekstraat 202, Luchthaven Schiphol, 1118 CP | CONFIRM | PREMISE | Evert van de Beekstraat 202, 1118 CP Schiphol |

**阿联酋 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Sanctuary Tower - Office NO.105, دبي, 341296 | FIX | OTHER |  |
| Al Tawoon, الشارقة, 06 | FIX | OTHER |  |
| Grosvenor House, Dubai | FIX | OTHER |  |
| 8/F, ICD Brookfield Place, Dubai | FIX | LOCALITY |  |

**阿联酋 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Al Hammadi 01, Ras Al Khor Industrial First, دبي | CONFIRM | ROUTE | 01 Ras Al Khor Road |
| 27/2 10th St, دبي | CONFIRM | ROUTE | 27/2 10th Street |
| Saraya Cafe & Roasters SHJ Warehouses Land Service Road Industrial Area 18, Sharjah, 14053 | CONFIRM | ROUTE | 18 Service Road |
| Ground Floor، Auto Center Building - Showroom#5 - Office #105 22A St, دبي, 22542 | CONFIRM | ROUTE | #105, 22a Street |

**阿联酋 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Sharjah Industrial Area 17/ 7CJV+C7 S102 | ACCEPT | PREMISE_PROXIMITY | 17, Muhaisnah 5, 7HQQ7CJV+C7 |
| Al Hubob St - Dubai Marina, Ground Floor, Marina Byblos Hotel | ACCEPT | PREMISE_PROXIMITY | Ground Floor, Marina Byblos Hotel, Al Hubob Street, Dubai Marina |
| Tamani Arts Building - Al Asayel St - Business Bay - Dubai, دبي, <<not-applicable>> | ACCEPT | PREMISE_PROXIMITY | Tamani Arts Building, Al Asayel Street, Business Bay |
| Duja Tower, Sheikh Zayed Road, World Trade Center Area, دبي, 333840 | ACCEPT | PREMISE_PROXIMITY | World Trade Center, Sheikh Zayed Road (south) |

**沙特 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Prince Muhammad Ibn Saad Ibn Abdulaziz Rd, الرياض, 13512 | CONFIRM | ROUTE | Alamir Mohamed Ibn Saad Ibn Abdelaziz Road, 13512 |
| Prince Ahmad Bin Abdulaziz Street Riyadh, الرياض, 11461 | CONFIRM | ROUTE | Ahmad, 11461 |
| Saeed Bin Zaid St, الرياض | CONFIRM | ROUTE | Saeed Bin Zaid |
| شارع الطائف, الرياض, 34439 | CONFIRM | ROUTE | الطائف, 34439 |

**沙特 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| hitteen, الرياض, 11411 | FIX | LOCALITY |  |
| https://goo.gl/maps/heC8gbHXxjT1kkKG9, الرياض | FIX | OTHER |  |
| Riyadh, الرياض, 2233 | FIX | OTHER |  |
| الرياض, الرياض, 1200 | FIX | OTHER |  |

**沙特 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| HH6V+683، العوالي، الرياض 14926، المملكة العربية السعودية, الرياض, 14926 | ACCEPT | PREMISE_PROXIMITY | حي العوالي, 14926, 7HP8HH6V+68 |
| MMGG+73P, Al Takhassousi, الرياض, 12312 | ACCEPT | PREMISE_PROXIMITY | Al Takhassousi Road, Al Mu'tamarat, 12312, 7HP8MMGG+73 |
| HJC3+M7R, الرياض, 14925 | ACCEPT | PREMISE_PROXIMITY | ظهرة نمار, 14925, 7HP8HJC3+M7 |

**马来西亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| M3 Mall, Bandar Kuala Lumpur | FIX | LOCALITY |  |
| The Square @ One City, Jalan USJ 25/1C, Subang Jaya, 47650 | FIX | LOCALITY |  |
| malaysia, Bandar Kuala Lumpur, 55100 | FIX | LOCALITY |  |
| Desa Business Centre, Kuala Lumpur, 58100 | FIX | LOCALITY |  |

**马来西亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Damansara Damai, Petaling Jaya | CONFIRM | ROUTE | Jalan Damansara, Petaling Jaya |
| F-11-3, Pusat Bandar Bukit Jalil, Jalan Jalil Utama 2, 57000, Kuala Lumpur, Malaysia., Kua | CONFIRM | ROUTE | 11-3 Persiaran Jalil Utama, 57000 |
| no 22 jalan AU1A/4C Taman Keramat Permai, Ampang, 68000 | CONFIRM | ROUTE | 4C Jalan Keramat, 68000 |
| Lembah Pantai, Petaling Jaya | CONFIRM | ROUTE | Jalan Lembah, Petaling Jaya |

**马来西亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 2 Jalan SS 4B/2, Petaling Jaya, 47301 | ACCEPT | ROUTE | 2 Jalan SS 4B/2, Petaling Jaya, 47301 |
| Suite 7,29-6 block E-1, Jalan PJU 1/42, Petaling Jaya, 47301 | ACCEPT | ROUTE | Suite 7, 1 Jalan PJU 1/42, Petaling Jaya, 47301 |
| 8 Jalan Sultan Ismail, Bandar Kuala Lumpur, 50250 | ACCEPT | ROUTE | 8 Jalan Sultan Ismail, Kuala Lumpur, 50250 |
| 9 Square Hotel, 5 Jalan USJ Sentral 3, Subang Jaya, 47600 | ACCEPT | ROUTE | 5 Jalan USJ Sentral 3, Subang Jaya, 47600 |

**印尼 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Jl. Raya Bekasi No.KM 26, RW.5, Jakarta Timur, 13960 | CONFIRM | ROUTE | Jalan Raya Bekasi 26, Jakarta Timur, 13960 |
| Pusdiklat Kemenag RI Ciputat, Tangerang Selatan | CONFIRM | ROUTE | Jalan Tangerang |
| Jl. SMPN 207 No.77, RT.4/RW.8, Jakarta Barat, 11630 | CONFIRM | ROUTE | Jalan SMPN 45 77, Jakarta Barat, 11630 |
| Jl. Kenanga No.10 7, RT.7/RW.2, Jakarta Selatan, 12560 | CONFIRM | ROUTE | Jalan Kenanga 10, Jakarta Selatan, 12560 |

**印尼 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Jl. Kamal Raya No.32 Blk C7, RT.6/RW.14, Jakarta Barat, 11730 | ACCEPT | ROUTE | Jalan Kamal Raya 32, Jakarta Barat, 11730 |
| Jalan Senopati 8B, Jakarta, 12190 | ACCEPT | ROUTE | Jalan Senopati 8B, 12190 |
| Jalan Percetakan Negara II, Blok J No.21-22, RT 03 / RW 03, Johar Baru, Jl. Percetakan Neg | ACCEPT | ROUTE | Jalan Percetakan Negara 21-22, Jakarta Pusat, 10560 |
| Jalan Boulevard Barat Raya 7, Jakarta, 14240 | ACCEPT | ROUTE | Jalan Boulevard Barat Raya 7, 14240 |

**印尼 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| jakarta, Jakarta | FIX | OTHER |  |
| 14, RT.14/RW.3, Jakarta Selatan, 12520 | FIX | LOCALITY |  |
| Kompl Duta Mas Bl A-3/45, Jakarta Barat, 11720 | FIX | LOCALITY |  |
| Jakarta, Jakarta | FIX | OTHER |  |

**泰国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 69 Phra Ngoen Market, 8 Soi Wat Pra Nguen, บางใหญ่, 11140 | FIX | LOCALITY |  |
| Nawamin 96 Alley, กรุงเทพมหานคร, 10230 | FIX | LOCALITY |  |
| อ่อนนุช, กรุงเทพมหานคร, 10250 | FIX | LOCALITY |  |
| 111/150 Moo 9, Bang Phut, Mo Town Villege Chaengwattana Rd, ปากเกร็ด, 11120 | FIX | LOCALITY |  |

**泰国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| ร้านลักชูรี่ เนลล์ บายนุ่น 43/5หมู่3 หน้าตลาดมนวดี ติดกับห้างทองศรสุวรรณ 2 ต.พิมลราช, บางบ | CONFIRM | ROUTE | 3 ซอยสุวรรณ, 11110 |
| กาญจนาภิเษก, นนทบุรี, 11110 | CONFIRM | ROUTE | ถนนกาญจนาภิเษก, 11110 |
| 101 สุขุมวิท, กรุงเทพมหานคร, 10260 | CONFIRM | ROUTE | 101 สุขุมวิท 7, 10260 |
| 393 หมู่ที่9, ถนนประชาอุทิศ, กรุงเทพมหานคร, 10140 | CONFIRM | ROUTE | 393 ถนนประชาอุทิศ, 10140 |

**泰国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| ปาก Tha Din Daeng 12, กรุงเทพมหานคร, 10600 | ACCEPT | ROUTE | 12 ท่าดินแดง 1, ท่าดินแดง, 10600 |
| 2 ถนน เทพารักษ์, สมุทรปราการ, 10270 | ACCEPT | ROUTE | 2 ถนนเทพารักษ์, 10270 |
| 98 ถนน สุขุมวิท, กรุงเทพมหานคร, 10110 | ACCEPT | ROUTE | 98 ถนนสุขุมวิท, 10110 |
| 16/4 ซอยนานาเหนือ ถนนสุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพมหานคร 10110 ไทย, กรุงเทพมห | ACCEPT | ROUTE | 16/4 ถนนสุขุมวิท, คลองเตยเหนือ, 10110 |

**越南 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 21 Hoàng Diệu, Quận 4, 70000 | CONFIRM | ROUTE | 21 Hoàng Diệu, 70000 |
| 51-49 Hồ Thị Kỷ, Phường 1, Quận 10, Thành phố Hồ Chí Minh, Việt Nam, Quận 5, 700000 | CONFIRM | ROUTE | 51-49 Hồ Thị Kỷ, 700000 |
| 71 Hoàng Hoa Thám, Quận Tân Bình, 72106 | CONFIRM | ROUTE | Hẻm 71 Đường Hoàng Hoa Thám, 72106 |
| 3 Khu Đô Thị Geleximco Lê Trọng Tấn, Quận Hà Đông, 12114 | CONFIRM | ROUTE | 3 Lê Trọng Tấn, 12114 |

**越南 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Phường Phước Long, Dĩ An, 700000 | FIX | LOCALITY |  |
| 458/41 Hẻm 458 Đường 3/2, Quận 10, 72510 | FIX | LOCALITY |  |
| P6-09, KDC PHI Long 5, Huyện Bình Chánh, 71812 | FIX | LOCALITY |  |
| 3 Đường 40, Thủ Đức, 50000 | FIX | LOCALITY |  |

**越南 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 178/23/4 Hẻm 178 Phan Đăng Lưu, Quận Phú Nhuận, 72213 | ACCEPT | ROUTE | 178/23/4 Hẻm 178 Phan Đăng Lưu, Phường Phú Nhuận, 72213 |
| 62/46 Hẻm 62 Trương Công Định, Quận Tân Bình, 72112 | ACCEPT | ROUTE | 62/46 Hẻm 62 Trương Công Định, Phường Tân Bình, 72112 |
| 368 Đường Cộng Hòa, Quận Tân Bình, 72110 | ACCEPT | ROUTE | 368 Cộng Hòa, Phường Tân Bình, 72110 |
| 284 Đường Tân Hương, Quận Tân Phú, 72011 | ACCEPT | ROUTE | 284 Tân Hương, Phường Tân Phú, 72011 |

**菲律宾 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Office no 415, 417 4/F Unit 4 C&D Commerce and Industry Plaza Building, Taguig, 1634 | CONFIRM | PREMISE_PROXIMITY | Unit 4, Commerce and Industry Plaza, 415, 1634 |
| 720 B Bulacan St, Manila, 002 | CONFIRM | ROUTE | 720 Bulacan Street, Manila |
| 53 Anonas, Quezon City, 1102 | CONFIRM | ROUTE | 53 Anonas, Quezon City, 1102 |
| Provident Vill, 170 Cambridge, Marikina, 1804 | CONFIRM | ROUTE | 170 Cambridge, 1804 |

**菲律宾 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Sampaloc Manila, Manila | FIX | LOCALITY |  |
| Two E-com Bldg, Pasay City, 1300 | FIX | LOCALITY |  |
| Manila, Manila, <<not-applicable>> | FIX | LOCALITY |  |
| Brgy, One Spatial Condominium Amang Rodriguez Pasig City 620 Kensington Bldg One Spatial C | FIX | LOCALITY |  |

**菲律宾 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 486 Lt. Artiaga, San Juan, 1500 | ACCEPT | ROUTE | 486 Artiaga, San Juan, 1500 |
| 303 building tullahan road, tandang sora extention, Santa Quiteria Rd, Caloocan City, 1402 | ACCEPT | ROUTE | 303 Santa Quiteria Road, Caloocan, 1402 |
| 537 J Fabella St, Mandaluyong, 1550 | ACCEPT | ROUTE | 537 J. Fabella Street, Mandaluyong, 1550 |
| G/F, Old Free Press 700-04 Corner Soler Street, Manila, 1002 | ACCEPT | ROUTE | 700-04 Soler Street, Manila, 1002 |

