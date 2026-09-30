# 多市场评测报告（自动生成）

- 真实地址：各城市留出的 20% 商户（不在参考库里）的自填地址，标准答案为商户坐标（弱标注）
- 合成地址：按各市场写法渲染的测试部分道路（AI 解析器训练时没见过），标准答案已知
- 解析方式：rules = 规则 + 地名表；crf = 机器学习（条件随机场）；hybrid = 两者都出候选，由参考数据裁决
- 判对标准（真实地址）：门牌级 ≤ 250 米、楼宇级 ≤ 400 米、道路级为该道路经过商户 250 米内；"偏差 >1 公里"的静默错误不是商户坐标不准能解释的，是真正的错

## 真实商户地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 1000 | 73.8% | 4.6% | 0.9% | 12.1% | 4.6% | 4.0% | 1.4% | 87.5% | 2 |
| 澳大利亚（AU） | A | crf | 1000 | 68.2% | 2.4% | 2.9% | 18.8% | 4.2% | 3.5% | 1.4% | 86.9% | 1 |
| 澳大利亚（AU） | A | hybrid | 1000 | 74.3% | 4.3% | 0.9% | 11.3% | 5.1% | 4.1% | 1.5% | 87.7% | 3 |
| 德国（DE） | A | rules | 1000 | 91.9% | 1.8% | 0.5% | 2.3% | 3.0% | 0.5% | 0.1% | 96.4% | 1 |
| 德国（DE） | A | crf | 1000 | 85.7% | 1.4% | 1.2% | 8.7% | 2.5% | 0.5% | 0.1% | 93.5% | 1 |
| 德国（DE） | A | hybrid | 1000 | 93.9% | 1.2% | 0.4% | 2.2% | 1.7% | 0.6% | 0.1% | 97.2% | 2 |
| 法国（FR） | A | rules | 1000 | 89.6% | 2.5% | 0.5% | 5.6% | 1.2% | 0.6% | 0.1% | 96.1% | 1 |
| 法国（FR） | A | crf | 1000 | 87.4% | 4.2% | 1.0% | 5.5% | 1.3% | 0.6% | 0.1% | 96.3% | 1 |
| 法国（FR） | A | hybrid | 1000 | 90.3% | 2.4% | 0.4% | 5.3% | 1.0% | 0.6% | 0.1% | 96.9% | 2 |
| 荷兰（NL） | A | rules | 1000 | 82.1% | 5.3% | 1.0% | 8.7% | 1.0% | 1.9% | 0.8% | 96.0% | 2 |
| 荷兰（NL） | A | crf | 1000 | 70.5% | 3.1% | 0.7% | 22.9% | 1.1% | 1.7% | 0.7% | 89.3% | 1 |
| 荷兰（NL） | A | hybrid | 1000 | 83.1% | 4.6% | 0.8% | 8.6% | 0.7% | 2.2% | 1.0% | 96.5% | 3 |
| 阿联酋（AE） | B | rules | 1000 | 2.3% | 29.3% | 12.1% | 24.3% | 30.8% | 1.2% | 0.9% | 19.6% | 4 |
| 阿联酋（AE） | B | crf | 1000 | 0.9% | 16.8% | 7.5% | 53.9% | 20.4% | 0.5% | 0.4% | 9.6% | 2 |
| 阿联酋（AE） | B | hybrid | 1000 | 2.4% | 30.0% | 11.4% | 20.6% | 34.4% | 1.2% | 0.9% | 20.0% | 5 |
| 沙特（SA） | B | rules | 1000 | 3.0% | 28.6% | 10.5% | 13.9% | 43.3% | 0.7% | 0.6% | 19.3% | 3 |
| 沙特（SA） | B | crf | 1000 | 2.2% | 27.0% | 15.9% | 22.3% | 31.7% | 0.9% | 0.6% | 19.8% | 3 |
| 沙特（SA） | B | hybrid | 1000 | 3.1% | 33.7% | 7.6% | 11.7% | 43.1% | 0.8% | 0.6% | 21.8% | 6 |
| 马来西亚（MY） | C | rules | 1000 | 33.4% | 36.6% | 4.9% | 5.3% | 16.2% | 3.6% | 1.7% | 60.7% | 4 |
| 马来西亚（MY） | C | crf | 1000 | 29.1% | 39.9% | 10.7% | 6.4% | 11.3% | 2.6% | 1.4% | 62.2% | 2 |
| 马来西亚（MY） | C | hybrid | 1000 | 34.0% | 38.7% | 3.3% | 3.3% | 17.1% | 3.6% | 1.7% | 63.2% | 5 |
| 印尼（ID） | C | rules | 1000 | 28.6% | 26.4% | 2.9% | 3.7% | 35.0% | 3.4% | 1.0% | 38.1% | 2 |
| 印尼（ID） | C | crf | 1000 | 9.9% | 32.0% | 28.2% | 8.4% | 21.0% | 0.5% | 0.2% | 42.8% | 5 |
| 印尼（ID） | C | hybrid | 1000 | 28.6% | 29.5% | 2.4% | 3.6% | 32.6% | 3.3% | 1.0% | 41.5% | 7 |
| 泰国（TH） | C | rules | 1000 | 17.3% | 41.8% | 9.2% | 8.9% | 20.0% | 2.8% | 1.0% | 29.3% | 6 |
| 泰国（TH） | C | crf | 1000 | 11.5% | 28.9% | 26.1% | 19.3% | 11.8% | 2.4% | 1.0% | 19.6% | 3 |
| 泰国（TH） | C | hybrid | 1000 | 17.3% | 43.1% | 8.5% | 8.0% | 20.1% | 3.0% | 1.2% | 29.8% | 9 |
| 越南（VN） | C | rules | 1000 | 8.6% | 57.7% | 2.0% | 4.0% | 26.2% | 1.5% | 1.0% | 47.9% | 2 |
| 越南（VN） | C | crf | 1000 | 8.5% | 41.1% | 20.0% | 15.4% | 13.9% | 1.1% | 0.7% | 40.8% | 3 |
| 越南（VN） | C | hybrid | 1000 | 11.0% | 56.5% | 1.5% | 3.9% | 25.1% | 2.0% | 1.3% | 48.0% | 5 |
| 菲律宾（PH） | C | rules | 1000 | 21.1% | 32.5% | 13.3% | 8.1% | 23.4% | 1.6% | 0.5% | 35.8% | 3 |
| 菲律宾（PH） | C | crf | 1000 | 11.8% | 38.5% | 21.7% | 8.6% | 18.9% | 0.5% | 0.1% | 39.8% | 3 |
| 菲律宾（PH） | C | hybrid | 1000 | 22.0% | 39.7% | 7.2% | 4.7% | 24.8% | 1.6% | 0.5% | 41.9% | 5 |

