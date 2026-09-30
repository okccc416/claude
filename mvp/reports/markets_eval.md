# 多市场评测报告（自动生成）

- 真实地址：各城市留出的 20% 商户（不在参考库里）的自填地址，标准答案为商户坐标（弱标注）
- 合成地址：按各市场写法渲染的测试部分道路（AI 解析器训练时没见过），标准答案已知
- 解析方式：rules = 规则 + 地名表；crf = 机器学习（条件随机场）；hybrid = 两者都出候选，由参考数据裁决
- 判对标准（真实地址）：门牌级 ≤ 250 米、楼宇级 ≤ 400 米、道路级为该道路经过商户 250 米内；"偏差 >1 公里"的静默错误不是商户坐标不准能解释的，是真正的错

## 真实商户地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 1000 | 74.8% | 3.4% | 0.4% | 13.0% | 4.6% | 3.8% | 1.6% | 86.7% | 2 |
| 澳大利亚（AU） | A | crf | 1000 | 69.1% | 2.3% | 2.5% | 18.4% | 4.2% | 3.5% | 1.5% | 86.1% | 2 |
| 澳大利亚（AU） | A | hybrid | 1000 | 75.4% | 2.8% | 0.4% | 12.7% | 4.8% | 3.9% | 1.7% | 86.5% | 3 |
| 德国（DE） | A | rules | 1000 | 92.3% | 1.4% | 0.2% | 2.0% | 3.2% | 0.9% | 0.5% | 95.7% | 2 |
| 德国（DE） | A | crf | 1000 | 86.6% | 1.2% | 0.7% | 8.0% | 3.2% | 0.3% | 0.2% | 93.9% | 1 |
| 德国（DE） | A | hybrid | 1000 | 94.2% | 1.2% | 0.1% | 2.0% | 1.6% | 0.9% | 0.5% | 97.3% | 2 |
| 法国（FR） | A | rules | 1000 | 88.4% | 3.0% | 0.3% | 6.1% | 1.0% | 1.2% | 0.7% | 95.6% | 1 |
| 法国（FR） | A | crf | 1000 | 85.5% | 4.7% | 0.8% | 5.9% | 2.1% | 1.0% | 0.6% | 94.8% | 1 |
| 法国（FR） | A | hybrid | 1000 | 88.9% | 3.2% | 0.2% | 5.7% | 0.8% | 1.2% | 0.7% | 96.5% | 2 |
| 荷兰（NL） | A | rules | 1000 | 81.2% | 7.5% | 0.9% | 8.1% | 0.8% | 1.5% | 0.8% | 96.0% | 2 |
| 荷兰（NL） | A | crf | 1000 | 72.0% | 2.1% | 0.8% | 22.7% | 1.1% | 1.3% | 0.8% | 89.9% | 1 |
| 荷兰（NL） | A | hybrid | 1000 | 83.2% | 5.6% | 0.8% | 8.1% | 0.7% | 1.6% | 0.8% | 96.1% | 3 |
| 阿联酋（AE） | B | rules | 1000 | 1.6% | 29.8% | 11.7% | 24.7% | 31.4% | 0.8% | 0.6% | 18.0% | 3 |
| 阿联酋（AE） | B | crf | 1000 | 0.7% | 19.3% | 6.6% | 53.0% | 20.0% | 0.4% | 0.2% | 11.1% | 3 |
| 阿联酋（AE） | B | hybrid | 1000 | 1.6% | 30.3% | 10.5% | 21.4% | 35.2% | 1.0% | 0.7% | 18.7% | 5 |
| 沙特（SA） | B | rules | 1000 | 2.4% | 27.8% | 11.8% | 13.8% | 43.5% | 0.7% | 0.6% | 17.4% | 3 |
| 沙特（SA） | B | crf | 1000 | 2.2% | 26.3% | 17.2% | 25.2% | 28.3% | 0.8% | 0.7% | 18.2% | 3 |
| 沙特（SA） | B | hybrid | 1000 | 2.6% | 32.0% | 9.5% | 12.5% | 42.7% | 0.7% | 0.6% | 19.4% | 6 |
| 马来西亚（MY） | C | rules | 1000 | 34.2% | 37.2% | 4.7% | 5.5% | 15.9% | 2.5% | 1.2% | 59.1% | 2 |
| 马来西亚（MY） | C | crf | 1000 | 28.3% | 40.1% | 12.3% | 6.4% | 10.8% | 2.1% | 1.0% | 59.6% | 2 |
| 马来西亚（MY） | C | hybrid | 1000 | 34.4% | 39.7% | 3.4% | 4.3% | 15.6% | 2.6% | 1.2% | 62.1% | 5 |
| 印尼（ID） | C | rules | 1000 | 28.5% | 28.2% | 2.7% | 4.0% | 32.9% | 3.7% | 1.2% | 40.9% | 2 |
| 印尼（ID） | C | crf | 1000 | 11.4% | 32.8% | 27.8% | 8.8% | 18.0% | 1.2% | 0.5% | 41.8% | 5 |
| 印尼（ID） | C | hybrid | 1000 | 28.4% | 31.3% | 2.1% | 3.7% | 30.4% | 4.1% | 1.5% | 43.6% | 6 |
| 泰国（TH） | C | rules | 1000 | 17.4% | 41.2% | 10.9% | 7.5% | 20.3% | 2.7% | 1.1% | 29.9% | 5 |
| 泰国（TH） | C | crf | 1000 | 13.1% | 28.6% | 24.0% | 19.5% | 13.4% | 1.4% | 0.5% | 22.0% | 3 |
| 泰国（TH） | C | hybrid | 1000 | 17.7% | 41.7% | 9.6% | 7.2% | 21.1% | 2.7% | 1.1% | 30.4% | 8 |
| 越南（VN） | C | rules | 1000 | 10.1% | 52.5% | 1.9% | 4.0% | 29.9% | 1.6% | 0.6% | 46.5% | 2 |
| 越南（VN） | C | crf | 1000 | 10.7% | 36.5% | 18.6% | 16.4% | 16.4% | 1.4% | 0.7% | 38.1% | 3 |
| 越南（VN） | C | hybrid | 1000 | 13.6% | 51.1% | 1.4% | 3.5% | 28.5% | 1.9% | 0.8% | 46.3% | 5 |
| 菲律宾（PH） | C | rules | 1000 | 20.1% | 34.0% | 15.5% | 9.7% | 18.4% | 2.3% | 1.0% | 36.1% | 3 |
| 菲律宾（PH） | C | crf | 1000 | 12.4% | 41.3% | 22.0% | 8.7% | 15.0% | 0.6% | 0.3% | 43.8% | 2 |
| 菲律宾（PH） | C | hybrid | 1000 | 21.4% | 42.1% | 8.5% | 6.5% | 19.1% | 2.4% | 1.0% | 44.1% | 5 |

