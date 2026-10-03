# 直接通过的放宽规则（开发集校准，自动生成）

条件：样本 ≥ 25、正确率 ≥ 95%（Wilson 下界 ≥ 88%）、偏差 >1 公里 ≤ 2%。未列出的组合仍按默认规则（A 类邮编被替换 -> 要求确认；B / C 类道路级要邮编印证 + 道路名唯一 + 名称完全一致）。

| 市场 | 证据组合 | 样本 | 正确 | 偏差 >1 公里 | 允许直接通过 |
|---|---|---|---|---|---|
| 澳大利亚（AU） | PREMISE|POSTCODE_REPLACED | 17 | 23.5% | 58.8% |  |
| 澳大利亚（AU） | POI|n2|pc | 11 | 81.8% | 0.0% |  |
| 法国（FR） | PREMISE|POSTCODE_REPLACED | 11 | 72.7% | 9.1% |  |
| 荷兰（NL） | PREMISE|POSTCODE_REPLACED | 19 | 100.0% | 0.0% |  |
| 阿联酋（AE） | ROUTE|-|u1|exact | 27 | 66.7% | 25.9% |  |
| 阿联酋（AE） | POI|n2|- | 20 | 55.0% | 25.0% |  |
| 马来西亚（MY） | POI|n2|pc | 84 | 72.6% | 13.1% |  |
| 马来西亚（MY） | POI|n1|pc | 48 | 70.8% | 16.7% |  |
| 马来西亚（MY） | ROUTE|-+area|u1|exact | 37 | 94.6% | 2.7% |  |
| 马来西亚（MY） | ROUTE|-|u1|exact | 17 | 88.2% | 11.8% |  |
| 马来西亚（MY） | POI|n2|- | 14 | 78.6% | 7.1% |  |
| 马来西亚（MY） | ROUTE|pc+area|uN|exact | 12 | 75.0% | 16.7% |  |
| 马来西亚（MY） | ROUTE|pc|uN|exact | 11 | 72.7% | 9.1% |  |
| 印尼（ID） | POI|n2|pc | 71 | 62.0% | 15.5% |  |
| 印尼（ID） | POI|n1|pc | 56 | 71.4% | 10.7% |  |
| 印尼（ID） | ROUTE|pc+area|uN|exact | 23 | 91.3% | 0.0% |  |
| 印尼（ID） | ROUTE|-+area|u1|exact | 11 | 81.8% | 9.1% |  |
| 泰国（TH） | ROUTE|-|u1|exact | 62 | 88.7% | 4.8% |  |
| 泰国（TH） | POI|n2|pc | 50 | 64.0% | 16.0% |  |
| 泰国（TH） | ROUTE|-|u1|core | 23 | 78.3% | 17.4% |  |
| 泰国（TH） | ROUTE|pc|u1|core | 18 | 66.7% | 16.7% |  |
| 泰国（TH） | POI|n1|pc | 16 | 81.2% | 12.5% |  |
| 泰国（TH） | POI|n2|- | 14 | 71.4% | 7.1% |  |
| 越南（VN） | POI|n1|pc | 22 | 77.3% | 4.5% |  |
| 越南（VN） | POI|n2|pc | 17 | 82.4% | 11.8% |  |
| 越南（VN） | ROUTE|pc+area|uN|exact | 13 | 69.2% | 23.1% |  |
| 越南（VN） | ROUTE|-+area|u1|exact | 13 | 100.0% | 0.0% |  |
| 越南（VN） | POI|n2|- | 10 | 40.0% | 50.0% |  |
| 菲律宾（PH） | POI|n2|pc | 59 | 79.7% | 11.9% |  |
| 菲律宾（PH） | ROUTE|pc+area|uN|exact | 44 | 90.9% | 6.8% |  |
| 菲律宾（PH） | POI|n1|pc | 31 | 90.3% | 0.0% |  |
| 菲律宾（PH） | ROUTE|-+area|u1|exact | 11 | 81.8% | 9.1% |  |
| 加拿大（CA） | PREMISE|POSTCODE_REPLACED | 49 | 91.8% | 8.2% |  |
| 加拿大（CA） | POI|n2|pc | 31 | 96.8% | 3.2% |  |
| 加拿大（CA） | POI|n1|pc | 22 | 90.9% | 9.1% |  |
| 墨西哥（MX） | PREMISE|POSTCODE_REPLACED | 50 | 76.0% | 20.0% |  |
| 墨西哥（MX） | POI|n1|pc | 16 | 87.5% | 12.5% |  |
| 墨西哥（MX） | POI|n2|pc | 15 | 86.7% | 0.0% |  |
| 波多黎各（PR） | ROUTE|pc|uN|exact | 43 | 90.7% | 4.7% |  |
| 波多黎各（PR） | POI|n2|pc | 26 | 73.1% | 11.5% |  |
| 波多黎各（PR） | ROUTE|-|u1|exact | 21 | 90.5% | 9.5% |  |
| 波多黎各（PR） | POI|n1|pc | 20 | 75.0% | 5.0% |  |
| 巴西（BR） | PREMISE|POSTCODE_REPLACED | 109 | 95.4% | 0.9% | 是 |
| 巴西（BR） | POI|n2|pc | 23 | 95.7% | 0.0% |  |
| 阿根廷（AR） | ROUTE|pc+area|uN|exact | 139 | 97.1% | 1.4% | 是 |
| 阿根廷（AR） | POI|n2|pc | 45 | 95.6% | 0.0% |  |
| 阿根廷（AR） | POI|n1|pc | 36 | 97.2% | 0.0% |  |
| 阿根廷（AR） | ROUTE|-+area|u1|exact | 14 | 85.7% | 14.3% |  |
| 阿根廷（AR） | ROUTE|-+area|uN|exact | 10 | 80.0% | 20.0% |  |
| 智利（CL） | POI|n2|pc | 34 | 94.1% | 2.9% |  |
| 哥伦比亚（CO） | POI|n2|pc | 38 | 89.5% | 5.3% |  |
| 哥伦比亚（CO） | POI|n1|pc | 26 | 80.8% | 15.4% |  |
| 英国（GB） | POI|n2|pc | 135 | 97.0% | 2.2% |  |
| 英国（GB） | POI|n1|pc | 59 | 91.5% | 5.1% |  |
| 英国（GB） | ROUTE|pc|uN|exact | 47 | 97.9% | 0.0% | 是 |
| 英国（GB） | ROUTE|-|u1|exact | 23 | 82.6% | 17.4% |  |
| 爱尔兰（IE） | POI|n2|pc | 40 | 90.0% | 2.5% |  |
| 爱尔兰（IE） | POI|n1|pc | 38 | 86.8% | 2.6% |  |
| 爱尔兰（IE） | ROUTE|pc|uN|exact | 26 | 92.3% | 7.7% |  |
| 爱尔兰（IE） | ROUTE|-|u1|exact | 10 | 70.0% | 20.0% |  |
| 卢森堡（LU） | PREMISE|POSTCODE_REPLACED | 22 | 63.6% | 27.3% |  |
| 葡萄牙（PT） | POI|n2|pc | 67 | 88.1% | 9.0% |  |
| 葡萄牙（PT） | PREMISE|POSTCODE_REPLACED | 39 | 79.5% | 10.3% |  |
| 葡萄牙（PT） | POI|n1|pc | 34 | 91.2% | 8.8% |  |
| 瑞典（SE） | POI|n2|pc | 68 | 95.6% | 1.5% |  |
| 瑞典（SE） | POI|n1|pc | 56 | 94.6% | 3.6% |  |
| 瑞典（SE） | ROUTE|pc|uN|exact | 35 | 91.4% | 2.9% |  |
| 瑞典（SE） | ROUTE|pc+area|uN|exact | 13 | 100.0% | 0.0% |  |
| 挪威（NO） | POI|n2|pc | 15 | 93.3% | 0.0% |  |
| 挪威（NO） | POI|n1|pc | 11 | 100.0% | 0.0% |  |
| 芬兰（FI） | POI|n2|pc | 22 | 95.5% | 4.5% |  |
| 芬兰（FI） | PREMISE|POSTCODE_REPLACED | 12 | 83.3% | 8.3% |  |
| 芬兰（FI） | POI|n1|pc | 12 | 91.7% | 0.0% |  |
| 立陶宛（LT） | PREMISE|POSTCODE_REPLACED | 103 | 98.1% | 1.9% | 是 |
| 波兰（PL） | PREMISE|POSTCODE_REPLACED | 40 | 80.0% | 2.5% |  |
| 捷克（CZ） | PREMISE|POSTCODE_REPLACED | 18 | 88.9% | 11.1% |  |
| 斯洛伐克（SK） | PREMISE|POSTCODE_REPLACED | 25 | 96.0% | 4.0% |  |
| 匈牙利（HU） | POI|n2|pc | 111 | 93.7% | 3.6% |  |
| 匈牙利（HU） | ROUTE|pc|uN|exact | 102 | 97.1% | 2.0% | 是 |
| 匈牙利（HU） | POI|n1|pc | 92 | 90.2% | 5.4% |  |
| 匈牙利（HU） | ROUTE|-|u1|exact | 15 | 93.3% | 0.0% |  |
| 克罗地亚（HR） | PREMISE|POSTCODE_REPLACED | 196 | 94.9% | 2.0% |  |
| 保加利亚（BG） | ROUTE|pc|u1|core | 144 | 98.6% | 1.4% | 是 |
| 保加利亚（BG） | POI|n2|pc | 85 | 90.6% | 4.7% |  |
| 保加利亚（BG） | POI|n1|pc | 84 | 92.9% | 0.0% |  |
| 保加利亚（BG） | ROUTE|-|u1|core | 18 | 72.2% | 22.2% |  |
| 保加利亚（BG） | POI|n2|- | 12 | 91.7% | 8.3% |  |
| 保加利亚（BG） | ROUTE|pc|uN|core | 12 | 91.7% | 8.3% |  |
| 新西兰（NZ） | POI|n2|pc | 17 | 94.1% | 0.0% |  |
| 印度（IN） | POI|n1|pc | 27 | 66.7% | 14.8% |  |
| 印度（IN） | POI|n2|pc | 16 | 68.8% | 0.0% |  |