## 合成地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 1000 | 82.5% | 8.7% | 0.0% | 5.8% | 1.8% | 1.2% | 0.2% | 97.6% | 1 |
| 澳大利亚（AU） | A | crf | 1000 | 86.7% | 5.6% | 0.0% | 5.8% | 0.7% | 1.2% | 0.2% | 98.9% | 1 |
| 澳大利亚（AU） | A | hybrid | 1000 | 86.4% | 5.9% | 0.0% | 5.8% | 0.7% | 1.2% | 0.2% | 98.9% | 3 |
| 德国（DE） | A | rules | 1000 | 79.6% | 6.8% | 0.0% | 5.5% | 5.4% | 2.7% | 0.2% | 94.3% | 2 |
| 德国（DE） | A | crf | 1000 | 83.0% | 9.7% | 0.0% | 4.9% | 2.2% | 0.2% | 0.2% | 97.3% | 1 |
| 德国（DE） | A | hybrid | 1000 | 81.9% | 8.7% | 0.0% | 4.6% | 2.1% | 2.7% | 0.2% | 97.5% | 3 |
| 法国（FR） | A | rules | 1000 | 89.5% | 3.1% | 0.0% | 5.1% | 1.9% | 0.4% | 0.0% | 97.4% | 1 |
| 法国（FR） | A | crf | 1000 | 88.2% | 6.6% | 0.0% | 4.3% | 0.9% | 0.0% | 0.0% | 99.2% | 1 |
| 法国（FR） | A | hybrid | 1000 | 90.6% | 4.2% | 0.0% | 4.3% | 0.6% | 0.3% | 0.0% | 99.2% | 2 |
| 荷兰（NL） | A | rules | 1000 | 86.7% | 7.0% | 0.0% | 4.2% | 0.7% | 1.4% | 0.0% | 99.4% | 3 |
| 荷兰（NL） | A | crf | 1000 | 87.3% | 8.0% | 0.0% | 4.0% | 0.1% | 0.6% | 0.0% | 100.0% | 1 |
| 荷兰（NL） | A | hybrid | 1000 | 87.1% | 7.4% | 0.0% | 3.8% | 0.3% | 1.4% | 0.0% | 100.0% | 3 |
| 阿联酋（AE） | B | rules | 1000 | 1.9% | 45.3% | 0.0% | 34.7% | 18.0% | 0.1% | 0.0% | 52.6% | 2 |
| 阿联酋（AE） | B | crf | 1000 | 7.0% | 69.0% | 0.0% | 2.0% | 21.9% | 0.1% | 0.0% | 72.9% | 1 |
| 阿联酋（AE） | B | hybrid | 1000 | 7.0% | 69.2% | 0.0% | 1.2% | 22.5% | 0.1% | 0.0% | 73.1% | 3 |
| 沙特（SA） | B | rules | 1000 | 10.2% | 66.8% | 0.0% | 7.3% | 15.7% | 0.0% | 0.0% | 76.2% | 2 |
| 沙特（SA） | B | crf | 1000 | 13.1% | 79.8% | 0.0% | 0.6% | 6.4% | 0.1% | 0.0% | 91.2% | 1 |
| 沙特（SA） | B | hybrid | 1000 | 13.1% | 79.7% | 0.0% | 0.4% | 6.7% | 0.1% | 0.0% | 91.0% | 3 |
| 马来西亚（MY） | C | rules | 1000 | 18.7% | 71.6% | 0.0% | 2.4% | 7.3% | 0.0% | 0.0% | 89.8% | 2 |
| 马来西亚（MY） | C | crf | 1000 | 23.2% | 72.9% | 0.0% | 0.1% | 3.8% | 0.0% | 0.0% | 95.0% | 1 |
| 马来西亚（MY） | C | hybrid | 1000 | 23.8% | 72.0% | 0.0% | 0.0% | 4.2% | 0.0% | 0.0% | 94.7% | 3 |
| 印尼（ID） | C | rules | 1000 | 22.5% | 66.6% | 0.0% | 0.3% | 10.6% | 0.0% | 0.0% | 88.8% | 2 |
| 印尼（ID） | C | crf | 1000 | 32.2% | 61.3% | 0.0% | 0.3% | 6.2% | 0.0% | 0.0% | 92.4% | 2 |
| 印尼（ID） | C | hybrid | 1000 | 32.7% | 60.6% | 0.0% | 0.0% | 6.7% | 0.0% | 0.0% | 92.2% | 3 |
| 泰国（TH） | C | rules | 1000 | 20.2% | 74.1% | 0.0% | 1.8% | 3.9% | 0.0% | 0.0% | 93.1% | 3 |
| 泰国（TH） | C | crf | 1000 | 24.2% | 72.7% | 0.0% | 0.4% | 2.6% | 0.1% | 0.0% | 95.1% | 1 |
| 泰国（TH） | C | hybrid | 1000 | 24.6% | 72.3% | 0.0% | 0.2% | 2.8% | 0.1% | 0.0% | 95.1% | 5 |
| 越南（VN） | C | rules | 1000 | 30.8% | 58.2% | 0.0% | 1.6% | 9.2% | 0.2% | 0.0% | 90.2% | 2 |
| 越南（VN） | C | crf | 1000 | 38.6% | 57.4% | 0.0% | 0.0% | 4.0% | 0.0% | 0.0% | 95.2% | 2 |
| 越南（VN） | C | hybrid | 1000 | 38.7% | 56.1% | 0.0% | 0.0% | 5.2% | 0.0% | 0.0% | 94.4% | 5 |
| 菲律宾（PH） | C | rules | 1000 | 20.9% | 66.0% | 0.0% | 3.3% | 9.8% | 0.0% | 0.0% | 85.8% | 2 |
| 菲律宾（PH） | C | crf | 1000 | 26.3% | 63.0% | 0.0% | 0.2% | 10.4% | 0.1% | 0.0% | 88.1% | 2 |
| 菲律宾（PH） | C | hybrid | 1000 | 26.6% | 64.5% | 0.0% | 0.0% | 8.8% | 0.1% | 0.0% | 89.0% | 4 |