## 合成地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 1000 | 82.5% | 8.7% | 0.0% | 5.8% | 1.8% | 1.2% | 0.2% | 97.6% | 2 |
| 澳大利亚（AU） | A | crf | 1000 | 86.7% | 5.7% | 0.0% | 5.8% | 0.6% | 1.2% | 0.2% | 99.0% | 1 |
| 澳大利亚（AU） | A | hybrid | 1000 | 86.4% | 5.9% | 0.0% | 5.8% | 0.7% | 1.2% | 0.2% | 98.9% | 3 |
| 德国（DE） | A | rules | 1000 | 79.6% | 6.8% | 0.0% | 5.5% | 5.4% | 2.7% | 0.2% | 94.3% | 2 |
| 德国（DE） | A | crf | 1000 | 83.0% | 9.7% | 0.0% | 4.9% | 2.2% | 0.2% | 0.2% | 97.3% | 1 |
| 德国（DE） | A | hybrid | 1000 | 81.9% | 8.7% | 0.0% | 4.6% | 2.1% | 2.7% | 0.2% | 97.5% | 3 |
| 法国（FR） | A | rules | 1000 | 89.5% | 3.1% | 0.0% | 5.1% | 1.9% | 0.4% | 0.0% | 97.4% | 2 |
| 法国（FR） | A | crf | 1000 | 88.2% | 6.6% | 0.0% | 4.3% | 0.9% | 0.0% | 0.0% | 99.2% | 1 |
| 法国（FR） | A | hybrid | 1000 | 90.6% | 4.2% | 0.0% | 4.3% | 0.6% | 0.3% | 0.0% | 99.2% | 3 |
| 荷兰（NL） | A | rules | 1000 | 86.7% | 7.0% | 0.0% | 4.2% | 0.7% | 1.4% | 0.0% | 99.4% | 3 |
| 荷兰（NL） | A | crf | 1000 | 87.3% | 8.0% | 0.0% | 4.0% | 0.1% | 0.6% | 0.0% | 100.0% | 1 |
| 荷兰（NL） | A | hybrid | 1000 | 87.1% | 7.4% | 0.0% | 3.8% | 0.3% | 1.4% | 0.0% | 100.0% | 4 |
| 阿联酋（AE） | B | rules | 1000 | 1.9% | 45.3% | 0.0% | 34.7% | 18.0% | 0.1% | 0.0% | 52.6% | 2 |
| 阿联酋（AE） | B | crf | 1000 | 7.0% | 69.0% | 0.0% | 2.0% | 21.9% | 0.1% | 0.0% | 72.9% | 1 |
| 阿联酋（AE） | B | hybrid | 1000 | 7.0% | 69.2% | 0.0% | 1.2% | 22.5% | 0.1% | 0.0% | 73.1% | 4 |
| 沙特（SA） | B | rules | 1000 | 10.2% | 66.8% | 0.0% | 7.4% | 15.6% | 0.0% | 0.0% | 76.2% | 2 |
| 沙特（SA） | B | crf | 1000 | 13.1% | 79.8% | 0.0% | 0.6% | 6.4% | 0.1% | 0.0% | 91.2% | 1 |
| 沙特（SA） | B | hybrid | 1000 | 13.1% | 79.7% | 0.0% | 0.4% | 6.7% | 0.1% | 0.0% | 91.0% | 3 |
| 马来西亚（MY） | C | rules | 1000 | 18.7% | 71.6% | 0.0% | 2.4% | 7.3% | 0.0% | 0.0% | 89.8% | 2 |
| 马来西亚（MY） | C | crf | 1000 | 23.2% | 72.9% | 0.0% | 0.1% | 3.8% | 0.0% | 0.0% | 95.0% | 1 |
| 马来西亚（MY） | C | hybrid | 1000 | 23.8% | 72.0% | 0.0% | 0.0% | 4.2% | 0.0% | 0.0% | 94.7% | 4 |
| 印尼（ID） | C | rules | 1000 | 22.5% | 66.6% | 0.0% | 0.4% | 10.5% | 0.0% | 0.0% | 88.8% | 2 |
| 印尼（ID） | C | crf | 1000 | 32.2% | 61.3% | 0.0% | 0.3% | 6.2% | 0.0% | 0.0% | 92.4% | 2 |
| 印尼（ID） | C | hybrid | 1000 | 32.7% | 60.6% | 0.0% | 0.0% | 6.7% | 0.0% | 0.0% | 92.2% | 3 |
| 泰国（TH） | C | rules | 1000 | 20.2% | 74.1% | 0.0% | 1.8% | 3.9% | 0.0% | 0.0% | 93.1% | 3 |
| 泰国（TH） | C | crf | 1000 | 24.2% | 72.7% | 0.0% | 0.4% | 2.6% | 0.1% | 0.0% | 95.1% | 2 |
| 泰国（TH） | C | hybrid | 1000 | 24.6% | 72.3% | 0.0% | 0.2% | 2.8% | 0.1% | 0.0% | 95.1% | 5 |
| 越南（VN） | C | rules | 1000 | 30.8% | 58.2% | 0.0% | 1.6% | 9.2% | 0.2% | 0.0% | 90.2% | 3 |
| 越南（VN） | C | crf | 1000 | 38.6% | 57.4% | 0.0% | 0.0% | 4.0% | 0.0% | 0.0% | 95.2% | 2 |
| 越南（VN） | C | hybrid | 1000 | 38.7% | 56.1% | 0.0% | 0.0% | 5.2% | 0.0% | 0.0% | 94.4% | 4 |
| 菲律宾（PH） | C | rules | 1000 | 20.9% | 66.1% | 0.0% | 3.3% | 9.7% | 0.0% | 0.0% | 85.9% | 2 |
| 菲律宾（PH） | C | crf | 1000 | 26.3% | 63.0% | 0.0% | 0.2% | 10.4% | 0.1% | 0.0% | 88.1% | 2 |
| 菲律宾（PH） | C | hybrid | 1000 | 26.6% | 64.5% | 0.0% | 0.0% | 8.8% | 0.1% | 0.0% | 89.0% | 4 |

