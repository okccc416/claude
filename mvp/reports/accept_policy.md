# 直接通过的放宽规则（开发集校准，自动生成）

条件：样本 ≥ 25、正确率 ≥ 95%（Wilson 下界 ≥ 88%）、偏差 >1 公里 ≤ 2%。未列出的组合仍按默认规则（A 类邮编被替换 -> 要求确认；B / C 类道路级要邮编印证 + 道路名唯一 + 名称完全一致）。

| 市场 | 证据组合 | 样本 | 正确 | 偏差 >1 公里 | 允许直接通过 |
|---|---|---|---|---|---|
| 澳大利亚（AU） | PREMISE|POSTCODE_REPLACED | 17 | 23.5% | 58.8% |  |
| 法国（FR） | PREMISE|POSTCODE_REPLACED | 10 | 80.0% | 0.0% |  |
| 荷兰（NL） | PREMISE|POSTCODE_REPLACED | 19 | 100.0% | 0.0% |  |
| 阿联酋（AE） | ROUTE|-|u1|exact | 33 | 72.7% | 21.2% |  |
| 阿联酋（AE） | ROUTE|-|u1|core | 10 | 70.0% | 30.0% |  |
| 马来西亚（MY） | ROUTE|-+area|u1|exact | 46 | 95.7% | 2.2% |  |
| 马来西亚（MY） | ROUTE|pc+area|uN|exact | 21 | 71.4% | 14.3% |  |
| 马来西亚（MY） | ROUTE|-|u1|exact | 19 | 89.5% | 10.5% |  |
| 马来西亚（MY） | ROUTE|pc|uN|exact | 16 | 81.2% | 6.2% |  |
| 印尼（ID） | ROUTE|pc+area|uN|exact | 48 | 83.3% | 10.4% |  |
| 印尼（ID） | ROUTE|pc+area|uN|core | 14 | 64.3% | 21.4% |  |
| 印尼（ID） | ROUTE|-+area|u1|exact | 13 | 76.9% | 7.7% |  |
| 印尼（ID） | ROUTE|pc|uN|exact | 10 | 80.0% | 10.0% |  |
| 泰国（TH） | ROUTE|-|u1|exact | 68 | 88.2% | 4.4% |  |
| 泰国（TH） | ROUTE|pc|u1|core | 30 | 66.7% | 13.3% |  |
| 泰国（TH） | ROUTE|-|u1|core | 24 | 75.0% | 16.7% |  |
| 泰国（TH） | ROUTE|-+area|u1|exact | 10 | 70.0% | 20.0% |  |
| 越南（VN） | ROUTE|pc|u1|core | 27 | 81.5% | 11.1% |  |
| 越南（VN） | ROUTE|-+area|u1|exact | 17 | 100.0% | 0.0% |  |
| 越南（VN） | ROUTE|pc|uN|exact | 15 | 73.3% | 20.0% |  |
| 越南（VN） | ROUTE|pc+area|uN|exact | 14 | 71.4% | 21.4% |  |
| 越南（VN） | ROUTE|-|u1|exact | 13 | 76.9% | 23.1% |  |
| 越南（VN） | ROUTE|-+area|uN|exact | 11 | 63.6% | 36.4% |  |
| 越南（VN） | ROUTE|pc+area|uN|core | 10 | 100.0% | 0.0% |  |
| 菲律宾（PH） | ROUTE|pc+area|uN|exact | 71 | 91.5% | 4.2% |  |
| 菲律宾（PH） | ROUTE|-+area|u1|exact | 13 | 76.9% | 7.7% |  |
| 菲律宾（PH） | ROUTE|pc+area|uN|core | 10 | 90.0% | 0.0% |  |
| 加拿大（CA） | OSM|pc|u1|exact | 102 | 97.1% | 2.0% | 是 |
| 加拿大（CA） | PREMISE|POSTCODE_REPLACED | 49 | 91.8% | 8.2% |  |
| 加拿大（CA） | OSM|pc|uN|exact | 17 | 100.0% | 0.0% |  |
| 墨西哥（MX） | PREMISE|POSTCODE_REPLACED | 53 | 75.5% | 18.9% |  |
| 波多黎各（PR） | ROUTE|pc|uN|exact | 73 | 87.7% | 5.5% |  |
| 波多黎各（PR） | ROUTE|-|u1|exact | 23 | 87.0% | 13.0% |  |
| 波多黎各（PR） | ROUTE|pc|uN|suffix | 23 | 69.6% | 17.4% |  |
| 波多黎各（PR） | OSM|pc|uN|exact | 19 | 78.9% | 5.3% |  |
| 波多黎各（PR） | OSM|pc|u1|exact | 19 | 84.2% | 5.3% |  |
| 波多黎各（PR） | OSM|pc|uN|suffix | 13 | 92.3% | 7.7% |  |
| 波多黎各（PR） | ROUTE|pc+area|uN|exact | 12 | 58.3% | 33.3% |  |
| 巴西（BR） | PREMISE|POSTCODE_REPLACED | 110 | 95.5% | 0.9% | 是 |
| 巴西（BR） | OSM|pc|u1|exact | 21 | 95.2% | 0.0% |  |
| 阿根廷（AR） | ROUTE|pc+area|uN|exact | 207 | 95.2% | 1.9% | 是 |
| 阿根廷（AR） | OSM|pc|uN|exact | 36 | 94.4% | 0.0% |  |
| 阿根廷（AR） | OSM|pc|u1|exact | 34 | 91.2% | 8.8% |  |
| 阿根廷（AR） | POI|n1|pc | 33 | 97.0% | 0.0% |  |
| 阿根廷（AR） | POI|n2|pc | 32 | 96.9% | 0.0% |  |
| 阿根廷（AR） | ROUTE|-+area|uN|exact | 18 | 88.9% | 11.1% |  |
| 阿根廷（AR） | ROUTE|-+area|u1|exact | 16 | 87.5% | 12.5% |  |
| 阿根廷（AR） | ROUTE|pc+area|uN|suffix | 15 | 86.7% | 0.0% |  |
| 阿根廷（AR） | ROUTE|pc+area|uN|core | 10 | 90.0% | 10.0% |  |
| 智利（CL） | OSM|pc|u1|exact | 17 | 94.1% | 5.9% |  |
| 智利（CL） | POI|n2|pc | 12 | 91.7% | 0.0% |  |
| 哥伦比亚（CO） | POI|n2|pc | 11 | 63.6% | 18.2% |  |
| 哥伦比亚（CO） | POI|n1|pc | 10 | 50.0% | 50.0% |  |
| 英国（GB） | ROUTE|pc|uN|exact | 204 | 98.5% | 1.0% | 是 |
| 英国（GB） | OSM|pc|uN|exact | 117 | 99.1% | 0.9% | 是 |
| 英国（GB） | OSM|pc|u1|exact | 111 | 94.6% | 2.7% |  |
| 英国（GB） | POI|n2|pc | 48 | 95.8% | 2.1% |  |
| 英国（GB） | POI|n1|pc | 23 | 91.3% | 8.7% |  |
| 英国（GB） | ROUTE|pc+area|uN|exact | 20 | 100.0% | 0.0% |  |
| 英国（GB） | ROUTE|-|u1|exact | 16 | 75.0% | 18.8% |  |
| 英国（GB） | ROUTE|-|uN|exact | 14 | 92.9% | 7.1% |  |
| 爱尔兰（IE） | ROUTE|pc|uN|exact | 120 | 86.7% | 5.0% |  |
| 爱尔兰（IE） | OSM|pc|uN|exact | 74 | 81.1% | 8.1% |  |
| 爱尔兰（IE） | OSM|pc|u1|exact | 70 | 90.0% | 4.3% |  |
| 爱尔兰（IE） | POI|n1|pc | 17 | 94.1% | 0.0% |  |
| 爱尔兰（IE） | POI|n2|pc | 17 | 88.2% | 0.0% |  |
| 爱尔兰（IE） | ROUTE|pc+area|uN|exact | 13 | 84.6% | 7.7% |  |
| 卢森堡（LU） | PREMISE|POSTCODE_REPLACED | 22 | 63.6% | 27.3% |  |
| 西班牙（ES） | PREMISE|POSTCODE_REPLACED | 11 | 72.7% | 9.1% |  |
| 葡萄牙（PT） | OSM|pc|u1|exact | 45 | 91.1% | 4.4% |  |
| 葡萄牙（PT） | PREMISE|POSTCODE_REPLACED | 39 | 87.2% | 5.1% |  |
| 葡萄牙（PT） | POI|n2|pc | 35 | 85.7% | 11.4% |  |
| 葡萄牙（PT） | OSM|pc|uN|exact | 20 | 100.0% | 0.0% |  |
| 瑞典（SE） | OSM|pc|u1|exact | 367 | 96.5% | 1.4% | 是 |
| 瑞典（SE） | OSM|pc|uN|exact | 52 | 96.2% | 3.8% |  |
| 瑞典（SE） | ROUTE|pc|uN|exact | 52 | 98.1% | 1.9% | 是 |
| 瑞典（SE） | ROUTE|pc+area|uN|exact | 18 | 94.4% | 5.6% |  |
| 瑞典（SE） | POI|n2|pc | 13 | 100.0% | 0.0% |  |
| 挪威（NO） | POI|n2|pc | 15 | 93.3% | 0.0% |  |
| 芬兰（FI） | OSM|pc|u1|exact | 41 | 97.6% | 0.0% |  |
| 芬兰（FI） | PREMISE|POSTCODE_REPLACED | 13 | 76.9% | 7.7% |  |
| 拉脱维亚（LV） | PREMISE|POSTCODE_REPLACED | 22 | 90.9% | 9.1% |  |
| 立陶宛（LT） | PREMISE|POSTCODE_REPLACED | 102 | 100.0% | 0.0% | 是 |
| 波兰（PL） | PREMISE|POSTCODE_REPLACED | 40 | 80.0% | 2.5% |  |
| 捷克（CZ） | PREMISE|POSTCODE_REPLACED | 17 | 88.2% | 11.8% |  |
| 捷克（CZ） | OSM|pc|u1|exact | 14 | 100.0% | 0.0% |  |
| 斯洛伐克（SK） | PREMISE|POSTCODE_REPLACED | 25 | 96.0% | 4.0% |  |
| 斯洛伐克（SK） | OSM|pc|u1|exact | 12 | 100.0% | 0.0% |  |
| 匈牙利（HU） | OSM|pc|u1|exact | 245 | 96.3% | 1.6% | 是 |
| 匈牙利（HU） | ROUTE|pc|uN|exact | 148 | 95.3% | 2.7% |  |
| 匈牙利（HU） | OSM|pc|uN|exact | 119 | 95.0% | 3.4% |  |
| 匈牙利（HU） | POI|n2|pc | 20 | 85.0% | 5.0% |  |
| 匈牙利（HU） | POI|n1|pc | 16 | 93.8% | 6.2% |  |
| 匈牙利（HU） | ROUTE|-|u1|exact | 14 | 85.7% | 0.0% |  |
| 克罗地亚（HR） | PREMISE|POSTCODE_REPLACED | 198 | 94.4% | 2.5% |  |
| 保加利亚（BG） | OSM|pc|u1|exact | 12 | 91.7% | 0.0% |  |
| 新西兰（NZ） | OSM|pc|u1|exact | 17 | 100.0% | 0.0% |  |
| 印度（IN） | ROUTE|pc|uN|exact | 18 | 72.2% | 11.1% |  |
| 印度（IN） | ROUTE|-|u1|exact | 10 | 10.0% | 90.0% |  |
| 科威特（KW） | ROUTE|-|u1|exact | 18 | 55.6% | 33.3% |  |
| 巴林（BH） | ROUTE|-|u1|core | 74 | 2.7% | 91.9% |  |
| 巴林（BH） | ROUTE|-+area|uN|exact | 53 | 75.5% | 9.4% |  |
| 巴林（BH） | ROUTE|-+area|u1|exact | 37 | 86.5% | 8.1% |  |
| 巴林（BH） | POI|n2|- | 26 | 88.5% | 11.5% |  |
| 巴林（BH） | ROUTE|-|u1|exact | 20 | 60.0% | 35.0% |  |
| 巴林（BH） | ROUTE|-|uN|exact | 14 | 78.6% | 21.4% |  |
| 埃及（EG） | ROUTE|-|u1|exact | 27 | 63.0% | 29.6% |  |
| 埃及（EG） | OSM|-|u1|exact | 23 | 60.9% | 26.1% |  |
| 埃及（EG） | ROUTE|-|uN|exact | 18 | 38.9% | 50.0% |  |
| 埃及（EG） | OSM|-|uN|exact | 17 | 47.1% | 41.2% |  |
| 埃及（EG） | ROUTE|pc|uN|core | 14 | 100.0% | 0.0% |  |
| 埃及（EG） | OSM|-|uN|core | 10 | 60.0% | 20.0% |  |
| 埃及（EG） | OSM|pc|uN|core | 10 | 90.0% | 10.0% |  |
| 哈萨克斯坦（KZ） | ROUTE|-+area|uN|exact | 52 | 76.9% | 19.2% |  |
| 哈萨克斯坦（KZ） | POI|n2|- | 43 | 74.4% | 23.3% |  |
| 哈萨克斯坦（KZ） | POI|n2|pc | 34 | 76.5% | 11.8% |  |
| 哈萨克斯坦（KZ） | ROUTE|pc|uN|exact | 31 | 90.3% | 6.5% |  |
| 哈萨克斯坦（KZ） | ROUTE|pc+area|uN|exact | 29 | 82.8% | 17.2% |  |
| 哈萨克斯坦（KZ） | ROUTE|-|u1|exact | 25 | 76.0% | 20.0% |  |
| 哈萨克斯坦（KZ） | POI|n1|pc | 22 | 90.9% | 9.1% |  |
| 哈萨克斯坦（KZ） | ROUTE|-+area|u1|exact | 16 | 87.5% | 12.5% |  |
| 哈萨克斯坦（KZ） | ROUTE|-+area|uN|core | 11 | 72.7% | 27.3% |  |
| 多米尼加（DO） | ROUTE|pc|uN|exact | 37 | 86.5% | 5.4% |  |
| 多米尼加（DO） | ROUTE|pc+area|uN|exact | 28 | 71.4% | 28.6% |  |
| 多米尼加（DO） | POI|n1|pc | 27 | 63.0% | 14.8% |  |
| 多米尼加（DO） | POI|n2|pc | 27 | 74.1% | 22.2% |  |
| 多米尼加（DO） | ROUTE|-|u1|exact | 24 | 62.5% | 33.3% |  |
| 多米尼加（DO） | ROUTE|-+area|u1|exact | 17 | 82.4% | 5.9% |  |
| 多米尼加（DO） | ROUTE|-+area|uN|exact | 15 | 40.0% | 53.3% |  |
| 多米尼加（DO） | ROUTE|-|u1|core | 10 | 30.0% | 50.0% |  |
| 多米尼加（DO） | POI|n2|- | 10 | 60.0% | 30.0% |  |