## 错误样例（规则解析，真实地址）

**澳大利亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 872 Canterbury Rd, Sydney, 2196 | FIX | ROUTE | 872 Canterbury Road, Sydney NSW 2196 |
| Cnr Davies &, Arab Rd, Sydney, 2211 | FIX | ROUTE | Arab Road, Sydney NSW 2211 |
| Unit 2/153/155 Orchardleigh St, Sydney, 2161 | FIX | ROUTE | Unit 2/153/155, Orchardleigh Street, Sydney NSW 2161 |
| Oak Rd N, Kirrawee, 2232 | FIX | ROUTE | Oak Road, Kirrawee NSW 2232 |

**澳大利亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 155 Queen St Level 10, Melbourne, 3000 | ACCEPT | PREMISE | Level 10, 155 Queen Street, Melbourne VIC 3000 |
| 345 Pacific Hwy Suite 9, North Sydney, 2060 | ACCEPT | PREMISE | Suite 9, 345 Pacific Highway, North Sydney NSW 2060 |
| 233 Riversdale Road, Hawthorn, VIC, 3122, 3122 | ACCEPT | PREMISE | 233 Riversdale Road, Hawthorn VIC 3122 |
| 25A Barker Rd, Sydney, 2135 | ACCEPT | PREMISE | 25A Barker Road, Sydney NSW 2135 |