## 错误样例（规则解析，真实地址）

**澳大利亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 53 Talavera Rd, Sydney, 2113 | FIX | ROUTE | 53 Talavera Road, Sydney NSW 2113 |
| SHOP 1, FOOTSCRAY PLAZA SHOPPING CENTRE, CNR ALBERT & PAISLEY STREET, FOOTSCRAY, 3011 | FIX | ROUTE | Shop 1, Paisley Street, Footscray VIC 3011 |
| Broughton Street,, Sydney, 2219 | FIX | ROUTE | Broughton Street, Sydney NSW 2219 |
| Hotham St, St Kilda East, 3183 | FIX | ROUTE | Hotham Street, St Kilda East VIC 3183 |

**澳大利亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 1/2 Tube St, Melbourne, 3020 | ACCEPT | PREMISE | Unit 1, 2 Tube Street, Melbourne VIC 3020 |
| 32 Lawrence St, Sydney, 2096 | CONFIRM_ADD_SUBPREMISES | PREMISE | 32 Lawrence Street, Sydney NSW 2096 |
| 404 High Street, WINDSOR, 3181 | ACCEPT | PREMISE | 404 High Street, Windsor VIC 3181 |
| Westfield, 236 Pacific Hwy, Sydney, 2077 | CONFIRM_ADD_SUBPREMISES | PREMISE | 236 Pacific Highway, Sydney NSW 2077 |

