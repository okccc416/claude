# 直接通过的放宽规则（开发集校准，自动生成）

条件：样本 ≥ 25、正确率 ≥ 95%（Wilson 下界 ≥ 88%）、偏差 >1 公里 ≤ 2%。未列出的组合仍按默认规则（A 类邮编被替换 -> 要求确认；B / C 类道路级要邮编印证 + 道路名唯一 + 名称完全一致）。

| 市场 | 证据组合 | 样本 | 正确 | 偏差 >1 公里 | 允许直接通过 |
|---|---|---|---|---|---|
| 澳大利亚（AU） | PREMISE|POSTCODE_REPLACED | 14 | 28.6% | 57.1% |  |
| 法国（FR） | PREMISE|POSTCODE_REPLACED | 11 | 72.7% | 9.1% |  |
| 荷兰（NL） | PREMISE|POSTCODE_REPLACED | 20 | 100.0% | 0.0% |  |
| 阿联酋（AE） | ROUTE|-|u1|exact | 34 | 70.6% | 23.5% |  |
| 马来西亚（MY） | ROUTE|-+area|u1|exact | 48 | 95.8% | 2.1% |  |
| 马来西亚（MY） | ROUTE|-|u1|exact | 25 | 96.0% | 4.0% |  |
| 马来西亚（MY） | ROUTE|pc+area|uN|exact | 22 | 72.7% | 13.6% |  |
| 马来西亚（MY） | ROUTE|pc|uN|exact | 16 | 75.0% | 12.5% |  |
| 印尼（ID） | ROUTE|pc+area|uN|exact | 38 | 86.8% | 5.3% |  |
| 印尼（ID） | ROUTE|pc|uN|exact | 17 | 70.6% | 23.5% |  |
| 印尼（ID） | ROUTE|-+area|u1|exact | 15 | 66.7% | 20.0% |  |
| 泰国（TH） | ROUTE|-|u1|exact | 71 | 87.3% | 4.2% |  |
| 泰国（TH） | ROUTE|pc|u1|core | 25 | 76.0% | 12.0% |  |
| 泰国（TH） | ROUTE|-|u1|core | 25 | 76.0% | 16.0% |  |
| 越南（VN） | ROUTE|-+area|u1|exact | 20 | 85.0% | 15.0% |  |
| 越南（VN） | ROUTE|pc+area|uN|exact | 16 | 62.5% | 18.8% |  |
| 越南（VN） | ROUTE|-|u1|exact | 13 | 53.8% | 38.5% |  |
| 越南（VN） | ROUTE|-+area|uN|exact | 11 | 63.6% | 36.4% |  |
| 菲律宾（PH） | ROUTE|pc+area|uN|exact | 71 | 91.5% | 4.2% |  |
| 菲律宾（PH） | ROUTE|-+area|u1|exact | 13 | 84.6% | 7.7% |  |
| 菲律宾（PH） | ROUTE|pc+area|uN|core | 10 | 90.0% | 0.0% |  |
| 加拿大（CA） | PREMISE|POSTCODE_REPLACED | 41 | 92.7% | 7.3% |  |
| 墨西哥（MX） | PREMISE|POSTCODE_REPLACED | 46 | 76.1% | 21.7% |  |
| 波多黎各（PR） | ROUTE|pc|uN|exact | 56 | 89.3% | 5.4% |  |
| 波多黎各（PR） | ROUTE|-|u1|exact | 22 | 90.9% | 9.1% |  |
| 波多黎各（PR） | ROUTE|pc+area|uN|exact | 10 | 70.0% | 20.0% |  |
| 巴西（BR） | PREMISE|POSTCODE_REPLACED | 95 | 94.7% | 1.1% |  |
| 阿根廷（AR） | ROUTE|pc|uN|exact | 161 | 94.4% | 1.2% |  |
| 阿根廷（AR） | ROUTE|-|u1|exact | 51 | 84.3% | 15.7% |  |
| 阿根廷（AR） | ROUTE|-+area|uN|exact | 14 | 92.9% | 7.1% |  |
| 阿根廷（AR） | ROUTE|pc+area|uN|exact | 13 | 100.0% | 0.0% |  |
| 阿根廷（AR） | ROUTE|-+area|u1|exact | 10 | 90.0% | 10.0% |  |
| 英国（GB） | ROUTE|pc|uN|exact | 75 | 98.7% | 1.3% | 是 |
| 英国（GB） | ROUTE|-|u1|exact | 28 | 85.7% | 14.3% |  |
| 爱尔兰（IE） | ROUTE|-|u1|exact | 70 | 90.0% | 7.1% |  |
| 爱尔兰（IE） | ROUTE|pc|uN|exact | 23 | 91.3% | 8.7% |  |
| 爱尔兰（IE） | ROUTE|-+area|u1|exact | 13 | 61.5% | 30.8% |  |
| 卢森堡（LU） | PREMISE|POSTCODE_REPLACED | 22 | 63.6% | 27.3% |  |
| 葡萄牙（PT） | PREMISE|POSTCODE_REPLACED | 32 | 90.6% | 3.1% |  |
| 瑞典（SE） | ROUTE|pc|uN|exact | 50 | 82.0% | 10.0% |  |
| 瑞典（SE） | ROUTE|pc+area|uN|exact | 15 | 100.0% | 0.0% |  |
| 瑞典（SE） | ROUTE|-|u1|exact | 10 | 100.0% | 0.0% |  |
| 芬兰（FI） | PREMISE|POSTCODE_REPLACED | 12 | 83.3% | 8.3% |  |
| 立陶宛（LT） | PREMISE|POSTCODE_REPLACED | 103 | 98.1% | 1.9% | 是 |
| 波兰（PL） | PREMISE|POSTCODE_REPLACED | 37 | 81.1% | 2.7% |  |
| 捷克（CZ） | PREMISE|POSTCODE_REPLACED | 11 | 81.8% | 18.2% |  |
| 斯洛伐克（SK） | PREMISE|POSTCODE_REPLACED | 22 | 95.5% | 4.5% |  |
| 匈牙利（HU） | ROUTE|pc|uN|exact | 145 | 96.6% | 2.8% |  |
| 匈牙利（HU） | ROUTE|-|u1|exact | 15 | 93.3% | 0.0% |  |
| 克罗地亚（HR） | PREMISE|POSTCODE_REPLACED | 175 | 94.9% | 2.3% |  |
| 保加利亚（BG） | ROUTE|pc|u1|core | 227 | 96.9% | 1.3% | 是 |
| 保加利亚（BG） | ROUTE|pc|uN|core | 20 | 90.0% | 10.0% |  |
| 保加利亚（BG） | ROUTE|-|u1|core | 19 | 84.2% | 15.8% |  |
| 保加利亚（BG） | ROUTE|-|u1|exact | 15 | 66.7% | 20.0% |  |
| 印度（IN） | ROUTE|pc|uN|exact | 14 | 85.7% | 0.0% |  |
| 印度（IN） | ROUTE|-|u1|exact | 10 | 10.0% | 90.0% |  |