**澳大利亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Building A, Level, 1, Room A.1.08, Lidcombe, 2141 | CONFIRM | PREMISE | Level 1, 1 Eucalyptus Street, LIDCOMBE NSW 2141 |
| 89-93 High St, Melbourne, 3101 | CONFIRM | PREMISE | 93 High Street, Melbourne VIC 3070 |
| 9A George St Suite 2, Sydney, 2137 | CONFIRM | PREMISE | Suite 2, 9A George Street, Sydney NSW 2166 |
| KINGS ARCADE, Suites 11-12, 2/978 High St, Melbourne, 3143 | CONFIRM | PREMISE | Unit 2, 11 High Street, Melbourne VIC 3181 |

**德国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Iranische Straße 6, Berlin, 13347 | FIX | ROUTE | Iranische Straße 6, 13347 |
| Alt-Mahlsdorf 121 a, Berlin, 12623 | FIX | ROUTE | Alt-Mahlsdorf 121, 12623 |
| Lindauer Allee 35, Berlin, 13407 | FIX | ROUTE | Lindauer Allee 35, 13407 |
| Köllnischer Park, Wallstraße 51, Berlin, 10179 | FIX | ROUTE | Wallstraße 51, 10179 |

**德国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Kohlfurter Straße 1, Berlin, 10999 | CONFIRM | PREMISE | Paul-Lincke-Ufer 1, 10999 Kreuzberg |
| Ausbau Kirschberg 23, Neuhausen/Spree, 03058 | CONFIRM | ROUTE | Ausbau 23, 03058 |
| Alt-Kladow 22, Berlin, 14089 | CONFIRM | PREMISE | Kafkastraße 22, 14089 Kladow |
| Schloßstraße, Berlin, 10178 | CONFIRM | PREMISE | Schloßstraße 10, 12163 Steglitz |

**德国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Lennéstraße 13, Berlin, 10785 | ACCEPT | PREMISE | Lennéstraße 13, 10785 Tiergarten |
| Hubertusbader Straße 35, Berlin, 14193 | ACCEPT | PREMISE | Hubertusbader Straße 35, 14193 Grunewald |
| Bruno-Bürgel-Weg 70 - 80, Berlin, 12439 | ACCEPT | PREMISE | Bruno-Bürgel-Weg 70, 12439 Niederschöneweide |
| Rothe Management, Großbeerenstraße 262, Potsdam, 14480 | ACCEPT | PREMISE | Großbeerenstraße 262, 14480 Potsdam |

**法国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 35 Boulevard de Rochechouart, Paris, 75009 | FIX | ROUTE | 35 Boulevard de Rochechouart, 75009 |
| 11 Place des Victoires, Asnières-sur-Seine, 92600 | FIX | ROUTE | 11 Place des Victoires, 92600 |
| 40 Avenue Pierre 1er de Serbie, Paris, 75008 | FIX | ROUTE | 40 Rue Pierre, 75008 |
| Avenue du Maine, Paris, 75015 | FIX | ROUTE | Avenue du Maine, 75015 |