**澳大利亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 775 Sydney Rd, Melbourne, 3056 | CONFIRM | PREMISE | 775 Sydney Road, Melbourne VIC 3058 |
| Unit 2/174-176 Victoria St, Sydney, 2015 | CONFIRM | ROUTE | Unit 2/174-176, Victoria Street, Sydney NSW 2015 |
| Suite 1/200 Lygon St, Melbourne, 3053 | CONFIRM | PREMISE | Suite 1, 200 Lygon Street, Melbourne VIC 3057 |
| 12 Cabots Drive, Altona North, 3025 | CONFIRM | PREMISE | 12 Cabot Drive, Altona North VIC 3025 |

**德国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Alt-Karow 3, Berlin, 13125 | CONFIRM | PREMISE | Boenkestraße 3, 13125 Karow |
| Europaplatz 2, Berlin, 10557 | CONFIRM | PREMISE | Holsteiner Ufer 2, 10557 Hansaviertel |
| Mierendorffplatz 8, Berlin, 10589 | CONFIRM | PREMISE | Bonhoefferufer 8, 10589 Charlottenburg |
| Terminal 1, Schönefeld, 12529 | CONFIRM | PREMISE | Mahlower Allee 1, 12529 Schönefeld |

**德国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Handy Germany, Stuttgarter Platz 1A, Berlin, 10627 | ACCEPT | PREMISE | Stuttgarter Platz 1 A, 10627 Charlottenburg |
| Neuendorfstraße 5, Hennigsdorf, 16761 | ACCEPT | PREMISE | Neuendorfstraße 5, 16761 Hennigsdorf |
| Berliner Str. 8, Velten, 16727 | ACCEPT | PREMISE | Berliner Straße 8, 16727 Oberkrämer |
| Beusselstraße 44/N-Q, Berlin, 10553 | ACCEPT | PREMISE | Beusselstraße 1, 10553 Moabit |

**德国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Am Ostbahnhof, Berlin, 10243 | FIX | ROUTE | Am Ostbahnhof, 10243 |
| Hagenower Ring, Berlin, 13059 | FIX | ROUTE | Hagenower Ring, 13059 |
| Reichenberger Straße 113, Berlin, 10999 | FIX | ROUTE | Reichenberger Straße 113, 10999 |
| Lichtenhainer Straße 16, Berlin, 12627 | FIX | ROUTE | Lichtenhainer Straße 16, 12627 |

**法国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Imp. des Jardiniers, Paris, 75011 | FIX | ROUTE | Impasse des Jardiniers, 75011 |
| Rue de Saint-Simon, Paris, 75007 | FIX | ROUTE | Rue de Saint-Simon, 75007 |
| 170 Rue de la Nouvelle France, Montreuil, 93100 | FIX | ROUTE | 170 Rue Nouvelle, 93100 Montreuil |
| 82 Av. Georges Lafont, Paris, 75016 | FIX | ROUTE | 82 Avenue Georges Lafont, 75016 |

