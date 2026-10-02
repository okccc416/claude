# 直接通过的放宽规则（开发集校准，自动生成）

条件：样本 ≥ 25、正确率 ≥ 95%（Wilson 下界 ≥ 88%）、偏差 >1 公里 ≤ 2%。未列出的组合仍按默认规则（A 类邮编被替换 -> 要求确认；B / C 类道路级要邮编印证 + 道路名唯一 + 名称完全一致）。

| 市场 | 证据组合 | 样本 | 正确 | 偏差 >1 公里 | 允许直接通过 |
|---|---|---|---|---|---|
| 加拿大（CA） | PREMISE|POSTCODE_REPLACED | 41 | 92.7% | 7.3% |  |
| 墨西哥（MX） | PREMISE|POSTCODE_REPLACED | 46 | 76.1% | 21.7% |  |
| 波多黎各（PR） | ROUTE|pc|uN|exact | 56 | 89.3% | 5.4% |  |
| 波多黎各（PR） | ROUTE|-|u1|exact | 22 | 90.9% | 9.1% |  |
| 波多黎各（PR） | ROUTE|pc+area|uN|exact | 10 | 70.0% | 20.0% |  |
| 巴西（BR） | PREMISE|POSTCODE_REPLACED | 95 | 94.7% | 1.1% |  |
| 阿根廷（AR） | ROUTE|pc|uN|exact | 162 | 94.4% | 1.2% |  |
| 阿根廷（AR） | ROUTE|-|u1|exact | 41 | 82.9% | 17.1% |  |
| 阿根廷（AR） | ROUTE|pc+area|uN|exact | 16 | 100.0% | 0.0% |  |
| 阿根廷（AR） | ROUTE|-+area|uN|exact | 12 | 91.7% | 8.3% |  |
| 英国（GB） | ROUTE|pc|uN|exact | 75 | 98.7% | 1.3% | 是 |
| 英国（GB） | ROUTE|-|u1|exact | 28 | 85.7% | 14.3% |  |
| 爱尔兰（IE） | ROUTE|-|u1|exact | 70 | 90.0% | 7.1% |  |
| 爱尔兰（IE） | ROUTE|pc|uN|exact | 23 | 91.3% | 8.7% |  |
| 爱尔兰（IE） | ROUTE|-+area|u1|exact | 13 | 61.5% | 30.8% |  |
| 卢森堡（LU） | PREMISE|POSTCODE_REPLACED | 22 | 63.6% | 27.3% |  |
| 葡萄牙（PT） | PREMISE|POSTCODE_REPLACED | 34 | 88.2% | 2.9% |  |
| 瑞典（SE） | ROUTE|pc|uN|exact | 50 | 82.0% | 10.0% |  |
| 瑞典（SE） | ROUTE|pc+area|uN|exact | 15 | 100.0% | 0.0% |  |
| 瑞典（SE） | ROUTE|-|u1|exact | 14 | 92.9% | 0.0% |  |
| 芬兰（FI） | PREMISE|POSTCODE_REPLACED | 12 | 83.3% | 8.3% |  |
| 立陶宛（LT） | PREMISE|POSTCODE_REPLACED | 103 | 98.1% | 1.9% | 是 |
| 波兰（PL） | PREMISE|POSTCODE_REPLACED | 37 | 81.1% | 2.7% |  |
| 捷克（CZ） | PREMISE|POSTCODE_REPLACED | 11 | 81.8% | 18.2% |  |
| 斯洛伐克（SK） | PREMISE|POSTCODE_REPLACED | 22 | 95.5% | 4.5% |  |
| 匈牙利（HU） | ROUTE|pc|uN|exact | 145 | 96.6% | 2.8% |  |
| 匈牙利（HU） | ROUTE|-|u1|exact | 15 | 93.3% | 0.0% |  |
| 克罗地亚（HR） | PREMISE|POSTCODE_REPLACED | 191 | 95.3% | 2.1% |  |
| 保加利亚（BG） | ROUTE|pc|u1|core | 229 | 96.9% | 1.3% | 是 |
| 保加利亚（BG） | ROUTE|pc|uN|core | 20 | 90.0% | 10.0% |  |
| 保加利亚（BG） | ROUTE|-|u1|core | 18 | 83.3% | 16.7% |  |
| 保加利亚（BG） | ROUTE|-|u1|exact | 15 | 66.7% | 20.0% |  |
| 印度（IN） | ROUTE|pc|uN|exact | 13 | 84.6% | 0.0% |  |
| 印度（IN） | ROUTE|-|u1|exact | 11 | 9.1% | 90.9% |  |