**法国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 14 Rue Paul Éluard, Charenton-le-Pont, 94220 | CONFIRM | PREMISE | 14 Rue de Charenton, 75012 Paris 12e Arrondissement |
| 53 Rue de La Rochefoucauld, Paris, 75009 | CONFIRM | PREMISE | 53 Rue de la Rochefoucauld, 92100 Boulogne-Billancourt |
| 5 Rue Moret, Paris, 75011 | CONFIRM | PREMISE | 5 Rue Morel, 92120 Montrouge |
| 2 Rue De Reuilly75012 Paris, Paris, 75012 | CONFIRM | PREMISE | 2 Rue François Truffaut, 75012 Paris 12e Arrondissement |

**法国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 10 Port de la Gare, Paris, 75013 | ACCEPT | PREMISE | 10 Port de la Gare, 75013 Paris 13e Arrondissement |
| 34 Rue Camille Pelletan, Levallois-Perret, 92300 | ACCEPT | PREMISE | 34 Rue Camille Pelletan, 92300 Levallois-Perret |
| 149 Rue de Sèvres, Paris, 75015 | ACCEPT | PREMISE | 149 Rue de Sèvres, 75015 Paris 15e Arrondissement |
| 7 rue Baudin, Courbevoie, 92400 | ACCEPT | PREMISE | 7 Rue Baudin, 92400 Courbevoie |

**荷兰 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Schipluidenlaan 4, Amsterdam, 1062 MZ | CONFIRM | PREMISE | Schipluidenlaan 4, 1062 HE Amsterdam |
| Kon. Wilhelminaplein 13, 1062HH, Amsterdam, 1062 HH | CONFIRM | PREMISE | Wilhelminaplein 13, 1182 ER Amstelveen |
| Dorpsstraat, Ouderkerk a/d Amstel | CONFIRM | ROUTE | Dorpsstraat |
| Kerk straat, Amsterdam | CONFIRM | ROUTE | Kerkstraat |

**荷兰 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Rokin, Amsterdam, 1012KR | FIX | ROUTE | Rokin, 1012 KR |
| Stationsplein, 41l, Amsterdam, 1012 AB | FIX | ROUTE | Stationsplein-ZW 41L, 1012 AB |
| Asserring 93, Amstelveen, 1187 SM | FIX | ROUTE | Asserring 93, 1187 SM Amstelveen |
| Gedempt Hamerkanaal 267, Amsterdam, 1021 KP | FIX | ROUTE | Gedempt Hamerkanaal 267, 1021 KP |

**荷兰 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Machineweg 1, Halfweg, 1165 NB | ACCEPT | PREMISE | Machineweg 1, 1165 NB Halfweg |
| Rozengracht 220B, Amsterdam, 1016 NL | ACCEPT | PREMISE | Rozengracht 220B, 1016 NL Amsterdam |
| Buitenveldert, Doornburg 2, Amsterdam, 1081 JB | ACCEPT | PREMISE | Doornburg 2, 1081 JB Buitenveldert |
| Paasheuvelweg 25, Amsterdam, 1105 BP | ACCEPT | PREMISE | Paasheuvelweg 25, 1105 BP Amsterdam |

**阿联酋 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Al Shoala Building - Block E 306 - 308 - near Deira City Center, دبي, 14476 | FIX | LOCALITY |  |
| Dubai Island | FIX | LOCALITY |  |
| Shop 7, Building 5, دبي, 00000 | FIX | OTHER |  |
| Dubai, دبي, <<not-applicable>> | FIX | OTHER |  |

**阿联酋 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 13th street, Umm Ramool, Rashidiya, دبي | CONFIRM | ROUTE | 13 Street |
| "First Floor, Mirdif City Centre, Sheikh Mohammed Bin Zayed Road (E311 Road), Mirdif", دبي | CONFIRM | ROUTE | Sheikh Mohammed bin Zayed Road, മിർദിഫ് |
| Office no. 111 Sheikh Hamdan Building, AI Khubaisi Area Near Abu Bakar Metro Station, DUBA | CONFIRM | PREMISE_PROXIMITY | Dubai UAE, 111 |
| Four Points by Sheraton Production City, Dubai, دبي | CONFIRM | PREMISE_PROXIMITY | Four Points By Sheraton |