**法国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 46 Rue Condorcet, Paris, 75009 | ACCEPT | PREMISE | 46 Rue Condorcet, 75009 Paris 9e Arrondissement |
| CAP 18 189 rue Aubervilliers Bat 5 allée F No 9, Paris, 75018 | ACCEPT | PREMISE | 189 Rue d'Aubervilliers, 75018 Paris 18e Arrondissement |
| 35 Av. de la Prte de Choisy, Paris, 75013 | ACCEPT | PREMISE | 35 Avenue de Choisy, 75013 Paris 13e Arrondissement |
| 5 Place de Port au Prince, Paris, 75013 | ACCEPT | PREMISE | 5 Place de Port-au-Prince, 75013 Paris 13e Arrondissement |

**法国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 21 Rue des 4 Cheminées, Boulogne-Billancourt, 92100 | CONFIRM | PREMISE | 21 Rue des Cheminots, 75018 Paris 18e Arrondissement |
| 3 Bis Vla Guizot, Paris, 75017 | CONFIRM | PREMISE | 3 Rue Denis Poisson, 75017 Paris 17e Arrondissement |
| 94-96 rue Ledru Rollin, Paris, 75011 | CONFIRM | ROUTE | 94-96 Rue Ledru-Rollin, 75011 |
| Espace Champerret, 6 Rue Jean Oestreiche, Paris, 75017 | CONFIRM | PREMISE | 6 Rue Jean, 93400 Saint-Ouen-sur-Seine |

**荷兰 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| IJdoornlaan 1001, Amsterdam, 1035 | FIX | ROUTE | IJdoornlaan 1001 |
| Hamerstraat 2/4, Amsterdam, 1021 JV | FIX | ROUTE | Hamerstraat 2/4, 1021 JV |
| Develstein 100C, Amsterdam, 1102 AK | FIX | ROUTE | Develstein 100C, 1102 AK |
| Sarphatistraat 35, Amsterdam, 1018 EV | FIX | ROUTE | Sarphatistraat 35, 1018 EV |

**荷兰 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Van Boshuizenstraat 12, Amsterdam, 1083 DG | CONFIRM | PREMISE | Van Boshuizenstraat 12, 1083 BA Amsterdam |
| Eleanoor Rooseveltlaan 2, Amstelveen, 1183 CL | CONFIRM | PREMISE | Rooseveltlaan 2, 1078 NH Amstelveen |
| Station Amsterdam Centraal, Amsterdam, 1012 AB | CONFIRM | PREMISE_PROXIMITY | Station Amsterdam-Centraal, 1012 AB |
| Stadsplein 100, Amstelveen, 1181 ZM | CONFIRM | PREMISE | Stadsplein 100, 1181 ZM Amstelveen |

**荷兰 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Mbc Netherlands, Valkenburgerstraat 194, Amsterdam, 1011 NC | CONFIRM_ADD_SUBPREMISES | PREMISE | Valkenburgerstraat 194, 1011 NC Amsterdam |
| Service van Jo, Krugerstraat 4, Amsterdam, 1091 LE | CONFIRM_ADD_SUBPREMISES | PREMISE | Krugerstraat 4, 1091 LE Amsterdam |
| Anthony Fokkerweg 1, Amsterdam, 1059 CM | ACCEPT | PREMISE | Anthony Fokkerweg 1, 1059 CM Amsterdam |
| Gatwickstraat 33, Amsterdam, 1043 GL | ACCEPT | PREMISE | Gatwickstraat 33, 1043 GL Amsterdam |

**阿联酋 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 22277 84744, شارع 35 36, دبي | FIX | OTHER |  |
| Grand Millenium Hotel, دبي | FIX | OTHER |  |
| Ajman,New Industrial Area Jurf 1, دبي, 31466 | FIX | LOCALITY |  |
| Hassanicor Building, Ground Floor, Dubai | FIX | OTHER |  |

