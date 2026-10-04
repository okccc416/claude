# 直接通过的放宽规则（开发集校准，自动生成）

条件：样本 ≥ 25、正确率 ≥ 95%（Wilson 下界 ≥ 88%）、偏差 >1 公里 ≤ 2%。未列出的组合仍按默认规则（A 类邮编被替换 -> 要求确认；B / C 类道路级要邮编印证 + 道路名唯一 + 名称完全一致）。

| 市场 | 证据组合 | 样本 | 正确 | 偏差 >1 公里 | 允许直接通过 |
|---|---|---|---|---|---|
| 澳大利亚（AU） | PREMISE|POSTCODE_REPLACED | 17 | 23.5% | 58.8% |  |
| 法国（FR） | PREMISE|POSTCODE_REPLACED | 10 | 80.0% | 0.0% |  |
| 荷兰（NL） | PREMISE|POSTCODE_REPLACED | 19 | 100.0% | 0.0% |  |
| 阿联酋（AE） | ROUTE|-|u1|exact | 29 | 58.6% | 27.6% |  |
| 阿联酋（AE） | ROUTE|-|uN|exact | 19 | 31.6% | 63.2% |  |
| 阿联酋（AE） | POI|n2|- | 15 | 60.0% | 26.7% |  |
| 马来西亚（MY） | POI|n2|pc | 51 | 66.7% | 15.7% |  |
| 马来西亚（MY） | OSM|pc|u1|exact | 46 | 89.1% | 2.2% |  |
| 马来西亚（MY） | ROUTE|-+area|u1|exact | 43 | 93.0% | 4.7% |  |
| 马来西亚（MY） | POI|n1|pc | 41 | 65.9% | 19.5% |  |
| 马来西亚（MY） | ROUTE|pc+area|uN|exact | 22 | 68.2% | 22.7% |  |
| 马来西亚（MY） | ROUTE|-|u1|exact | 21 | 85.7% | 9.5% |  |
| 马来西亚（MY） | POI|n2|- | 20 | 65.0% | 20.0% |  |
| 马来西亚（MY） | ROUTE|pc|uN|exact | 18 | 61.1% | 27.8% |  |
| 印尼（ID） | POI|n2|pc | 67 | 59.7% | 14.9% |  |
| 印尼（ID） | ROUTE|pc+area|uN|exact | 59 | 72.9% | 13.6% |  |
| 印尼（ID） | POI|n1|pc | 50 | 68.0% | 14.0% |  |
| 印尼（ID） | ROUTE|pc+area|uN|core | 14 | 50.0% | 35.7% |  |
| 印尼（ID） | ROUTE|pc|uN|exact | 13 | 69.2% | 15.4% |  |
| 印尼（ID） | ROUTE|-+area|u1|exact | 11 | 63.6% | 18.2% |  |
| 泰国（TH） | ROUTE|-|u1|exact | 64 | 68.8% | 20.3% |  |
| 泰国（TH） | POI|n2|pc | 47 | 57.4% | 23.4% |  |
| 泰国（TH） | ROUTE|pc|u1|core | 34 | 58.8% | 29.4% |  |
| 泰国（TH） | POI|n2|- | 31 | 51.6% | 25.8% |  |
| 泰国（TH） | ROUTE|-|u1|core | 27 | 66.7% | 18.5% |  |
| 泰国（TH） | OSM|pc|u1|exact | 16 | 68.8% | 31.2% |  |
| 泰国（TH） | POI|n1|pc | 15 | 66.7% | 20.0% |  |
| 泰国（TH） | ROUTE|-+area|u1|exact | 10 | 60.0% | 30.0% |  |
| 泰国（TH） | ROUTE|-|uN|exact | 10 | 50.0% | 40.0% |  |
| 越南（VN） | POI|n1|pc | 22 | 81.8% | 4.5% |  |
| 越南（VN） | ROUTE|pc|u1|core | 18 | 72.2% | 27.8% |  |
| 越南（VN） | POI|n2|pc | 18 | 77.8% | 16.7% |  |
| 越南（VN） | ROUTE|-+area|u1|exact | 17 | 82.4% | 11.8% |  |
| 越南（VN） | ROUTE|pc+area|uN|exact | 16 | 68.8% | 25.0% |  |
| 越南（VN） | ROUTE|pc+area|uN|core | 12 | 91.7% | 8.3% |  |
| 越南（VN） | ROUTE|pc|uN|exact | 10 | 70.0% | 20.0% |  |
| 菲律宾（PH） | ROUTE|pc+area|uN|exact | 72 | 90.3% | 6.9% |  |
| 菲律宾（PH） | POI|n2|pc | 38 | 76.3% | 15.8% |  |
| 菲律宾（PH） | POI|n1|pc | 25 | 88.0% | 0.0% |  |
| 菲律宾（PH） | OSM|pc|u1|exact | 21 | 90.5% | 4.8% |  |
| 菲律宾（PH） | ROUTE|-+area|u1|exact | 14 | 78.6% | 7.1% |  |
| 菲律宾（PH） | ROUTE|pc+area|uN|core | 11 | 81.8% | 9.1% |  |
| 菲律宾（PH） | ROUTE|pc|u1|core | 10 | 90.0% | 10.0% |  |
| 加拿大（CA） | OSM|pc|u1|exact | 102 | 97.1% | 2.0% | 是 |
| 加拿大（CA） | PREMISE|POSTCODE_REPLACED | 49 | 91.8% | 8.2% |  |
| 加拿大（CA） | OSM|pc|uN|exact | 17 | 100.0% | 0.0% |  |
| 墨西哥（MX） | PREMISE|POSTCODE_REPLACED | 53 | 75.5% | 18.9% |  |
| 墨西哥（MX） | POI|n1|pc | 14 | 78.6% | 21.4% |  |
| 波多黎各（PR） | ROUTE|pc|uN|exact | 74 | 87.8% | 5.4% |  |
| 波多黎各（PR） | ROUTE|pc|uN|suffix | 23 | 69.6% | 13.0% |  |
| 波多黎各（PR） | ROUTE|-|u1|exact | 22 | 90.9% | 9.1% |  |
| 波多黎各（PR） | POI|n2|pc | 20 | 80.0% | 15.0% |  |
| 波多黎各（PR） | OSM|pc|uN|exact | 20 | 80.0% | 5.0% |  |
| 波多黎各（PR） | OSM|pc|u1|exact | 19 | 84.2% | 5.3% |  |
| 波多黎各（PR） | POI|n1|pc | 19 | 63.2% | 5.3% |  |
| 波多黎各（PR） | OSM|pc|uN|suffix | 12 | 91.7% | 8.3% |  |
| 波多黎各（PR） | ROUTE|pc+area|uN|exact | 12 | 58.3% | 33.3% |  |
| 巴西（BR） | PREMISE|POSTCODE_REPLACED | 110 | 95.5% | 0.9% | 是 |
| 巴西（BR） | OSM|pc|u1|exact | 21 | 95.2% | 0.0% |  |
| 阿根廷（AR） | ROUTE|pc+area|uN|exact | 207 | 95.2% | 1.9% | 是 |
| 阿根廷（AR） | OSM|pc|uN|exact | 36 | 94.4% | 0.0% |  |
| 阿根廷（AR） | OSM|pc|u1|exact | 34 | 91.2% | 8.8% |  |
| 阿根廷（AR） | POI|n1|pc | 33 | 97.0% | 0.0% |  |
| 阿根廷（AR） | POI|n2|pc | 32 | 96.9% | 0.0% |  |
| 阿根廷（AR） | ROUTE|-+area|uN|exact | 18 | 88.9% | 11.1% |  |
| 阿根廷（AR） | ROUTE|pc+area|uN|suffix | 16 | 87.5% | 0.0% |  |
| 阿根廷（AR） | ROUTE|-+area|u1|exact | 16 | 87.5% | 12.5% |  |
| 阿根廷（AR） | ROUTE|pc+area|uN|core | 10 | 90.0% | 10.0% |  |
| 智利（CL） | OSM|pc|u1|exact | 17 | 94.1% | 5.9% |  |
| 智利（CL） | POI|n2|pc | 13 | 92.3% | 0.0% |  |
| 哥伦比亚（CO） | POI|n1|pc | 33 | 72.7% | 24.2% |  |
| 哥伦比亚（CO） | POI|n2|pc | 29 | 89.7% | 3.4% |  |
| 哥伦比亚（CO） | OSM|pc|uN|exact | 13 | 84.6% | 7.7% |  |
| 英国（GB） | ROUTE|pc|uN|exact | 204 | 98.5% | 1.0% | 是 |
| 英国（GB） | OSM|pc|uN|exact | 117 | 99.1% | 0.9% | 是 |
| 英国（GB） | OSM|pc|u1|exact | 110 | 94.5% | 2.7% |  |
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
| 葡萄牙（PT） | PREMISE|POSTCODE_REPLACED | 40 | 87.5% | 5.0% |  |
| 葡萄牙（PT） | POI|n2|pc | 35 | 85.7% | 11.4% |  |
| 葡萄牙（PT） | POI|n1|pc | 24 | 91.7% | 8.3% |  |
| 葡萄牙（PT） | OSM|pc|uN|exact | 20 | 100.0% | 0.0% |  |
| 瑞典（SE） | OSM|pc|u1|exact | 360 | 96.4% | 1.4% | 是 |
| 瑞典（SE） | OSM|pc|uN|exact | 50 | 96.0% | 4.0% |  |
| 瑞典（SE） | ROUTE|pc|uN|exact | 50 | 98.0% | 2.0% | 是 |
| 瑞典（SE） | ROUTE|pc+area|uN|exact | 18 | 94.4% | 5.6% |  |
| 瑞典（SE） | POI|n2|pc | 13 | 100.0% | 0.0% |  |
| 挪威（NO） | POI|n2|pc | 15 | 93.3% | 0.0% |  |
| 挪威（NO） | POI|n1|pc | 11 | 100.0% | 0.0% |  |
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
| 保加利亚（BG） | ROUTE|pc|u1|core | 234 | 94.9% | 1.7% |  |
| 保加利亚（BG） | OSM|pc|u1|core | 174 | 97.1% | 0.6% | 是 |
| 保加利亚（BG） | OSM|pc|u1|exact | 82 | 87.8% | 4.9% |  |
| 保加利亚（BG） | ROUTE|-|u1|core | 24 | 58.3% | 37.5% |  |
| 保加利亚（BG） | POI|n1|pc | 21 | 90.5% | 0.0% |  |
| 保加利亚（BG） | ROUTE|pc|uN|core | 21 | 85.7% | 9.5% |  |
| 保加利亚（BG） | POI|n2|pc | 19 | 84.2% | 10.5% |  |
| 保加利亚（BG） | OSM|pc|uN|core | 11 | 90.9% | 9.1% |  |
| 保加利亚（BG） | ROUTE|-|u1|exact | 10 | 90.0% | 0.0% |  |
| 新西兰（NZ） | OSM|pc|u1|exact | 17 | 100.0% | 0.0% |  |
| 印度（IN） | POI|n1|pc | 29 | 69.0% | 17.2% |  |
| 印度（IN） | ROUTE|pc|uN|exact | 23 | 78.3% | 4.3% |  |
| 印度（IN） | POI|n2|pc | 21 | 71.4% | 4.8% |  |
| 印度（IN） | ROUTE|pc+area|uN|exact | 11 | 45.5% | 36.4% |  |
| 印度（IN） | ROUTE|-|u1|exact | 10 | 10.0% | 90.0% |  |