**阿联酋 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Upper Level, The Boulevard, Jumeirah Emirates Towers, Sheikh Zayed Road, DIFC, دبي, 00000 | ACCEPT | PREMISE_PROXIMITY | The Boulevard, Sheikh Zayed Road (south), Jumeira |
| 8C8W+7G - Industrial AreaIndustrial Area 13 - Sharjah, الشارقة, 79681 | ACCEPT | PREMISE_PROXIMITY | 13, Mughaidir, 7HQQ8C8W+7G |
| Aveda Flagship Salon, Rooftop of Galleria Mall, Al Wasl Road, دبي | ACCEPT | PREMISE_PROXIMITY | Galleria Mall, Al Wasl Road |
| Oud Metha Metro Station, Oud Metha Rd, Near Rashid Hospital, Dubai | ACCEPT | PREMISE_PROXIMITY | Rashid Hospital, Oud Metha Road, ഔദ് മേത്ത |

**沙特 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Riyadh, الرياض, 11461 | FIX | LOCALITY |  |
| حي المرقب - الرياض, الرياض, 12345 | FIX | LOCALITY |  |
| طريق الثمامة، الصحافة، الرياض 13315, الرياض, 13315 | FIX | LOCALITY |  |
| KASCH, Riyadh | FIX | OTHER |  |

**沙特 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| King Abdullah Road, الرياض | CONFIRM | ROUTE | King Abdullah Rd |
| 8406 Prince Turki Ibn Abdulaziz Al Awwal Rd, An Nakhil Riyadh 12391 4990, الرياض, 12391 | CONFIRM | ROUTE | 4990 Prince Turki Bin Abdelaziz, 12391 |
| Al Sail Khabeer St. Al Ghadeer Dist., الرياض, 11461 | CONFIRM | ROUTE | Al Sail, 11461 |
| king saud university, الرياض, 00966 | CONFIRM | ROUTE | King Saud, 00966 |

**沙特 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| MM7M+P2C, الرياض | ACCEPT | PREMISE_PROXIMITY | Al Mutamarat District, 7HP8MM7M+P2 |
| ⁧مجمع الرصيص التجاري, RHOA6468, 6468 شارع العليا, الرياض, 12211 | ACCEPT | ROUTE | 6468 Al Olaya Street, 12211 |
| Kingdom Centre, Olaya Street, Olaya Dist, الرياض | ACCEPT | PREMISE_PROXIMITY | Kingdom Centre, Al Olaya Street |
| Northern Ring Rd الفرعي, PJR3+JM6, الرياض, 12394 | ACCEPT | PREMISE_PROXIMITY | Northern Ring Rd, Hittin, 12394, 7HP8PJR3+JM |

**马来西亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 145 Jalan Ampang, Bandar Kuala Lumpur, 50450 | CONFIRM | ROUTE | 145 Jalan Ampang, Kuala Lumpur, 50450 |
| Jalan Equine 10A, Bandar Kuala Lumpur, 43300 | CONFIRM | ROUTE | 10A Jalan Equine, 43300 |
| Jalan Sentul, Bandar Kuala Lumpur | CONFIRM | ROUTE | Jalan Sentul |
| No. 1.57, 1st  Floor South Citi Plaza Taman Serdang Perdana Seksyen 1, Seri Kembangan, 433 | CONFIRM | ROUTE | 1St Floor, 57 Jalan Serdang, 43300 |

**马来西亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Suria KLCC, Kuala Lumpur, 50088 | FIX | LOCALITY |  |
| 2nd Floor, 29, Jalan SS 22/23, Petaling Jaya, 47400 | FIX | LOCALITY |  |
| جامعه بوترا ماليزيا Universiti Putra Malaysia UPM, Seri Kembangan, 43000 | FIX | LOCALITY |  |
| Depan Empire, Subang Jaya | FIX | LOCALITY |  |