**阿联酋 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Omar Bin Al Khattab St, دبي, 78G5+78 | CONFIRM | PREMISE_PROXIMITY | Al Murar, 7HQQ78G5+78 |
| - 43rd St, دبي, 46477 | CONFIRM | ROUTE | 3rd Street |
| Mall of The Emirates - Ground Level, دبي, 182956 | CONFIRM | ROUTE | Ground Floor, Emirates Road |
| TCM - G-010 & G011, Circle Mall, Dubai, 00000 | CONFIRM | PREMISE_PROXIMITY | Circle Mall, 010 |

**阿联酋 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Murano Residence 1, Al Furjan, Dubai, دبي, 24FR+H5J | ACCEPT | PREMISE_PROXIMITY | 1, Al Furjan, 7HQQ24FR+H5 |
| Level 1, Emaar Square Building 4 - Office 103 - Sheikh Mohammed bin Rashid Blvd - Burj Kha | ACCEPT | PREMISE_PROXIMITY | Office 103, Emaar Square, 4 Sheikh Mohammed bin Rashid Boulevard, Даун |
| Al Ghurair Centre, Unit G-65, Al Rigga St., دبي, 000 | ACCEPT | PREMISE_PROXIMITY | Al Ghurair Centre, 65 Al Rigga Street |
| Sharjah Industrial Area 17/ 7CJV+C7 S102 | ACCEPT | PREMISE_PROXIMITY | 17, Muhaisnah 5, 7HQQ7CJV+C7 |

**沙特 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 7710 Abi Sufyan Ibn Harb، حي, RHNA3882, 3882, الرياض, 12474 | CONFIRM | ROUTE | 7710 Ibn Harb, 12474 |
| Exit 25, The Western Ring Road Jarir Book Store, الرياض, NA | CONFIRM | ROUTE | 25 Western Ring Road |
| Oqba Bin Nafea St, الرياض | CONFIRM | ROUTE | Oqbah Bin Nafea |
| Imam Saud Bin Abdulaziz, الرياض, 12274 | CONFIRM | ROUTE | Saeed Al Bana, 12274 |

**沙特 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| الرياض السعودية, الرياض | FIX | OTHER |  |
| السعوديه الرياض, الرياض, 13334 | FIX | LOCALITY |  |
| Khories Rd, East Naseem, الرياض | FIX | OTHER |  |
| head office : Batha, Bangaldeshi Market, Near Lu Lu Market Gate No-4, الرياض | FIX | LOCALITY |  |

**沙特 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| QJ83+CPQ, الرياض | ACCEPT | PREMISE_PROXIMITY | Hittin, 7HP8QJ83+CP |
| Kingdom Centre - Olaya St., الرياض, 12345 | ACCEPT | PREMISE_PROXIMITY | Kingdom Centre, Al Olaya Street, 12345 |
| RM8Q+97M, الرياض | ACCEPT | PREMISE_PROXIMITY | An Nada, 7HP8RM8Q+97 |
| VJ6W+7RR, الرياض, 13336 | ACCEPT | PREMISE_PROXIMITY | Al Aarid, 13336, 7HP8VJ6W+7R |

**马来西亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| No.54-1, Jalan PJS11/28A, Sunway Metro. Selangor, Subang Jaya, 46150 | CONFIRM | ROUTE | 54-1 Persiaran Metro, 46150 |
| Tingkat 12, Wisma Perkeso, Bandar Kuala Lumpur | CONFIRM | PREMISE_PROXIMITY | Wisma PERKESO, 12 |
| Taman Tasik Perdana, Kuala Lumpur | CONFIRM | ROUTE | Lebuh Perdana, Kuala Lumpur |
| No. 41, Aked Nisara, Jalan Tunku Abdul Rahman, Bandar Kuala Lumpur, 50100 | CONFIRM | ROUTE | 41 Jalan Tunku, 50100 |

**马来西亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Corus Hotel, Kuala Lumpur, 50450 | FIX | LOCALITY |  |
| jalan pju 10/13, Petaling Jaya, 47830 | FIX | LOCALITY |  |
| 10 Jalan SM4 Taman Sunway Batu Caves, Batu Caves, 68100 | FIX | LOCALITY |  |
| C-2-19, Jalan 2/142A Megan Phoenix, Kuala Lumpur, 56000 | FIX | LOCALITY |  |

**马来西亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 29 21, Jalan Ampang Utama 2/2, Ampang, 68000 | ACCEPT | ROUTE | 21 Jalan Ampang Utama 2/2, Ampang, 68000 |
| 5 Jalan 5/62A, Batu, 52200 | ACCEPT | ROUTE | 5 Jalan 5/62A, 52200 |
| 1 Jalan Puteri 4/1, Puchong, 47100 | ACCEPT | ROUTE | 1 Jalan Puteri 4/1, Puchong, 47100 |
| Unit B-G-11 Gateway Corporate Suites Gateway Kiaramas, 1, Jalan Desa Kiara, Kuala Lumpur,  | ACCEPT | ROUTE | 1 Jalan Desa Kiara, Kiaramas, 50480 |

**印尼 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Bintaro, Tangerang | CONFIRM | ROUTE | Jalan Tangerang |
| Jalan Bendungan Jatiluhur 28, Jakarta, 10210 | CONFIRM | ROUTE | Jalan Bendungan 28, 10210 |
| Samsung Service Center, PGC Cililitan Pusat Grosir Cililitan (PGC), Lantai 3, 968 & 969+G, | CONFIRM | ROUTE | Lantai 3, Gang Service 968, Jakarta Timur, 13630 |
| Cengkareng Business City 8, Tangerang Kota, 15125 | CONFIRM | ROUTE | Jalan Tangerang 8, 15125 |

**印尼 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Jl. Moh. Kahfi 1 No.2, RT.1/RW.6, Jakarta Selatan, 12620 | ACCEPT | ROUTE | Jalan Kahfi 1, Jakarta Selatan, 12620 |
| Jalan Raya Bogor 27, Jakarta, 13740 | ACCEPT | ROUTE | Jalan Raya Bogor 27, 13740 |
| Jl. Moh. Kahfi 1 No.11, RT.6/RW.4, Jakarta Selatan, 12630 | ACCEPT | ROUTE | Jalan Kahfi 1, Jakarta Selatan, 12630 |
| Jl. Meruya Utara No. 17, Jakarta Barat, 11620 | ACCEPT | ROUTE | Jalan Meruya Utara 17, Jakarta Barat, 11620 |

**印尼 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Palmerah, Jakarta Barat, 14420 | FIX | LOCALITY |  |
| RT.9/RW.7, Jakarta Timur, 13460 | FIX | LOCALITY |  |
| Jalan Raya Psr Minggu 2 B-C Ged IBA, Jakarta Selatan, 12780 | FIX | LOCALITY |  |
| Lippo Mall, Jakarta | FIX | OTHER |  |

**泰国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 32/1 พระราม 9 ซอย 41, กรุงเทพมหานคร, 10250 | CONFIRM | ROUTE | 32/1 ซอยพระราม 9 ซอย 41, 10250 |
| 41 ซอย ร่วมพัฒนา, กรุงเทพมหานคร, 10250 | CONFIRM | ROUTE | 41 ซอยร่วมพัฒนา, 10250 |
| บ้านเอื้ออาทรร่มเกล้า2 ซอย12, กรุงเทพมหานคร, 10520 | CONFIRM | ROUTE | 12 ซอยร่มเกล้า 2, 10520 |
| Bangkrang, กรุงเทพมหานคร, 11000 | CONFIRM | ROUTE | Bangkrang 5, 11000 |