**马来西亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Heritage House, 33 Jalan Yap Ah Shak, Bandar Kuala Lumpur, 50300 | ACCEPT | PREMISE_PROXIMITY | Heritage House, 33 Jalan Yap Ah Shak, Kuala Lumpur, 50300 |
| 9 Jalan Suasana 2/7A, Cheras, 43200 | ACCEPT | ROUTE | 9 Jalan Suasana 2/7A, Cheras, 43200 |
| 19 Jalan Kolam Air Lama, Ampang, 68000 | ACCEPT | ROUTE | 19 Jalan Kolam Air Lama, Ampang, 68000 |
| 2 Jalan Manja 5, Batu, 52200 | ACCEPT | ROUTE | 2 Jalan Manja 5, 52200 |

**印尼 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Jl. Prima Raya, RT.4/RW.10, Jakarta Barat, 11820 | CONFIRM | ROUTE | Jalan Prima Raya, 11820 |
| Jl. R.A. Kartini No.1, RT.9/RW.7, Jakarta Selatan, 12440 | CONFIRM | ROUTE | Jalan R 1, Jakarta Selatan, 12440 |
| Bojong Kulur Gunung Putri, Bekasi, 16969 | CONFIRM | ROUTE | Jalan Putri, 16969 |
| Jl. Kihajar Dewantara, RT.02/RW.10, Tangerang Selatan, 15411 | CONFIRM | ROUTE | Jalan Tangerang, 15411 |

**印尼 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Esutubizi Centre 2nd Floor, Jl, Waltermonginsidi No. 71, Jakarta Selatan | FIX | LOCALITY |  |
| RT.14/RW.9, Jakarta Barat, 11810 | FIX | LOCALITY |  |
| Rukan Avenue No.8 007, RT.11/RW.8, Jakarta Timur, 13910 | FIX | LOCALITY |  |
| Jl. TPU Prumpung No.1, RW.2, Jakarta Timur, 13410 | FIX | LOCALITY |  |

**印尼 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Mall Bintaro Jaya X Change Lantai LG #129, Boulevard Bintaro Jaya, Bintaro Jaya Sektor 7 B | ACCEPT | ROUTE | #129, Jalan Boulevard Bintaro Jaya 2, Bintaro Jaya, 15117 |
| Jalan Pangeran Tubagus Angke 2, Jakarta, 11460 | ACCEPT | ROUTE | Jalan Pangeran Tubagus Angke 2, 11460 |
| Jalan Cikoko Timur II 2B, Jakarta, 12770 | ACCEPT | ROUTE | Jalan Cikoko Timur II 2B, 12770 |
| Sequis Center, Senayan, Kota Jakarta Selatan, Daerah Khusus Ibukota Jakarta, Indonesia 20t | ACCEPT | PREMISE_PROXIMITY | Unit 6, Daerah Khusus IbuKota Jakarta, Jalan Jenderal Sudirman 71, Jak |

**泰国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| พระยามนธาตุ, กรุงเทพมหานคร, 10150 | FIX | LOCALITY |  |
| 695/2 Ladprao, Saparnsong, Wangthonglang, กรุงเทพมหานคร, 10310 | FIX | LOCALITY |  |
| 120/36, กรุงเทพมหานคร, 10150 | FIX | LOCALITY |  |
| โครงการ Aqua อารีย์ 488, กรุงเทพมหานคร, 10400 | FIX | LOCALITY |  |

**泰国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 89/5 วิลเลต ทาวน์โฮม กาญจนาภิเษก, กรุงเทพมหานคร, 10150 | CONFIRM | ROUTE | 89/5 ถนนกาญจนาภิเษก, 10150 |
| ปตท.เสรีไทย, กรุงเทพมหานคร, 10240 | CONFIRM | ROUTE | ถนนเสรีไทย, 10240 |
| 200/1, ถนนกำแพงเพชร, กรุงเทพมหานคร, 10900 | CONFIRM | ROUTE | 200/1 ถนนกำแพงเพชร, 10900 |
| สินทวี, กรุงเทพมหานคร | CONFIRM | ROUTE | ซอยสินทวี |