**泰国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 9 หมู่ 10 ถนนเพชรเกษม, กรุงเทพมหานคร, 10160 | ACCEPT | ROUTE | 10 ถนนเพชรเกษม, 10160 |
| 1000/161,164.,1st Fl Liberty Plaza Building,Soi Thonglor(Sukhumvit55, ถ. สุขุมวิท, กรุงเทพ | ACCEPT | ROUTE | 1St Floor, 164 Sukhumvit Road, 10110 |
| 11 ถนน สุขุมวิท, กรุงเทพมหานคร, 10260 | ACCEPT | ROUTE | 11 ถนนสุขุมวิท, 10260 |
| 999/9 ถนน พระรามที่ 1, ปทุมวัน, 10330 | ACCEPT | ROUTE | 999/9 ถนนพระรามที่ 1, ปทุมวัน, 10330 |

**泰国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| ซอย น้อมสุข 401, กรุงเทพมหานคร, 10240 | FIX | LOCALITY |  |
| พัฒนาการ, กรุงเทพมหานคร, 10250 | FIX | LOCALITY |  |
| หนองใหญ่, กรุงเทพมหานคร, 10160 | FIX | LOCALITY |  |
| ปากซอยไปรษณีย์สุทธิสาร, กรุงเทพมหานคร | FIX | OTHER |  |

**越南 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 472/12 Vườn Lài, Khu Phố 3, Phường An Phú Đông, Quận Gò Vấp, 700000 | CONFIRM | ROUTE | 472/12 Đường An Phú, Khu phố 3, 700000 |
| 28 Quốc Lộ 1, Quận 12, 71516 | CONFIRM | ROUTE | 28 Quốc Lộ 1, 71516 |
| 17 Đường Số 12, Quận Bình Thạnh, 72310 | CONFIRM | ROUTE | Dương Thanh, 72310 |
| 497/5 Sư Vạn Hạnh, Quận 10, 700000 | CONFIRM | ROUTE | 497/5 Đường Sư Vạn Hạnh, 700000 |

**越南 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 666/46/11 Hẻm 666/46 Đường 3/2, Quận 10, 72506 | FIX | LOCALITY |  |
| 20/1C QL1A, Quận 12, 700000 | FIX | LOCALITY |  |
| 864 Đường Vĩnh Lộc, Huyện Bình Chánh, 71819 | FIX | LOCALITY |  |
| 1/90 Đ. Mỹ Phước - Tân Vạn, Thuận Giao, Hồ Chí Minh, Quận 7, 750000 | FIX | LOCALITY |  |

**越南 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 20D Đường Trương Quốc Dung, Quận Phú Nhuận, 72217 | ACCEPT | ROUTE | 20D Đường Trương Quốc Dung, Phường Phú Nhuận, 72217 |
| 23 Đường Lê Trung Nghĩa, Quận Tân Bình, 72111 | ACCEPT | ROUTE | 23 Lê Trung Nghĩa, Phường Tân Bình, 72111 |
| 38 Đường Trương Quốc Dung, Quận Phú Nhuận, 72217 | ACCEPT | ROUTE | 38 Đường Trương Quốc Dung, Phường Phú Nhuận, 72217 |
| 258 Đường Bình Phú, Thủ Đức, 71311 | ACCEPT | ROUTE | 258 Đường Bình Phú, 71311 |

**菲律宾 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 2nd floor San lorenzo Place Edsa corner chino roces ave., Makati, 1223 | CONFIRM | ROUTE | 2Nd Floor, Chino Roces Avenue, Makati, 1223 |
| Level 5, One Ayala (Ayala Malls, Makati, 1226 | CONFIRM | PREMISE_PROXIMITY | Level 5, 𝗔𝘆𝗮𝗹𝗮 𝗠𝗮𝗹𝗹𝘀, 1226 |
| at Epifanio delos Santos Ave., Quezon City, 1109 | CONFIRM | ROUTE | Delos Santos Street, Quezon City, 1109 |
| L2 Trinisia Building , Arayat Street, San Martin De Porres , San Martin De Pores , 1111 Qu | CONFIRM | ROUTE | Arayat Street, Quezon City, 1111 |

**菲律宾 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Unit K4-K6 Ground Floor, CW Home Depot, 1 Doña Julia Vargas Ave, Pasig, 1604 | ACCEPT | PREMISE_PROXIMITY | Unit K4, Home Depot, 1 Doña Julia Vargas Avenue, Pasig, 1604 |
| UP-Ayala Land TechnoHub, Commonwealth Ave, Quezon City | ACCEPT | PREMISE_PROXIMITY | U.P. Ayala Land TechnoHub, Commonwealth Avenue, Quezon City |
| Exquadra Tower, Exchange Road cor. Jade Drive, Ortigas Center, Pasig City, Pasig, 1605 | ACCEPT | PREMISE_PROXIMITY | Ortigas Center, Jade Drive, Pasig, 1605 |
| Banlat Rd 208, Quezon City, 1116 | ACCEPT | ROUTE | 208 Banlat Road, Quezon City, 1116 |

**菲律宾 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Victoria, Quezon City, 1116 | FIX | LOCALITY |  |
| Escolta - Pasig Ferry Lawton, Manila, 1540 | FIX | LOCALITY |  |
| 5 pulong Kendi Street  Santa Ana Taguig, Taguig City | FIX | LOCALITY |  |
| Pasig Line, Manila, 1017 | FIX | LOCALITY |  |