**泰国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 93/136 ซอยเซ็นต์หลุยส์ 3 แยก 30 ถนนจันทน์, กรุงเทพมหานคร, 10120 | ACCEPT | ROUTE | 30 ถนนจันทน์, 10120 |
| 40 ถนน หทัยราษฎร์, กรุงเทพมหานคร, 10510 | ACCEPT | ROUTE | 40 ถนนหทัยราษฎร์, 10510 |
| 120 ถนน ราชปรารภ, กรุงเทพมหานคร, 10400 | ACCEPT | ROUTE | 120 ถนนราชปรารภ, 10400 |
| ศูนย์ราชการ แจ้งวัฒนะ, 120 ถนน แจ้งวัฒนะ, กรุงเทพมหานคร, 10210 | ACCEPT | ROUTE | 120 ถนนแจ้งวัฒนะ, 10210 |

**越南 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 46 Trần Huy Liệu Phú Nhuận, Quận Gò Vấp | CONFIRM | ROUTE | 46 Trần Huy Liệu, Phú Nhuận |
| Trần Quang Khải, phường Tân Định, Quận 1, Quận Bình Thạnh, 700000 | CONFIRM | ROUTE | 1 Trần Quang Khải, Phường Tân Định, 700000 |
| 36 Đường Tân Hòa, Dĩ An, 75308 | CONFIRM | ROUTE | 36 Tân Hòa, 75308 |
| 246 Lê Văn Việt, Phường Long Trường, Quận 7 | CONFIRM | ROUTE | 246 Lê Văn Việt |

**越南 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 43 Đường Lô C, Thủ Đức, 71312 | ACCEPT | ROUTE | 43 Đường Lô C, 71312 |
| 37 Đại Lộ Bình Dương, Thuận An, 75207 | ACCEPT | ROUTE | 37 Đại lộ Bình Dương, 75207 |
| 923 Đường Nguyễn Kiệm, Quận Gò Vấp, 71409 | ACCEPT | ROUTE | 923 Đường Nguyễn Kiệm, Phường Gò Vấp, 71409 |
| 435 Đường Lê Đức Thọ, Quận Gò Vấp, 71413 | ACCEPT | ROUTE | 435 Đường Lê Đức Thọ, Phường Gò Vấp, 71413 |

**越南 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| tháp B, Sadora, Thủ Đức, 71110 | FIX | LOCALITY |  |
| Quận 9, Thủ Đức | FIX | LOCALITY |  |
| gần Chùa Giác Vương, q12). ĐT: 0976693907, 107/41 đường TCH35, Quận 12, 71716 | FIX | LOCALITY |  |
| 363 38/20, Quận Bình Tân | FIX | LOCALITY |  |

**菲律宾 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Resorts World, Pasay | FIX | LOCALITY |  |
| rizal, Quezon City, <<not-applicable>> | FIX | LOCALITY |  |
| Ste 1707, Raffles Corporate Center, F. Ortigas Jr. Rd, Pasig, 1605 | FIX | LOCALITY |  |
| 143 Rd 20, Quezon City, 1108 | FIX | LOCALITY |  |

**菲律宾 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| P. Guevarra, San Juan | CONFIRM | ROUTE | Guevarra |
| 2nd floor Uptown Parade 9th Ave, Cor 36th St, Taguig City, 1630 | CONFIRM | ROUTE | 2Nd Floor, 9th Avenue, Taguig, 1630 |
| Ayala Malls Circuit Cinemas - Third Floor, Ayala Malls Circuit, Hippodromo, Carmona, Makat | CONFIRM | PREMISE_PROXIMITY | Ayala Malls Circuit |
| Milano Street, Taguig City, 1634 | CONFIRM | ROUTE | Mariano Street, Taguig, 1634 |

**菲律宾 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Higher Ground, Tandang Sora Ave 699, Quezon City, 1119 | ACCEPT | ROUTE | 699 Tandang Sora Avenue, Quezon City, 1119 |
| Green Sun 1232, 2285 Chino Roces Ave, Makati, 1231 | ACCEPT | ROUTE | 2285 Chino Roces Avenue, Makati, 1231 |
| L. Gonzales and MG Tower II, Shaw Boulevard, corner 29 de Agosto, Mandaluyong, 1550 | ACCEPT | PREMISE_PROXIMITY | MG Tower, 29 Shaw Boulevard, Mandaluyong, 1550 |
| 2nd Floor, Unit 2H, Super Miler Bldg, 189 Ortigas Ave, Pasig, 1604 | ACCEPT | ROUTE | Unit 2H, 189 Ortigas Avenue, Pasig, 1604 |

