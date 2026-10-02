# 多市场评测报告（自动生成）

- 真实地址：各城市留出的 20% 商户（不在参考库里）的自填地址，标准答案为商户坐标（弱标注）
- 合成地址：按各市场写法渲染的测试部分道路（AI 解析器训练时没见过），标准答案已知
- 解析方式：rules = 规则 + 地名表；crf = 机器学习（条件随机场）；hybrid = 两者都出候选，由参考数据裁决
- 判对标准（真实地址）：门牌级 ≤ 250 米、楼宇级 ≤ 400 米、道路级为该道路经过商户 250 米内；"偏差 >1 公里"的静默错误不是商户坐标不准能解释的，是真正的错

## 真实商户地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 600 | 75.3% | 8.0% | 1.0% | 10.0% | 3.0% | 2.7% | 1.5% | 89.5% | 2 |
| 澳大利亚（AU） | A | crf | 600 | 70.0% | 6.5% | 2.5% | 15.0% | 3.3% | 2.7% | 1.5% | 88.8% | 2 |
| 澳大利亚（AU） | A | hybrid | 600 | 76.2% | 7.0% | 1.0% | 9.8% | 3.2% | 2.8% | 1.7% | 89.2% | 4 |
| 德国（DE） | A | rules | 600 | 92.7% | 2.7% | 0.2% | 1.3% | 2.2% | 1.0% | 0.7% | 97.0% | 2 |
| 德国（DE） | A | crf | 600 | 85.8% | 2.5% | 0.5% | 8.7% | 1.7% | 0.8% | 0.5% | 95.0% | 1 |
| 德国（DE） | A | hybrid | 600 | 94.2% | 2.7% | 0.0% | 1.3% | 0.8% | 1.0% | 0.7% | 98.3% | 2 |
| 法国（FR） | A | rules | 600 | 87.0% | 4.7% | 0.3% | 4.5% | 1.7% | 1.8% | 1.0% | 95.2% | 1 |
| 法国（FR） | A | crf | 600 | 85.7% | 4.7% | 0.7% | 5.0% | 2.0% | 2.0% | 1.2% | 94.3% | 1 |
| 法国（FR） | A | hybrid | 600 | 87.5% | 4.7% | 0.0% | 4.5% | 1.3% | 2.0% | 1.2% | 95.8% | 2 |
| 荷兰（NL） | A | rules | 600 | 82.8% | 7.5% | 1.2% | 6.7% | 0.7% | 1.2% | 0.7% | 96.0% | 2 |
| 荷兰（NL） | A | crf | 600 | 70.5% | 14.5% | 1.3% | 11.7% | 1.0% | 1.0% | 0.5% | 96.3% | 1 |
| 荷兰（NL） | A | hybrid | 600 | 85.3% | 5.3% | 0.8% | 6.3% | 1.0% | 1.2% | 0.7% | 96.3% | 3 |
| 阿联酋（AE） | B | rules | 600 | 1.7% | 30.3% | 11.8% | 25.3% | 29.8% | 1.0% | 0.2% | 19.5% | 3 |
| 阿联酋（AE） | B | crf | 600 | 0.7% | 18.8% | 7.3% | 52.7% | 20.0% | 0.5% | 0.2% | 11.3% | 2 |
| 阿联酋（AE） | B | hybrid | 600 | 1.7% | 30.5% | 10.8% | 21.8% | 34.2% | 1.0% | 0.2% | 20.2% | 5 |
| 沙特（SA） | B | rules | 600 | 2.0% | 29.2% | 11.2% | 14.5% | 42.7% | 0.5% | 0.5% | 16.7% | 3 |
| 沙特（SA） | B | crf | 600 | 1.8% | 28.3% | 15.5% | 26.7% | 27.0% | 0.7% | 0.7% | 17.8% | 2 |
| 沙特（SA） | B | hybrid | 600 | 2.2% | 33.5% | 8.7% | 13.5% | 41.7% | 0.5% | 0.5% | 19.3% | 6 |
| 马来西亚（MY） | C | rules | 600 | 33.3% | 35.0% | 4.2% | 5.0% | 19.5% | 3.0% | 1.2% | 54.2% | 3 |
| 马来西亚（MY） | C | crf | 600 | 27.5% | 38.8% | 13.3% | 7.2% | 10.3% | 2.8% | 1.2% | 56.7% | 2 |
| 马来西亚（MY） | C | hybrid | 600 | 33.2% | 38.5% | 3.7% | 3.3% | 18.2% | 3.2% | 1.2% | 58.2% | 4 |
| 印尼（ID） | C | rules | 600 | 26.5% | 30.2% | 1.7% | 3.8% | 34.3% | 3.5% | 0.3% | 40.3% | 2 |
| 印尼（ID） | C | crf | 600 | 8.5% | 35.5% | 27.0% | 7.8% | 19.5% | 1.7% | 0.3% | 44.2% | 4 |
| 印尼（ID） | C | hybrid | 600 | 26.5% | 32.8% | 1.3% | 3.5% | 32.2% | 3.7% | 0.5% | 43.0% | 6 |
| 泰国（TH） | C | rules | 600 | 15.8% | 41.7% | 11.5% | 8.3% | 20.5% | 2.2% | 0.7% | 27.7% | 6 |
| 泰国（TH） | C | crf | 600 | 12.5% | 27.7% | 25.8% | 20.7% | 12.2% | 1.2% | 0.3% | 19.5% | 3 |
| 泰国（TH） | C | hybrid | 600 | 15.8% | 41.0% | 10.5% | 8.2% | 22.2% | 2.3% | 0.7% | 27.3% | 8 |
| 越南（VN） | C | rules | 600 | 8.7% | 53.5% | 2.0% | 4.7% | 29.3% | 1.8% | 0.7% | 47.8% | 2 |
| 越南（VN） | C | crf | 600 | 8.8% | 35.7% | 21.3% | 17.0% | 15.8% | 1.3% | 0.7% | 40.3% | 2 |
| 越南（VN） | C | hybrid | 600 | 11.3% | 52.3% | 1.7% | 4.2% | 28.5% | 2.0% | 0.8% | 48.0% | 4 |
| 菲律宾（PH） | C | rules | 600 | 20.2% | 35.7% | 13.8% | 6.7% | 21.3% | 2.3% | 1.2% | 39.2% | 3 |
| 菲律宾（PH） | C | crf | 600 | 11.7% | 39.7% | 25.5% | 7.7% | 15.0% | 0.5% | 0.2% | 43.5% | 3 |
| 菲律宾（PH） | C | hybrid | 600 | 21.7% | 42.5% | 7.2% | 3.7% | 22.7% | 2.3% | 1.2% | 46.3% | 6 |
| 加拿大（CA） | A | rules | 600 | 61.2% | 25.3% | 0.3% | 9.3% | 2.0% | 1.8% | 0.7% | 93.0% | 2 |
| 加拿大（CA） | A | crf | 600 | 54.0% | 29.3% | 2.5% | 11.0% | 2.0% | 1.2% | 0.3% | 92.2% | 2 |
| 加拿大（CA） | A | hybrid | 600 | 62.5% | 24.2% | 0.3% | 9.2% | 2.0% | 1.8% | 0.7% | 93.0% | 3 |
| 墨西哥（MX） | A | rules | 600 | 34.7% | 19.2% | 1.5% | 26.5% | 15.7% | 2.5% | 1.2% | 67.8% | 2 |
| 墨西哥（MX） | A | crf | 600 | 26.8% | 18.3% | 8.0% | 30.8% | 13.3% | 2.7% | 1.2% | 62.8% | 2 |
| 墨西哥（MX） | A | hybrid | 600 | 36.3% | 19.2% | 1.3% | 25.2% | 15.5% | 2.5% | 1.2% | 69.0% | 4 |
| 波多黎各（PR） | C | rules | 600 | 15.5% | 29.2% | 12.2% | 9.8% | 31.8% | 1.5% | 0.7% | 36.3% | 2 |
| 波多黎各（PR） | C | crf | 600 | 12.0% | 23.8% | 24.2% | 18.0% | 20.5% | 1.5% | 0.7% | 31.8% | 1 |
| 波多黎各（PR） | C | hybrid | 600 | 15.5% | 31.0% | 10.7% | 9.3% | 32.0% | 1.5% | 0.7% | 37.3% | 3 |
| 巴西（BR） | A | rules | 600 | 52.2% | 30.0% | 0.7% | 11.5% | 3.8% | 1.8% | 0.3% | 91.5% | 3 |
| 巴西（BR） | A | crf | 600 | 45.8% | 30.0% | 3.7% | 15.5% | 3.5% | 1.5% | 0.3% | 89.8% | 2 |
| 巴西（BR） | A | hybrid | 600 | 52.2% | 31.3% | 0.7% | 10.8% | 3.2% | 1.8% | 0.3% | 92.7% | 5 |
| 阿根廷（AR） | C | rules | 600 | 30.7% | 45.3% | 4.0% | 4.7% | 14.3% | 1.0% | 0.8% | 48.7% | 2 |
| 阿根廷（AR） | C | crf | 600 | 9.8% | 56.8% | 3.8% | 6.8% | 22.0% | 0.7% | 0.7% | 34.7% | 1 |
| 阿根廷（AR） | C | hybrid | 600 | 30.2% | 49.2% | 2.7% | 2.7% | 14.3% | 1.0% | 0.8% | 48.5% | 4 |
| 智利（CL） | A | rules | 600 | 55.8% | 13.2% | 1.2% | 19.7% | 6.7% | 3.5% | 2.2% | 76.8% | 2 |
| 智利（CL） | A | crf | 600 | 53.2% | 12.3% | 4.5% | 24.0% | 2.8% | 3.2% | 1.7% | 74.2% | 1 |
| 智利（CL） | A | hybrid | 600 | 56.3% | 12.5% | 0.8% | 21.5% | 5.3% | 3.5% | 2.0% | 77.2% | 3 |
| 哥伦比亚（CO） | A | rules | 600 | 20.5% | 37.0% | 4.2% | 19.2% | 16.8% | 2.3% | 1.7% | 65.0% | 4 |
| 哥伦比亚（CO） | A | crf | 600 | 15.7% | 32.5% | 5.3% | 24.0% | 20.5% | 2.0% | 1.3% | 56.8% | 2 |
| 哥伦比亚（CO） | A | hybrid | 600 | 20.5% | 38.0% | 1.7% | 19.7% | 17.8% | 2.3% | 1.7% | 65.7% | 5 |
| 英国（GB） | C | rules | 600 | 68.7% | 20.0% | 3.0% | 1.8% | 4.7% | 1.8% | 1.0% | 88.2% | 2 |
| 英国（GB） | C | crf | 600 | 67.7% | 17.5% | 4.5% | 2.8% | 5.7% | 1.8% | 1.0% | 87.5% | 1 |
| 英国（GB） | C | hybrid | 600 | 71.0% | 19.0% | 1.5% | 1.3% | 5.3% | 1.8% | 1.0% | 88.7% | 3 |
| 爱尔兰（IE） | C | rules | 600 | 32.3% | 39.0% | 5.2% | 9.5% | 11.8% | 2.2% | 0.8% | 69.0% | 2 |
| 爱尔兰（IE） | C | crf | 600 | 30.3% | 34.7% | 5.3% | 19.3% | 8.3% | 2.0% | 1.0% | 63.8% | 1 |
| 爱尔兰（IE） | C | hybrid | 600 | 32.8% | 39.8% | 4.5% | 8.8% | 11.5% | 2.5% | 1.0% | 69.7% | 3 |
| 比利时（BE） | A | rules | 600 | 77.3% | 6.5% | 1.3% | 8.8% | 3.2% | 2.8% | 0.8% | 90.7% | 1 |
| 比利时（BE） | A | crf | 600 | 74.7% | 9.0% | 1.7% | 9.8% | 1.8% | 3.0% | 1.0% | 90.3% | 1 |
| 比利时（BE） | A | hybrid | 600 | 77.8% | 8.7% | 1.3% | 7.3% | 1.8% | 3.0% | 1.0% | 93.0% | 2 |
| 卢森堡（LU） | A | rules | 600 | 68.7% | 7.3% | 1.7% | 11.0% | 7.8% | 3.5% | 0.8% | 84.2% | 2 |
| 卢森堡（LU） | A | crf | 600 | 64.2% | 11.7% | 2.5% | 14.2% | 4.8% | 2.7% | 0.8% | 85.8% | 1 |
| 卢森堡（LU） | A | hybrid | 600 | 68.8% | 11.2% | 1.5% | 10.8% | 4.2% | 3.5% | 0.8% | 88.3% | 3 |
| 瑞士（CH） | A | rules | 600 | 88.2% | 3.3% | 0.8% | 3.3% | 2.5% | 1.8% | 1.3% | 94.0% | 1 |
| 瑞士（CH） | A | crf | 600 | 87.7% | 2.7% | 0.8% | 3.8% | 3.2% | 1.8% | 1.3% | 93.3% | 1 |
| 瑞士（CH） | A | hybrid | 600 | 89.7% | 2.5% | 0.7% | 3.0% | 2.2% | 2.0% | 1.5% | 94.5% | 2 |
| 奥地利（AT） | A | rules | 600 | 79.3% | 5.7% | 1.2% | 6.7% | 3.2% | 4.0% | 1.5% | 91.8% | 1 |
| 奥地利（AT） | A | crf | 600 | 75.8% | 6.8% | 1.7% | 8.5% | 3.5% | 3.7% | 1.7% | 88.5% | 1 |
| 奥地利（AT） | A | hybrid | 600 | 81.0% | 5.0% | 0.8% | 6.7% | 2.5% | 4.0% | 1.5% | 92.5% | 1 |
| 意大利（IT） | A | rules | 600 | 79.8% | 4.3% | 3.2% | 7.3% | 3.0% | 2.3% | 1.3% | 90.3% | 2 |
| 意大利（IT） | A | crf | 600 | 75.0% | 4.5% | 1.8% | 9.5% | 7.0% | 2.2% | 1.2% | 86.2% | 1 |
| 意大利（IT） | A | hybrid | 600 | 80.3% | 3.8% | 2.7% | 7.3% | 3.5% | 2.3% | 1.3% | 90.3% | 3 |
| 西班牙（ES） | A | rules | 600 | 82.7% | 2.8% | 1.2% | 8.5% | 3.2% | 1.7% | 0.5% | 92.8% | 2 |
| 西班牙（ES） | A | crf | 600 | 80.0% | 4.0% | 2.3% | 8.3% | 4.0% | 1.3% | 0.7% | 91.3% | 1 |
| 西班牙（ES） | A | hybrid | 600 | 84.2% | 3.0% | 1.2% | 8.0% | 1.8% | 1.8% | 0.7% | 94.5% | 3 |
| 葡萄牙（PT） | A | rules | 600 | 14.2% | 44.0% | 1.8% | 31.7% | 7.3% | 1.0% | 0.7% | 83.0% | 2 |
| 葡萄牙（PT） | A | crf | 600 | 8.2% | 40.2% | 7.0% | 37.8% | 5.8% | 1.0% | 0.7% | 81.5% | 2 |
| 葡萄牙（PT） | A | hybrid | 600 | 14.2% | 44.0% | 1.5% | 31.8% | 7.5% | 1.0% | 0.7% | 83.5% | 4 |
| 丹麦（DK） | A | rules | 600 | 86.0% | 7.0% | 0.2% | 3.5% | 1.3% | 2.0% | 0.3% | 95.8% | 1 |
| 丹麦（DK） | A | crf | 600 | 84.5% | 5.2% | 0.0% | 6.8% | 1.5% | 2.0% | 0.3% | 94.3% | 1 |
| 丹麦（DK） | A | hybrid | 600 | 87.8% | 5.2% | 0.2% | 3.5% | 1.3% | 2.0% | 0.3% | 95.8% | 2 |
| 瑞典（SE） | C | rules | 600 | 75.5% | 16.3% | 4.0% | 0.5% | 2.5% | 1.2% | 0.5% | 90.7% | 1 |
| 瑞典（SE） | C | crf | 600 | 68.0% | 22.5% | 2.3% | 3.7% | 2.3% | 1.2% | 0.5% | 87.5% | 1 |
| 瑞典（SE） | C | hybrid | 600 | 75.3% | 17.5% | 3.2% | 0.2% | 2.7% | 1.2% | 0.5% | 91.2% | 2 |
| 挪威（NO） | A | rules | 600 | 73.5% | 18.3% | 0.7% | 3.7% | 1.7% | 2.2% | 0.7% | 96.2% | 1 |
| 挪威（NO） | A | crf | 600 | 74.7% | 16.0% | 1.0% | 4.2% | 2.3% | 1.8% | 0.3% | 95.5% | 1 |
| 挪威（NO） | A | hybrid | 600 | 75.8% | 16.7% | 0.7% | 3.0% | 1.7% | 2.2% | 0.7% | 96.2% | 1 |
| 芬兰（FI） | A | rules | 600 | 73.5% | 17.2% | 2.0% | 2.3% | 2.2% | 2.8% | 0.8% | 95.8% | 1 |
| 芬兰（FI） | A | crf | 600 | 71.0% | 16.5% | 2.8% | 3.0% | 3.7% | 3.0% | 0.8% | 93.0% | 1 |
| 芬兰（FI） | A | hybrid | 600 | 74.0% | 16.2% | 1.8% | 2.5% | 2.5% | 3.0% | 0.8% | 95.3% | 2 |
| 爱沙尼亚（EE） | A | rules | 600 | 79.7% | 3.7% | 8.0% | 3.5% | 1.0% | 4.2% | 1.8% | 92.8% | 1 |
| 爱沙尼亚（EE） | A | crf | 600 | 77.3% | 3.3% | 3.0% | 10.8% | 1.5% | 4.0% | 1.8% | 91.8% | 1 |
| 爱沙尼亚（EE） | A | hybrid | 600 | 83.5% | 3.5% | 0.8% | 6.5% | 1.3% | 4.3% | 1.8% | 94.2% | 2 |
| 拉脱维亚（LV） | A | rules | 600 | 78.2% | 3.2% | 0.8% | 7.7% | 4.7% | 5.5% | 1.8% | 86.7% | 1 |
| 拉脱维亚（LV） | A | crf | 600 | 73.5% | 4.5% | 0.5% | 10.8% | 5.8% | 4.8% | 1.8% | 82.2% | 1 |
| 拉脱维亚（LV） | A | hybrid | 600 | 78.3% | 3.3% | 0.7% | 7.0% | 5.0% | 5.7% | 2.0% | 86.7% | 2 |
| 立陶宛（LT） | A | rules | 600 | 84.5% | 5.7% | 0.7% | 4.5% | 2.2% | 2.5% | 1.5% | 93.7% | 1 |
| 立陶宛（LT） | A | crf | 600 | 79.8% | 5.5% | 0.0% | 8.7% | 3.8% | 2.2% | 1.3% | 87.7% | 1 |
| 立陶宛（LT） | A | hybrid | 600 | 86.0% | 4.8% | 0.5% | 4.2% | 1.8% | 2.7% | 1.8% | 94.2% | 2 |
| 波兰（PL） | A | rules | 600 | 68.8% | 14.3% | 1.2% | 6.5% | 5.5% | 3.7% | 1.5% | 91.0% | 2 |
| 波兰（PL） | A | crf | 600 | 64.2% | 15.2% | 3.8% | 6.7% | 6.5% | 3.7% | 1.5% | 89.7% | 1 |
| 波兰（PL） | A | hybrid | 600 | 69.8% | 13.8% | 1.0% | 6.3% | 5.3% | 3.7% | 1.5% | 91.3% | 3 |
| 捷克（CZ） | A | rules | 600 | 83.3% | 5.0% | 0.2% | 7.2% | 1.5% | 2.8% | 0.7% | 94.5% | 1 |
| 捷克（CZ） | A | crf | 600 | 79.8% | 7.3% | 0.5% | 8.0% | 1.8% | 2.5% | 0.3% | 93.5% | 1 |
| 捷克（CZ） | A | hybrid | 600 | 83.7% | 4.7% | 0.2% | 7.0% | 1.5% | 3.0% | 0.7% | 94.5% | 1 |
| 斯洛伐克（SK） | A | rules | 600 | 71.0% | 8.8% | 0.0% | 9.3% | 8.0% | 2.8% | 0.5% | 87.0% | 1 |
| 斯洛伐克（SK） | A | crf | 600 | 69.2% | 9.7% | 2.2% | 13.2% | 3.0% | 2.8% | 0.3% | 88.8% | 1 |
| 斯洛伐克（SK） | A | hybrid | 600 | 73.0% | 9.8% | 0.0% | 9.0% | 5.0% | 3.2% | 0.5% | 90.2% | 2 |
| 匈牙利（HU） | C | rules | 600 | 58.3% | 35.2% | 2.2% | 0.7% | 2.2% | 1.5% | 0.8% | 77.8% | 2 |
| 匈牙利（HU） | C | crf | 600 | 57.5% | 35.5% | 2.8% | 0.7% | 2.0% | 1.5% | 0.8% | 77.5% | 1 |
| 匈牙利（HU） | C | hybrid | 600 | 58.3% | 35.5% | 2.0% | 0.5% | 2.2% | 1.5% | 0.8% | 78.2% | 3 |
| 斯洛文尼亚（SI） | A | rules | 600 | 79.7% | 4.0% | 1.0% | 4.3% | 4.7% | 6.3% | 3.7% | 89.0% | 1 |
| 斯洛文尼亚（SI） | A | crf | 600 | 81.5% | 2.8% | 0.5% | 4.8% | 4.2% | 6.2% | 3.5% | 89.2% | 1 |
| 斯洛文尼亚（SI） | A | hybrid | 600 | 83.8% | 2.8% | 0.7% | 4.3% | 2.2% | 6.2% | 3.5% | 91.5% | 2 |
| 克罗地亚（HR） | A | rules | 600 | 40.0% | 35.5% | 2.2% | 8.7% | 11.3% | 2.3% | 0.5% | 83.3% | 1 |
| 克罗地亚（HR） | A | crf | 600 | 63.7% | 15.2% | 1.2% | 12.8% | 4.0% | 3.2% | 1.0% | 86.0% | 1 |
| 克罗地亚（HR） | A | hybrid | 600 | 47.7% | 33.2% | 1.8% | 8.5% | 6.3% | 2.5% | 0.5% | 88.5% | 2 |
| 保加利亚（BG） | C | rules | 600 | 58.5% | 21.7% | 10.5% | 0.8% | 5.8% | 2.7% | 1.3% | 68.5% | 1 |
| 保加利亚（BG） | C | crf | 600 | 55.2% | 20.5% | 13.5% | 2.8% | 5.8% | 2.2% | 0.8% | 65.2% | 1 |
| 保加利亚（BG） | C | hybrid | 600 | 58.5% | 22.3% | 9.3% | 0.8% | 6.3% | 2.7% | 1.3% | 68.3% | 2 |
| 新西兰（NZ） | A | rules | 600 | 70.2% | 14.7% | 1.7% | 8.3% | 2.2% | 3.0% | 1.8% | 91.2% | 1 |
| 新西兰（NZ） | A | crf | 600 | 68.5% | 14.0% | 3.5% | 8.5% | 2.5% | 3.0% | 1.7% | 89.2% | 1 |
| 新西兰（NZ） | A | hybrid | 600 | 70.7% | 14.8% | 1.0% | 8.3% | 2.0% | 3.2% | 1.8% | 91.7% | 2 |
| 日本（JP） | A | rules | 600 | 80.5% | 0.3% | 8.3% | 3.8% | 0.3% | 6.7% | 2.5% | 90.7% | 1 |
| 日本（JP） | A | crf | 600 | 57.8% | 5.8% | 22.2% | 6.5% | 3.3% | 4.3% | 1.5% | 77.3% | 1 |
| 日本（JP） | A | hybrid | 600 | 79.7% | 2.5% | 5.2% | 3.2% | 3.2% | 6.3% | 2.3% | 89.3% | 3 |
| 印度（IN） | C | rules | 600 | 10.7% | 21.5% | 33.0% | 6.2% | 26.3% | 2.3% | 0.2% | 39.3% | 5 |
| 印度（IN） | C | crf | 600 | 3.5% | 13.3% | 63.8% | 6.7% | 12.0% | 0.7% | 0.0% | 36.2% | 3 |
| 印度（IN） | C | hybrid | 600 | 10.7% | 22.8% | 30.8% | 5.3% | 27.8% | 2.5% | 0.2% | 40.0% | 8 |

## 合成地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 600 | 82.8% | 8.0% | 0.0% | 4.8% | 4.3% | 0.0% | 0.0% | 95.7% | 2 |
| 澳大利亚（AU） | A | crf | 600 | 87.0% | 6.5% | 0.0% | 4.7% | 1.7% | 0.2% | 0.0% | 98.0% | 1 |
| 澳大利亚（AU） | A | hybrid | 600 | 87.2% | 6.0% | 0.0% | 4.7% | 2.0% | 0.2% | 0.0% | 97.7% | 3 |
| 德国（DE） | A | rules | 600 | 82.7% | 6.8% | 0.0% | 4.8% | 3.8% | 1.8% | 0.2% | 95.5% | 2 |
| 德国（DE） | A | crf | 600 | 86.5% | 8.0% | 0.0% | 4.2% | 1.2% | 0.2% | 0.2% | 98.3% | 1 |
| 德国（DE） | A | hybrid | 600 | 85.0% | 7.7% | 0.0% | 4.2% | 1.3% | 1.8% | 0.2% | 98.3% | 3 |
| 法国（FR） | A | rules | 600 | 87.8% | 3.2% | 0.0% | 7.5% | 1.2% | 0.3% | 0.0% | 97.5% | 1 |
| 法国（FR） | A | crf | 600 | 89.3% | 4.0% | 0.0% | 6.2% | 0.5% | 0.0% | 0.0% | 99.2% | 1 |
| 法国（FR） | A | hybrid | 600 | 89.7% | 3.3% | 0.0% | 6.2% | 0.5% | 0.3% | 0.0% | 99.2% | 2 |
| 荷兰（NL） | A | rules | 600 | 84.0% | 9.7% | 0.0% | 5.0% | 1.2% | 0.2% | 0.0% | 99.7% | 2 |
| 荷兰（NL） | A | crf | 600 | 85.7% | 9.0% | 0.0% | 5.2% | 0.2% | 0.0% | 0.0% | 99.8% | 1 |
| 荷兰（NL） | A | hybrid | 600 | 85.8% | 8.7% | 0.0% | 4.8% | 0.5% | 0.2% | 0.0% | 99.8% | 3 |
| 阿联酋（AE） | B | rules | 600 | 1.5% | 49.5% | 0.0% | 31.3% | 17.3% | 0.3% | 0.0% | 52.5% | 2 |
| 阿联酋（AE） | B | crf | 600 | 4.8% | 71.8% | 0.0% | 0.8% | 22.5% | 0.0% | 0.0% | 72.5% | 1 |
| 阿联酋（AE） | B | hybrid | 600 | 4.8% | 72.2% | 0.0% | 0.3% | 22.7% | 0.0% | 0.0% | 72.7% | 3 |
| 沙特（SA） | B | rules | 600 | 9.0% | 67.5% | 0.0% | 6.8% | 16.7% | 0.0% | 0.0% | 75.0% | 2 |
| 沙特（SA） | B | crf | 600 | 11.3% | 80.0% | 0.0% | 0.8% | 7.8% | 0.0% | 0.0% | 88.5% | 1 |
| 沙特（SA） | B | hybrid | 600 | 11.5% | 80.2% | 0.0% | 0.2% | 8.2% | 0.0% | 0.0% | 88.8% | 3 |
| 马来西亚（MY） | C | rules | 600 | 19.5% | 72.5% | 0.0% | 2.2% | 5.8% | 0.0% | 0.0% | 91.0% | 2 |
| 马来西亚（MY） | C | crf | 600 | 23.3% | 74.2% | 0.0% | 0.2% | 2.3% | 0.0% | 0.0% | 95.8% | 1 |
| 马来西亚（MY） | C | hybrid | 600 | 23.3% | 73.5% | 0.0% | 0.2% | 3.0% | 0.0% | 0.0% | 95.2% | 3 |
| 印尼（ID） | C | rules | 600 | 21.8% | 65.3% | 0.0% | 0.7% | 12.0% | 0.2% | 0.0% | 87.2% | 2 |
| 印尼（ID） | C | crf | 600 | 31.7% | 61.3% | 0.0% | 0.0% | 7.0% | 0.0% | 0.0% | 92.3% | 2 |
| 印尼（ID） | C | hybrid | 600 | 31.8% | 60.8% | 0.0% | 0.0% | 7.2% | 0.2% | 0.0% | 92.0% | 3 |
| 泰国（TH） | C | rules | 600 | 16.3% | 78.0% | 0.0% | 1.8% | 3.5% | 0.3% | 0.2% | 93.2% | 3 |
| 泰国（TH） | C | crf | 600 | 20.2% | 77.7% | 0.0% | 0.5% | 1.5% | 0.2% | 0.0% | 96.0% | 2 |
| 泰国（TH） | C | hybrid | 600 | 20.3% | 77.2% | 0.0% | 0.2% | 2.2% | 0.2% | 0.0% | 95.8% | 5 |
| 越南（VN） | C | rules | 600 | 28.7% | 62.5% | 0.0% | 0.8% | 7.8% | 0.2% | 0.0% | 91.3% | 3 |
| 越南（VN） | C | crf | 600 | 40.0% | 56.2% | 0.0% | 0.2% | 3.7% | 0.0% | 0.0% | 95.7% | 2 |
| 越南（VN） | C | hybrid | 600 | 40.5% | 55.3% | 0.0% | 0.0% | 4.0% | 0.2% | 0.0% | 95.5% | 4 |
| 菲律宾（PH） | C | rules | 600 | 21.7% | 61.7% | 0.0% | 4.8% | 11.8% | 0.0% | 0.0% | 82.5% | 2 |
| 菲律宾（PH） | C | crf | 600 | 28.0% | 60.2% | 0.0% | 0.0% | 11.8% | 0.0% | 0.0% | 86.5% | 2 |
| 菲律宾（PH） | C | hybrid | 600 | 28.2% | 62.0% | 0.0% | 0.0% | 9.8% | 0.0% | 0.0% | 87.7% | 4 |
| 加拿大（CA） | A | rules | 600 | 87.5% | 6.5% | 0.0% | 5.5% | 0.3% | 0.2% | 0.0% | 99.0% | 2 |
| 加拿大（CA） | A | crf | 600 | 87.0% | 7.7% | 0.0% | 4.5% | 0.7% | 0.2% | 0.0% | 99.5% | 1 |
| 加拿大（CA） | A | hybrid | 600 | 87.8% | 7.5% | 0.0% | 4.2% | 0.3% | 0.2% | 0.0% | 99.7% | 2 |
| 墨西哥（MX） | A | rules | 600 | 65.2% | 13.0% | 0.0% | 10.2% | 9.7% | 2.0% | 0.7% | 92.7% | 2 |
| 墨西哥（MX） | A | crf | 600 | 66.8% | 14.8% | 0.0% | 11.0% | 6.2% | 1.2% | 0.2% | 95.0% | 1 |
| 墨西哥（MX） | A | hybrid | 600 | 69.5% | 12.8% | 0.0% | 8.7% | 6.7% | 2.3% | 0.5% | 95.0% | 4 |
| 波多黎各（PR） | C | rules | 600 | 10.0% | 70.2% | 0.0% | 1.8% | 18.0% | 0.0% | 0.0% | 78.2% | 1 |
| 波多黎各（PR） | C | crf | 600 | 10.2% | 73.5% | 0.0% | 1.5% | 14.8% | 0.0% | 0.0% | 81.0% | 1 |
| 波多黎各（PR） | C | hybrid | 600 | 10.2% | 73.3% | 0.0% | 0.3% | 16.2% | 0.0% | 0.0% | 81.0% | 3 |
| 巴西（BR） | A | rules | 600 | 83.0% | 6.3% | 0.0% | 8.8% | 1.7% | 0.2% | 0.0% | 98.0% | 5 |
| 巴西（BR） | A | crf | 600 | 83.0% | 7.8% | 0.0% | 8.5% | 0.5% | 0.2% | 0.0% | 99.5% | 1 |
| 巴西（BR） | A | hybrid | 600 | 83.0% | 7.8% | 0.0% | 8.3% | 0.7% | 0.2% | 0.0% | 99.3% | 6 |
| 阿根廷（AR） | C | rules | 600 | 2.8% | 79.7% | 0.0% | 1.8% | 15.5% | 0.2% | 0.0% | 69.2% | 2 |
| 阿根廷（AR） | C | crf | 600 | 5.8% | 82.2% | 0.0% | 1.3% | 10.5% | 0.2% | 0.0% | 75.0% | 1 |
| 阿根廷（AR） | C | hybrid | 600 | 5.8% | 83.0% | 0.0% | 0.2% | 10.8% | 0.2% | 0.0% | 72.7% | 3 |
| 智利（CL） | A | rules | 600 | 86.0% | 3.7% | 0.0% | 6.5% | 3.3% | 0.5% | 0.3% | 93.8% | 1 |
| 智利（CL） | A | crf | 600 | 89.0% | 5.5% | 0.0% | 4.2% | 1.3% | 0.0% | 0.0% | 98.2% | 1 |
| 智利（CL） | A | hybrid | 600 | 88.5% | 6.0% | 0.0% | 3.8% | 1.5% | 0.2% | 0.2% | 98.3% | 3 |
| 哥伦比亚（CO） | A | rules | 600 | 89.3% | 0.0% | 0.0% | 4.2% | 6.5% | 0.0% | 0.0% | 94.7% | 3 |
| 哥伦比亚（CO） | A | crf | 600 | 89.3% | 1.0% | 0.0% | 4.3% | 5.3% | 0.0% | 0.0% | 95.5% | 1 |
| 哥伦比亚（CO） | A | hybrid | 600 | 89.3% | 1.0% | 0.0% | 3.8% | 5.8% | 0.0% | 0.0% | 95.5% | 3 |
| 英国（GB） | C | rules | 600 | 31.0% | 65.5% | 0.0% | 1.8% | 1.3% | 0.3% | 0.0% | 96.0% | 2 |
| 英国（GB） | C | crf | 600 | 35.8% | 62.3% | 0.0% | 0.3% | 1.5% | 0.0% | 0.0% | 97.2% | 2 |
| 英国（GB） | C | hybrid | 600 | 34.0% | 64.5% | 0.0% | 0.2% | 1.2% | 0.2% | 0.0% | 97.7% | 3 |
| 爱尔兰（IE） | C | rules | 600 | 24.2% | 72.0% | 0.0% | 2.3% | 1.2% | 0.3% | 0.0% | 96.5% | 2 |
| 爱尔兰（IE） | C | crf | 600 | 26.7% | 70.8% | 0.0% | 0.7% | 1.8% | 0.0% | 0.0% | 96.2% | 1 |
| 爱尔兰（IE） | C | hybrid | 600 | 26.8% | 72.0% | 0.0% | 0.2% | 1.0% | 0.0% | 0.0% | 97.8% | 3 |
| 比利时（BE） | A | rules | 600 | 89.8% | 4.3% | 0.0% | 4.0% | 1.7% | 0.2% | 0.0% | 98.7% | 2 |
| 比利时（BE） | A | crf | 600 | 87.2% | 7.7% | 0.0% | 4.7% | 0.5% | 0.0% | 0.0% | 99.0% | 1 |
| 比利时（BE） | A | hybrid | 600 | 90.3% | 4.7% | 0.0% | 3.8% | 1.0% | 0.2% | 0.0% | 99.2% | 3 |
| 卢森堡（LU） | A | rules | 600 | 90.2% | 4.0% | 0.0% | 4.2% | 1.7% | 0.0% | 0.0% | 98.2% | 2 |
| 卢森堡（LU） | A | crf | 600 | 90.0% | 3.8% | 0.0% | 4.3% | 1.8% | 0.0% | 0.0% | 98.0% | 1 |
| 卢森堡（LU） | A | hybrid | 600 | 90.8% | 3.5% | 0.0% | 4.2% | 1.5% | 0.0% | 0.0% | 98.5% | 3 |
| 瑞士（CH） | A | rules | 600 | 51.7% | 31.3% | 0.0% | 9.8% | 6.2% | 1.0% | 0.0% | 94.5% | 2 |
| 瑞士（CH） | A | crf | 600 | 51.8% | 32.7% | 0.0% | 9.2% | 5.0% | 1.3% | 0.0% | 97.3% | 1 |
| 瑞士（CH） | A | hybrid | 600 | 53.3% | 33.5% | 0.0% | 9.0% | 3.0% | 1.2% | 0.0% | 97.3% | 3 |
| 奥地利（AT） | A | rules | 600 | 82.8% | 8.0% | 0.0% | 7.3% | 1.8% | 0.0% | 0.0% | 97.7% | 1 |
| 奥地利（AT） | A | crf | 600 | 83.5% | 9.2% | 0.0% | 7.0% | 0.3% | 0.0% | 0.0% | 99.3% | 1 |
| 奥地利（AT） | A | hybrid | 600 | 83.5% | 9.2% | 0.0% | 7.0% | 0.3% | 0.0% | 0.0% | 99.3% | 1 |
| 意大利（IT） | A | rules | 600 | 81.2% | 9.0% | 0.0% | 3.2% | 6.5% | 0.2% | 0.0% | 92.8% | 2 |
| 意大利（IT） | A | crf | 600 | 81.5% | 9.5% | 0.0% | 2.7% | 6.2% | 0.2% | 0.0% | 93.7% | 1 |
| 意大利（IT） | A | hybrid | 600 | 81.5% | 9.5% | 0.0% | 2.7% | 6.2% | 0.2% | 0.0% | 93.8% | 3 |
| 西班牙（ES） | A | rules | 600 | 92.0% | 2.8% | 0.0% | 4.5% | 0.5% | 0.2% | 0.2% | 98.8% | 2 |
| 西班牙（ES） | A | crf | 600 | 91.7% | 3.8% | 0.0% | 4.3% | 0.2% | 0.0% | 0.0% | 99.5% | 1 |
| 西班牙（ES） | A | hybrid | 600 | 92.0% | 3.3% | 0.0% | 4.3% | 0.2% | 0.2% | 0.2% | 99.3% | 3 |
| 葡萄牙（PT） | A | rules | 600 | 82.0% | 4.7% | 0.0% | 6.7% | 5.3% | 1.3% | 0.3% | 96.3% | 2 |
| 葡萄牙（PT） | A | crf | 600 | 85.5% | 6.5% | 0.0% | 7.2% | 0.7% | 0.2% | 0.2% | 99.5% | 1 |
| 葡萄牙（PT） | A | hybrid | 600 | 86.5% | 6.0% | 0.0% | 4.7% | 1.5% | 1.3% | 0.3% | 99.2% | 4 |
| 丹麦（DK） | A | rules | 600 | 88.2% | 4.7% | 0.0% | 3.0% | 3.3% | 0.8% | 0.0% | 97.7% | 2 |
| 丹麦（DK） | A | crf | 600 | 88.2% | 7.2% | 0.0% | 4.3% | 0.3% | 0.0% | 0.0% | 99.3% | 1 |
| 丹麦（DK） | A | hybrid | 600 | 88.5% | 6.3% | 0.0% | 2.7% | 1.7% | 0.8% | 0.0% | 99.2% | 3 |
| 瑞典（SE） | C | rules | 600 | 31.7% | 64.5% | 0.0% | 1.7% | 2.0% | 0.2% | 0.0% | 93.3% | 1 |
| 瑞典（SE） | C | crf | 600 | 32.3% | 65.3% | 0.0% | 0.5% | 1.8% | 0.0% | 0.0% | 94.7% | 1 |
| 瑞典（SE） | C | hybrid | 600 | 32.8% | 65.3% | 0.0% | 0.0% | 1.8% | 0.0% | 0.0% | 94.8% | 2 |
| 挪威（NO） | A | rules | 600 | 88.8% | 5.7% | 0.0% | 4.3% | 1.2% | 0.0% | 0.0% | 99.3% | 1 |
| 挪威（NO） | A | crf | 600 | 89.5% | 5.8% | 0.0% | 4.5% | 0.2% | 0.0% | 0.0% | 100.0% | 1 |
| 挪威（NO） | A | hybrid | 600 | 89.8% | 5.8% | 0.0% | 4.3% | 0.0% | 0.0% | 0.0% | 100.0% | 2 |
| 芬兰（FI） | A | rules | 600 | 85.2% | 6.5% | 0.0% | 5.8% | 2.5% | 0.0% | 0.0% | 98.3% | 1 |
| 芬兰（FI） | A | crf | 600 | 87.0% | 7.5% | 0.0% | 5.5% | 0.0% | 0.0% | 0.0% | 100.0% | 1 |
| 芬兰（FI） | A | hybrid | 600 | 87.0% | 7.5% | 0.0% | 5.5% | 0.0% | 0.0% | 0.0% | 100.0% | 2 |
| 爱沙尼亚（EE） | A | rules | 600 | 81.0% | 3.3% | 0.0% | 10.5% | 3.0% | 2.2% | 0.5% | 91.2% | 1 |
| 爱沙尼亚（EE） | A | crf | 600 | 86.2% | 4.0% | 0.0% | 6.3% | 2.5% | 1.0% | 0.0% | 96.3% | 1 |
| 爱沙尼亚（EE） | A | hybrid | 600 | 85.8% | 4.5% | 0.0% | 5.2% | 2.7% | 1.8% | 0.2% | 96.2% | 2 |
| 拉脱维亚（LV） | A | rules | 600 | 84.7% | 5.3% | 0.0% | 5.0% | 3.2% | 1.8% | 0.0% | 98.5% | 1 |
| 拉脱维亚（LV） | A | crf | 600 | 77.0% | 10.0% | 0.0% | 4.2% | 7.2% | 1.7% | 0.8% | 93.3% | 1 |
| 拉脱维亚（LV） | A | hybrid | 600 | 85.5% | 5.5% | 0.0% | 5.0% | 1.7% | 2.3% | 0.3% | 99.0% | 2 |
| 立陶宛（LT） | A | rules | 600 | 90.3% | 3.3% | 0.0% | 3.2% | 2.5% | 0.7% | 0.3% | 98.2% | 1 |
| 立陶宛（LT） | A | crf | 600 | 91.0% | 4.3% | 0.0% | 3.5% | 1.2% | 0.0% | 0.0% | 99.2% | 1 |
| 立陶宛（LT） | A | hybrid | 600 | 90.5% | 4.5% | 0.0% | 3.2% | 1.5% | 0.3% | 0.0% | 99.2% | 2 |
| 波兰（PL） | A | rules | 600 | 85.2% | 6.3% | 0.0% | 5.7% | 2.8% | 0.0% | 0.0% | 97.5% | 2 |
| 波兰（PL） | A | crf | 600 | 86.7% | 6.8% | 0.0% | 5.2% | 1.3% | 0.0% | 0.0% | 98.8% | 1 |
| 波兰（PL） | A | hybrid | 600 | 87.2% | 6.3% | 0.0% | 5.2% | 1.3% | 0.0% | 0.0% | 98.8% | 3 |
| 捷克（CZ） | A | rules | 600 | 83.2% | 11.3% | 0.0% | 4.8% | 0.5% | 0.2% | 0.2% | 98.7% | 1 |
| 捷克（CZ） | A | crf | 600 | 87.8% | 7.3% | 0.0% | 4.7% | 0.2% | 0.0% | 0.0% | 99.7% | 1 |
| 捷克（CZ） | A | hybrid | 600 | 87.8% | 7.2% | 0.0% | 4.7% | 0.2% | 0.2% | 0.2% | 99.5% | 1 |
| 斯洛伐克（SK） | A | rules | 600 | 79.5% | 9.0% | 0.0% | 5.5% | 6.0% | 0.0% | 0.0% | 93.7% | 1 |
| 斯洛伐克（SK） | A | crf | 600 | 81.5% | 12.7% | 0.0% | 5.8% | 0.0% | 0.0% | 0.0% | 99.3% | 1 |
| 斯洛伐克（SK） | A | hybrid | 600 | 82.5% | 11.7% | 0.0% | 4.7% | 1.2% | 0.0% | 0.0% | 98.8% | 2 |
| 匈牙利（HU） | C | rules | 600 | 25.8% | 69.7% | 0.0% | 1.0% | 3.5% | 0.0% | 0.0% | 89.7% | 2 |
| 匈牙利（HU） | C | crf | 600 | 26.5% | 70.2% | 0.0% | 0.0% | 3.3% | 0.0% | 0.0% | 91.2% | 1 |
| 匈牙利（HU） | C | hybrid | 600 | 27.0% | 70.3% | 0.0% | 0.0% | 2.7% | 0.0% | 0.0% | 91.2% | 3 |
| 斯洛文尼亚（SI） | A | rules | 600 | 81.2% | 6.5% | 0.0% | 5.0% | 7.0% | 0.3% | 0.3% | 92.3% | 1 |
| 斯洛文尼亚（SI） | A | crf | 600 | 86.5% | 7.7% | 0.0% | 4.5% | 1.3% | 0.0% | 0.0% | 97.8% | 1 |
| 斯洛文尼亚（SI） | A | hybrid | 600 | 87.8% | 7.2% | 0.0% | 4.3% | 0.5% | 0.2% | 0.2% | 98.8% | 2 |
| 克罗地亚（HR） | A | rules | 600 | 86.5% | 4.5% | 0.0% | 5.2% | 3.7% | 0.2% | 0.0% | 95.8% | 1 |
| 克罗地亚（HR） | A | crf | 600 | 86.7% | 7.2% | 0.0% | 4.7% | 0.7% | 0.8% | 0.0% | 99.3% | 1 |
| 克罗地亚（HR） | A | hybrid | 600 | 89.2% | 5.3% | 0.0% | 4.7% | 0.7% | 0.2% | 0.0% | 99.3% | 2 |
| 保加利亚（BG） | C | rules | 600 | 28.8% | 62.7% | 0.0% | 4.5% | 3.7% | 0.3% | 0.0% | 89.3% | 1 |
| 保加利亚（BG） | C | crf | 600 | 30.8% | 65.8% | 0.0% | 1.2% | 2.0% | 0.2% | 0.0% | 93.3% | 1 |
| 保加利亚（BG） | C | hybrid | 600 | 30.7% | 65.3% | 0.0% | 1.0% | 2.7% | 0.3% | 0.0% | 92.3% | 2 |
| 新西兰（NZ） | A | rules | 600 | 86.5% | 4.7% | 0.0% | 6.8% | 1.5% | 0.5% | 0.0% | 98.0% | 1 |
| 新西兰（NZ） | A | crf | 600 | 87.2% | 5.3% | 0.0% | 5.7% | 1.3% | 0.5% | 0.0% | 99.2% | 1 |
| 新西兰（NZ） | A | hybrid | 600 | 87.2% | 5.2% | 0.0% | 5.7% | 1.5% | 0.5% | 0.0% | 99.2% | 2 |
| 日本（JP） | A | rules | 600 | 87.8% | 0.0% | 0.0% | 12.2% | 0.0% | 0.0% | 0.0% | 96.7% | 1 |
| 日本（JP） | A | crf | 600 | 88.3% | 2.5% | 0.0% | 9.2% | 0.0% | 0.0% | 0.0% | 96.0% | 1 |
| 日本（JP） | A | hybrid | 600 | 88.3% | 2.5% | 0.0% | 9.2% | 0.0% | 0.0% | 0.0% | 97.7% | 2 |
| 印度（IN） | C | rules | 600 | 34.2% | 54.3% | 0.0% | 3.8% | 7.7% | 0.0% | 0.0% | 83.5% | 3 |
| 印度（IN） | C | crf | 600 | 39.0% | 56.0% | 0.0% | 0.0% | 4.8% | 0.2% | 0.0% | 89.8% | 1 |
| 印度（IN） | C | hybrid | 600 | 39.7% | 54.7% | 0.0% | 0.0% | 5.5% | 0.2% | 0.0% | 89.0% | 4 |

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

**德国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Kastanienallee 55, Berlin, 12627 | CONFIRM | PREMISE | Nossener Straße 55, 12627 Hellersdorf |
| Hauptbahnhof 1, Berlin, 10557 | CONFIRM | PREMISE | Bartningallee 1, 10557 Hansaviertel |
| Mierendorffplatz 12, Berlin, 10589 | CONFIRM | PREMISE | Bonhoefferufer 12, 10589 Charlottenburg |
| Reischstrasse 13, Berlin, 14052 | CONFIRM | PREMISE | Reichsstraße 13, 14052 Westend |

**德国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Am Zwirngraben 6-7, Berlin, 10178 | FIX | ROUTE | Am Zwirngraben 6-7, 10178 |
| Brommystraße 1, Berlin, 10997 | FIX | ROUTE | Brommystraße 1, 10997 |
| Heidestr. 65-68, Berlin, 10557 | FIX | ROUTE | Heidestraße 65-68, 10557 |
| Karl-Kunger-Str., Berlin, 12435 | FIX | ROUTE | Karl-Kunger-Straße, 12435 |

**德国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Turmstr. 21/Haus M, Berlin, 10559 | ACCEPT | PREMISE | Turmstraße 21, 10559 Moabit |
| Unitb Consulting, Brunnenstraße 156, Berlin, 10115 | ACCEPT | PREMISE | Brunnenstraße 156, 10115 Mitte |
| Spenerstraße 15, Berlin, 10557 | ACCEPT | PREMISE | Spenerstraße 15, 10557 Moabit |
| Hardenbergstraße 9a, Berlin, 10623 | ACCEPT | PREMISE | Hardenbergstraße 9 A, 10623 Charlottenburg |

**法国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 10 Rue de Sévigné, Paris, 75004 | CONFIRM | PREMISE_PROXIMITY | 10 Rue de Sévigné, 92120 Montrouge |
| 2 Place Charles de Gaulle, Paris, 75017 | CONFIRM | PREMISE_PROXIMITY | 2 Place Charles de Gaulle, 92400 Courbevoie |
| Forum des Halles, 101 Porte Berger, Rue Berger Level-3, Paris, 75001 | CONFIRM | PREMISE_PROXIMITY | Level 3, 101 Allée du Forum, 92100 Boulogne-Billancourt |
| 1 Pl. de la Prte de Versailles, Paris, 75015 | CONFIRM | PREMISE_PROXIMITY | 1 Avenue de Versailles, 75016 Paris 16e Arrondissement |

**法国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 60 Rue François 1er, Paris, 75008 | FIX | ROUTE | 60 Rue François 1er, 75008 |
| Rue Viala, Paris, 75015 | FIX | ROUTE | Rue Viala, 75015 |
| Esplanade La Défense, Courbevoie, 92400 | FIX | ROUTE | la Défense, 92400 Courbevoie |
| Av. Kléber, Paris, 75016 | FIX | ROUTE | Avenue Kléber, 75016 |

**法国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Rives de Seine Habitat, 6 Rue Jacques Mazaud, Levallois-Perret, 92300 | ACCEPT | PREMISE | 6 Rue Jacques Mazaud, 92300 Levallois-Perret |
| 6 place de Belgique, Courbevoie, 92400 | ACCEPT | PREMISE | 6 Place de Belgique, 92400 Courbevoie |
| 6 Rue Rataud, Paris, 75005 | ACCEPT | PREMISE | 6 Rue Rataud, 75005 Paris 5e Arrondissement |
| Les Films du Cap, 20 Rue Oberkampf, Paris, 75011 | ACCEPT | PREMISE | 20 Rue Oberkampf, 75011 Paris 11e Arrondissement |

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
| V&d Buitenplein 101, Amstelveen, 1181 ZE | ACCEPT | PREMISE | Buitenplein 101, 1181 ZE Amstelveen |

**荷兰 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Wingerdweg, Amsterdam | CONFIRM | ROUTE | Wingerdweg |
| Evert V/D Beekstraat 202, Luchthaven Schiphol, 1118 CP | CONFIRM | PREMISE | Evert van de Beekstraat 202, 1118 CP Schiphol |
| Professor Tulpstraat 18, Amsterdam, 1018 HA | CONFIRM | PREMISE_PROXIMITY | Tulpstraat 18, 1171 MT Badhoevedorp |
| Sporthal Fanny Blankers Koen/FBK, Marathonlaan 12, Almere-Stad, 1318 EE | CONFIRM | PREMISE_PROXIMITY | Marathonlaan 12, 1183 VC Amstelveen |

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

**加拿大 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Sherbourne St N, Toronto, M4W 2T2 | FIX | ROUTE | Sherbourne Street North, ON M4W 2T2 |
| 17 Gould St, Toronto, M5B 2L5 | FIX | ROUTE | 17 Gould Street, ON M5B 2L5 |
| 70 Glen Scarlett Rd, Toronto, M6N 1P4 | FIX | ROUTE | 70 Glen Scarlett Road, ON M6N 1P4 |
| Entrance from inner parking lot, 2100 Ellesmere Rd Unit 109, Ground floor, Toronto, M1H 3B | FIX | ROUTE | Unit 109, Ellesmere Road, ON M1H 3B7 |

**加拿大 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 1500 – 5255 Yonge Street, Toronto, M2N 6P4 | CONFIRM | PREMISE | 1500 Yonge Street, TORONTO ON M4T 1Z6 |
| 350 Victoria St, Toronto, M5B 2K3 | CONFIRM | ROUTE | 350 Victoria Street, ON M5B 2K3 |
| 419, King Street West, Toronto, L1J 2K5 | CONFIRM | PREMISE_PROXIMITY | 419 King Street West, TORONTO ON M5V 1K1 |
| 51 Wolseley Street, Suite 105, Toronto, M5T 1A5 | CONFIRM | PREMISE_PROXIMITY | Suite 105, 51 Wolseley Street, TORONTO ON M5T 1A4 |

**加拿大 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 1-168 Oakdale road, Toronto, M3N 2S5 | ACCEPT | PREMISE | 168 Oakdale Road, NORTH YORK ON M3N 2S5 |
| 3401 Dufferin St, Unit 305A, Toronto, M6A 2T9 | ACCEPT | PREMISE | Unit 305A, 3401 Dufferin Street, NORTH YORK ON M6A 2T9 |
| 2869 Bloor St W #126, Toronto, M8X 1B3 | ACCEPT | PREMISE | #126, 2869 Bloor Street West, ETOBICOKE ON M8X 1B3 |
| 1800 Sheppard Ave E, Toronto, M2J 5A7 | CONFIRM_ADD_SUBPREMISES | PREMISE | 1800 Sheppard Avenue East, NORTH YORK ON M2J 5A7 |

**墨西哥 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Parque arboledas, Enrique Pestalozzi, Benito Juárez, 03100 | CONFIRM | ROUTE | Avenida de Parque, Benito Juárez, 03100 |
| Zapotecas mz 30 lt 12, Calle Ajusco, Coyoacán, 04300 | CONFIRM | PREMISE_PROXIMITY | Zapotecas 12, Coyoacán, 04300 |
| Avenida Central 8, Gustavo A Madero, 07570 | CONFIRM | PREMISE | Avenida Central 8, Nezahualcóyotl, 57150 |
| Cecilio Robelo 20-Und 3, edificio 2 Loc.1630, Venustiano Carranza, 15900 | CONFIRM | PREMISE_PROXIMITY | Loc 1630, Calle Cecilio Robelo 20, Venustiano Carranza, 15900 |

**墨西哥 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Chihuahua 222, Ciudad de México, 06700 | FIX | ROUTE | Chihuahua 222, 06700 |
| Calz. de Las Armas 1058, Azcapotzalco, 02710 | FIX | ROUTE | Calzada de las Armas 1058, Azcapotzalco, 02710 |
| Avenida Canal de Miramontes 152, Tlalpan, 14300 | FIX | ROUTE | Avenida Canal de Miramontes 152, 14300 |
| Cda. Francisco Moreno 129, Gustavo A Madero, 07050 | FIX | ROUTE | Cerrada Francisco Moreno 129, 07050 |

**墨西哥 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Santa María La Ribera 24, Cuauhtémoc, 06400 | ACCEPT | PREMISE | Calle Santa María La Ribera 24, Cuauhtémoc, 06400 |
| Avenida Isabel La Católica 16, Benito Juárez, 03410 | ACCEPT | PREMISE | Isabel la Católica, Calle Isabel La Católica 16, Benito Juárez, 03410 |
| Oriente 253 109, Iztacalco, 08500 | ACCEPT | PREMISE | Calle Oriente 253 109, Iztacalco, 08500 |
| Esq. con, Gregorio Sosa, Arroyo Seco LT 5, Iztapalapa, 09760 | ACCEPT | PREMISE | Calle Gregorio Sosa 5, Iztapalapa, 09760 |

**波多黎各 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 200 Avenida San Marcos, Carolina, 00982 | ACCEPT | ROUTE | 200 Avenida San Marcos, 00982 |
| 1190 Avenida Americo Miranda, San Juan, 00921 | ACCEPT | ROUTE | 1190 Avenida Américo Miranda, 00921 |
| Centro de Estudiantes, 54 Av. Universidad, San Juan, 00925 | ACCEPT | ROUTE | 54 Avenida Universidad, 00925 |
| Bo. Monacillos 150 Ave Americo Miranda, San Juan, 00936 | ACCEPT | ROUTE | 150 Avenida Américo Miranda, 00936 |

**波多黎各 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 1045 Ashford Ave, San Juan, 00907 | CONFIRM | ROUTE | 1045 Calle Ashford, 00907 |
| 803 Av. Roberto Sánchez Vilella, San Juan, 00924 | CONFIRM | ROUTE | 803 Autopista Roberto Sánchez Vilella, 00924 |
| 103 Avenida José de Diego, San Juan, 00911 | CONFIRM | ROUTE | 103 Avenida José de Diego, 00911 |
| 4 Calle 3, Toa Baja, 00949 | CONFIRM | ROUTE | 4 Calle 3, 00949 |

**波多黎各 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 97 PR-2, Guaynabo, 00966 | FIX | LOCALITY |  |
| Puerto rico, San Juan, 00924 | FIX | LOCALITY |  |
| Road Pr 167 Km 18.8, Bayamón, 00956 | FIX | LOCALITY |  |
| Road B Lot 21 Luchetti Industrial Park, Bayamón, 00961 | FIX | LOCALITY |  |

**巴西 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| AVENIDA ELISEU DE ALMEIDA, São Paulo, 05145-907 | FIX | ROUTE | Avenida Eliseu de Almeida, 05145-907 |
| rua da consolação, São Paulo, 459118191 | FIX | ROUTE | Rua da Consolação |
| R. Santa Ifigênia, 261, São Paulo, 01207-001 | FIX | ROUTE | Rua Santa Ifigênia 261, 01207-001 |
| Rua Vergueiro, 2177, São Paulo, 04101-000 | FIX | ROUTE | Rua Vergueiro 2177, 04101-000 |

**巴西 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Avenida José do Patrocínio, 198, São Paulo, 96415-500 | CONFIRM | PREMISE_PROXIMITY | Rua José do Patrocínio 198, 04108-000 São Paulo |
| Modular II, Avenida Marginal Projetada, 1810, Barueri, 06463-400 | CONFIRM | PREMISE_PROXIMITY | Modular TI, 1810, 06463-400 |
| Rua Conselheiro Crispiniano, 72, São Paulo, 01037-001 | CONFIRM | PREMISE | Rua Conselheiro Crispiniano 72, 01037-000 São Paulo |
| Condomínio Edifício Umuarama - R. Piracuama, 428, São Paulo, 05017-040 | CONFIRM | PREMISE_PROXIMITY | Condomínio Edificio Umuarama, 428, 05017-040 |

**巴西 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Rua Domingos Rodrigues, 77, São Paulo, 05075-000 | ACCEPT | PREMISE | Rua Domingos Rodrigues 77, 05075-000 São Paulo |
| Rua Dr. Luiz Migliano, 1986 - 1106, São Paulo, 05711-001 | ACCEPT | PREMISE | Rua Doutor Luiz Migliano 1986, 05711-001 São Paulo |
| Rua Doutor Paulo Vieira, 566, São Paulo, 01257-000 | ACCEPT | PREMISE | Rua Doutor Paulo Vieira 566, 01257-000 São Paulo |
| Rua Barão de Jaceguai, 684, São Paulo, 04606-000 | ACCEPT | PREMISE | Rua Barão Jaceguai 684, 04606-000 São Paulo |

**阿根廷 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Godoy Cruz 2880, Ciudad de Buenos Aires, C1425FQN | FIX | LOCALITY |  |
| J P Tamborini 3638, Buenos Aires, 1430 | FIX | OTHER |  |
| Sarmiento 1315, Ciudad de Buenos Aires, C1041 | FIX | LOCALITY |  |
| Luján, 1294 Ciudad de Buenos Aires, Argentina, Ciudad de Buenos Aires, 1294 | FIX | OTHER |  |

**阿根廷 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| PEDRO GOYENA 1486 CABALLITO, Buenos Aires, 1406 | CONFIRM | ROUTE | Pedro Goyena 1486 |
| Rodriguez Peña 1487, Ciudad de Buenos Aires, 1640 | CONFIRM | ROUTE | Rodríguez Peña 1487 |
| Manuel castro 4149, Ciudad de Buenos Aires, 1832 | CONFIRM | ROUTE | Manuel Castro 4149 |
| Alberti 140, Buenos Aires | CONFIRM | ROUTE | Alberti 140 |

**阿根廷 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Av. Cerviño 3126, Ciudad de Buenos Aires, C1425AAX | ACCEPT | ROUTE | Avenida Cerviño 3126, 1425 |
| Avenida Pres. Tte. Gral. Juan Domingo Perón 3700, Haedo, B1706 | ACCEPT | ROUTE | Teniente General Juan Domingo Perón 3700, 1706 |
| Boyacá 601, Ciudad de Buenos Aires, C1406BHK | ACCEPT | ROUTE | Boyacá 601, 1406 |
| Av. Olazábal 1483, Ciudad de Buenos Aires, C1428 | ACCEPT | ROUTE | Avenida Olazábal 1483, 1428 |

**智利 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Avenida José Miguel Carrera 8193, La Cisterna | CONFIRM | ROUTE | Pasaje La Cisterna 8193 |
| Av. Las Torres 561, Pudahuel, 9190847 | CONFIRM | PREMISE_PROXIMITY | Avenida Las Torres 561, CERRILLOS |
| Bellavista 0384, Providencia, 7520335 | CONFIRM | PREMISE_PROXIMITY | Bellavista 0384, Providencia |
| Santiago, Estación Central, 9210007 | CONFIRM | ROUTE | Autopista Central, 9210007 |

**智利 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Calle Bandera 883, Santiago, 8320000 | ACCEPT | PREMISE | Bandera 883, SANTIAGO |
| Calle Cerro Colorado 4700, Las Condes, 7550000 | ACCEPT | PREMISE | Cerro Colorado 4700, LAS CONDES |
| Sgto. Aldea 131, El Bosque, 8030027 | ACCEPT | PREMISE | Avenida El Bosque 131, PROVIDENCIA |
| "Avenida Suecia 0120, Metro Los Leones", Providencia | ACCEPT | PREMISE | Avenida Suecia 0120, Providencia |

**智利 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Aldaia, Quinta Normal, 46960 | FIX | LOCALITY |  |
| Av. Libertador Bernardo O'Higgins, Santiago | FIX | ROUTE | Avenida Libertador Bernardo O'Higgins |
| San Enrique 041, Quilicura, 8730058 | FIX | ROUTE | San Enrique 041, Quilicura, 8730058 |
| Avenida Providencia, Providencia, 7500000 | FIX | ROUTE | Avenida Providencia, Providencia, 7500000 |

**哥伦比亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Carrera 99-52, Bogotá, D.C., 111041 | FIX | LOCALITY |  |
| Carrera 53-05, Bogotá, D.C., 110611 | FIX | LOCALITY |  |
| Cl. 59c Sur #no 87g 42, Bogotá, D.C., 110711 | FIX | ROUTE | Calle 59C Sur # 87G-42, 110711 |
| Calle 18 Sur 16-9, Bogotá, D.C., 111511 | FIX | ROUTE | Calle 18 Sur # 16-9, 111511 |

**哥伦比亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Autopista Sur 51D-83, Bogotá, D.C., 110611 | CONFIRM | ROUTE | Autopista Sur # 51D-83, 110611 |
| Avenida Ciudad de Cali 6-09, Bogotá, D.C., 110811 | CONFIRM | ROUTE | Avenida Ciudad de Cali # 6-09, 110811 |
| Ak. 20 #8781, Bogotá, D.C., 111411 | CONFIRM | ROUTE | AK 20 # 8781, 111411 |
| Cra. 14, Bogotá, D.C., 414020 | CONFIRM | ROUTE | Carrera 14, 414020 |

**哥伦比亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Carrera 9 2-60, Bogotá, D.C., 110321 | ACCEPT | PREMISE | Carrera 9 # 2-60, Bogotá Distrito Capital |
| Carrera 53 104B-66, Bogotá, D.C., 111111 | ACCEPT | PREMISE | Carrera 53 # 104B-66, Bogotá Distrito Capital |
| Calle 127 BIS 19-25, Bogotá, D.C., 110121 | ACCEPT | PREMISE | Calle 127 Bis # 19-25, Bogotá Distrito Capital |
| Cra 27 #No. 14 - 47, Bogotá, D.C., 111311 | ACCEPT | PREMISE | Carrera 27 # 14-47, Bogotá Distrito Capital |

**英国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Shepherd's Bush Grn, London, W12 8PP | CONFIRM | ROUTE | Shepherd's Bush Road, Shepherd's Bush, W12 8PP |
| 88-90 Kings Street, Hammersmith, W6 0QW | CONFIRM | ROUTE | 88-90 Kings Road, W6 0QW |
| 142 Bentworth Rd, London W12 7AH, London, W12 7AH | CONFIRM | ROUTE | 142 Bentworth Road, W12 7AH |
| 130 High Street, London, SW11 3JR | CONFIRM | ROUTE | 130 High Street, SW11 3JR |

**英国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 2-я Тверская-Ямская улица, London | FIX | OTHER |  |
| The Prow 4Th Floor, 1 Wylder Road, London, W1B 5AP | FIX | OTHER |  |
| The Studio Buildings 2nd Floor 21 Eversham Street, London, W11 4AJ | FIX | OTHER |  |
| Worldwide, London | FIX | OTHER |  |

**英国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 27 Lower Belgrave St, London Sw1W 0Ls, United Kingdom, London, SW1W 0LS | ACCEPT | ROUTE | 27 Lower Belgrave Street, SW1W 0LS |
| Office No. 1032, 14 Grays Inn Rd, London, WC1X 8HN | ACCEPT | ROUTE | 14 Grays Inn Road, WC1X 8HN |
| 7 Lower Grove Road, Richmond, TW10 6HP | ACCEPT | ROUTE | 7 Lower Grove Road, TW10 6HP |
| 3Rd Floor, 86-90 Paul Street, London, EC2A 4NE | ACCEPT | ROUTE | 3Rd Floor, 86-90 Paul Street, EC2A 4NE |

**爱尔兰 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Carriglea Gardens, 8 Kill Avenue, Dun Laoghaire, A96 A593 | ACCEPT | ROUTE | 8 Carriglea Gardens, Dunleary, A96 A593 |
| 4 Donnybrook Rd, Dublin, D04 HK50 | ACCEPT | ROUTE | 4 Donnybrook Road, D04 HK50 |
| 6a The Meadows, Dublin, D05 E489 | ACCEPT | ROUTE | 6A The Meadows, D05 E489 |
| 25 Harcourt Street, Dublin, D02H364 | ACCEPT | ROUTE | 25 Harcourt Street, D02 H364 |

**爱尔兰 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Greenfield Road, Dublin | CONFIRM | ROUTE | Greenfield Road |
| Belgrove Park, Dublin, D20 DR77 | CONFIRM | ROUTE | Belgrove Park, D20 DR77 |
| St. James's Hospital, Dublin, Dublin 8 | CONFIRM | ROUTE | 8 St. James's Hospital |
| 27 Frederick St S, Dublin, D02 EP03 | CONFIRM | ROUTE | 27 Frederick Court, D02 EP03 |

**爱尔兰 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| grange x, Dublin | FIX | LOCALITY |  |
| Wayfinder House, Dublin, D13 H6E5 | FIX | OTHER |  |
| 5 Camden Villas, Dublin, 2 | FIX | OTHER |  |
| Foxrock Avenue, Dublin, 18 | FIX | OTHER |  |

**比利时 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Ninoofsesteenweg, Anderlecht, 1070 | FIX | ROUTE | Chaussée de Ninove - Ninoofsesteenweg, 1070 Anderlecht |
| Herendal /  Val des Seigneurs, St-Pieters-Woluwe-St-Pierre, 1050 | FIX | ROUTE | Val des Seigneurs - Herendal, 1050 Woluwe-Saint-Pierre - Sint-Pieters- |
| Koningin Elisabethlaan 11, Dilbeek, 1700 | FIX | ROUTE | Koningin Elisabethlaan 11, 1700 Dilbeek |
| Steenweg op Zaventem, Kraainem, 1950 | FIX | ROUTE | Steenweg op Zaventem - Chaussée de Zaventem, 1950 Kraainem |

**比利时 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Rue Saint-Lambert 107, Woluwé-Saint-Lambert, 1200 | CONFIRM_ADD_SUBPREMISES | PREMISE | Rue Saint-Lambert - Sint-Lambertusstraat 107, 1200 Woluwe-Saint-Lamber |
| Pleinlaan 2, Elsene, 1050 | CONFIRM_ADD_SUBPREMISES | PREMISE | Boulevard de la Plaine - Pleinlaan 2, 1050 Ixelles - Elsene |
| Avenue Franklin Roosevelt 50, CP 135, Bruxelles, 1050 | CONFIRM_ADD_SUBPREMISES | PREMISE | Avenue Franklin Roosevelt - Franklin Rooseveltlaan 50, 1050 Bruxelles |
| Avenue Louise 304, Brussels, 1050 | CONFIRM_ADD_SUBPREMISES | PREMISE | Avenue Louise - Louizalaan 304, 1050 Bruxelles |

**比利时 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Turcksinstraat 25, Machelen, 1830 | CONFIRM | PREMISE | Steenweg Buda 25, 1830 Machelen |
| Chau. de Gand 272, Molenbeek-Saint-Jean, 1080 | CONFIRM | PREMISE | Boulevard Louis Mettewie - Louis Mettewielaan 272, 1080 Molenbeek-Sain |
| Mail 9, Ganshoren, 1083 | CONFIRM | PREMISE | Venelle Mozart - Mozartsteeg 9, 1083 Ganshoren |
| Koninklijke Parklaan, Bruxelles, 1020 | CONFIRM | ROUTE | Parklaan - Avenue du Parc, 1020 |

**卢森堡 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 65 zone industrielle Gadderscheier, Differdange, 4984 | FIX | LOCALITY |  |
| Rue de la Cimenterie, Luxembourg, 1337 | FIX | ROUTE | Rue de la Cimenterie, L-1337 |
| 35 Rue Friedrich Wilhelm Raiffeisen, Luxembourg, 2411 | FIX | ROUTE | 35 Boulevard Friedrich Wilhelm Raiffeisen, L-2411 |
| Rue Daniel Grün, Luxembourg, L5315 | FIX | ROUTE | Rue Daniel Grün, L-5315 |

**卢森堡 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 11-13 Rte de Mondorf, Frisange, 3337 | CONFIRM | PREMISE | 11 Rue de Mondorf, L-2159 Luxembourg |
| 85 Route d'Arlon, L-8210 Mamer, Luxembourg, Mamer, 8210 | CONFIRM | PREMISE | 85 Route d'Arlon, L-1140 Mamer |
| 140 Rte d'Esch, Luxembourg, 1471 | CONFIRM | PREMISE | 140 Rue d'Esch, L-3922 Mondercange |
| 243 Rte d'Arlon, Luxembourg, 1150 | CONFIRM | ROUTE | 243 Chemin d'Arlon, L-1150 |

**卢森堡 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 16 Rue du Marché-aux-Herbes, Luxembourg, 1728 | ACCEPT | PREMISE | 16 Rue du Marché-aux-Herbes, L-1728 Luxembourg |
| 96 Rue Emile Mayrisch, Esch-sur-Alzette, 4240 | ACCEPT | PREMISE | 96 Rue Émile Mayrisch, L-4240 Esch-sur-Alzette |
| 97 Avenue Pasteur, Luxembourg, 2311 | ACCEPT | PREMISE | 97 Avenue Pasteur, L-2311 Luxembourg |
| 70 Zone Industrielle um Monkeler, Mondercange, 4149 | ACCEPT | PREMISE | 70 Zone Industrielle Um Monkeler, L-4149 Mondercange |

**瑞士 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Paradeplatz 8, Zürich, 8001 | CONFIRM | PREMISE | Schweizergasse 8, 8001 Zürich |
| Bahnhofplatz 4, Zürich, 8001 | CONFIRM | PREMISE | Gessnerallee 4, 8001 Zürich |
| Illgenstrasse 4, Zürich, 8032 | CONFIRM | PREMISE | Ilgenstrasse 4, 8032 Zürich |
| Bernstrasse 8 3360 Herzogenbuchsee, zurich, 8038 | CONFIRM | PREMISE_PROXIMITY | Bernstrasse 8, 8952 Schlieren |

**瑞士 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Bahnhofspassage 1, ShopVille Dosenbach + SPORT, Zürich, 8001 | FIX | ROUTE | Bahnhofpassage 1, 8001 |
| Leonhardstrasse, Zürich, 8092 | FIX | ROUTE | Leonhardstrasse, 8092 |
| Weinbergstrasse, Zurich, 8006 | FIX | ROUTE | Weinbergstrasse, 8006 |
| Steinkluppenweg, Zürich, 8057 | FIX | ROUTE | Steinkluppenweg, 8057 |

**瑞士 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Langstrasse 136, Zürich, 8004 | ACCEPT | PREMISE | Langstrasse 136, 8004 Zürich |
| Hönggerstrasse 120, Zürich, 8037 | ACCEPT | PREMISE | Hönggerstrasse 120, 8037 Zürich |
| Dorfstrasse 6, Dietlikon, 8305 | ACCEPT | PREMISE | Dorfstrasse 6, 8305 Dietlikon |
| Bahnhofstr. 79, Zurich, 8001 | ACCEPT | PREMISE | Bahnhofstrasse 79, 8001 Zürich |

**奥地利 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Gentzgasse 122, Wien, 1180 | ACCEPT | PREMISE | Gentzgasse 122, 1180 Wien |
| Billrothstraße 14/1, Wien, 1190 | ACCEPT | PREMISE | Billrothstraße 1, 1190 Wien |
| Wiener Straße 176-196, Langenzersdorf, 2103 | ACCEPT | PREMISE | Wiener Straße 176 - 196, 2103 Langenzersdorf |
| Albrechtsbergergasse 29/2.1, Wien, 1120 | ACCEPT | PREMISE | Albrechtsbergergasse 2, 1120 Wien |

**奥地利 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Naschmarkt 1, Wien, 1060 | CONFIRM | PREMISE | Capistrangasse 1, 1060 Wien |
| Freyung 4, Wien, 1010 | CONFIRM | PREMISE | Rathausstraße 4, 1010 Wien |
| Lichtensteinstrasse 87-89, Wien, 1090 | CONFIRM | PREMISE | Liechtensteinstraße 87, 1090 Wien |
| Landstr.r Hauptstr. 1b/Top 202, Vienna | CONFIRM | PREMISE | Hauptstraße 202, 3400 Weidling |

**奥地利 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Braunhubergasse 21/6/G2, Wien, 1110 | FIX | ROUTE | Braunhubergasse, 1110 |
| Bauernmarkt, Wien, 1010 | FIX | ROUTE | Bauernmarkt, 1010 |
| Billrothstraße 61/R1, Wien, 1190 | FIX | ROUTE | Billrothstraße, 1190 |
| Maurer Lange Gasse K 345, Wien, 1230 | FIX | ROUTE | Maurer Lange Gasse 345, 1230 |

**意大利 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Via Ampere, Milano | CONFIRM | ROUTE | Via Campestre |
| Via Pisa, 28, Sesto San Giovanni, 20099 | CONFIRM | PREMISE_PROXIMITY | Via Pisa 28, Sesto San Giovanni |
| PIAZZA CAMILLO BENSO DI CAVOUR 1, MILANO, 20121 | CONFIRM | PREMISE_PROXIMITY | VIA CAMILLO BENSO CAVOUR 1, Bresso |
| VIALE VINCENZO LANCETTI 1, MILAN, 20158 | CONFIRM | PREMISE_PROXIMITY | Viale Vincenzo Lancetti 1, Milano |

**意大利 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Via Rossini 6/8, Milano | FIX | OTHER |  |
| VIA UMBERTO PACE 130, SESTO SAN GIOVANNI, 20099 | FIX | ROUTE | VIA UMBERTO PACE 130, 20099 |
| Via Amedeo D'Aosta, 8, Milano, 20157 | FIX | ROUTE | Via Amedeo d'Aosta 8, 20157 |
| VIA NINO BIXIO, MILANO, 20129 | FIX | ROUTE | Via Nino Bixio, 20129 |

**意大利 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| VIA LEONARDO DA VINCI 17, CORSICO, 20094 | ACCEPT | PREMISE | Via Leonardo da Vinci 17, Corsico |
| Via Generale Antonio Cantore, 145, Sesto San Giovanni, 20099 | ACCEPT | PREMISE | VIA GENERALE ANTONIO CANTORE 145, Sesto San Giovanni |
| VIA DELLA SPIGA 52, MILANO, 20121 | ACCEPT | PREMISE | Via della Spiga 52, Milano |
| VIALE EUROPA 49, CUSAGO, 20090 | ACCEPT | PREMISE | Viale Europa 49, Cusago |

**西班牙 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| C/ Serrano, Madrid, 28006 | FIX | ROUTE | Calle de Serrano, 28006 |
| C. del Valle de Tobalina, 42, Nave 12, Madrid, 28021 | FIX | ROUTE | Calle del Valle de Tobalina 42, 28021 |
| Puente Cultural, 12, San Sebastián de los Reyes, 28702 | FIX | ROUTE | Calle de San Sebastián 12, 28702 |
| C. de Caños Viejos, 2, Madrid, 28005 | FIX | ROUTE | Calle de los Caños Viejos 2, 28005 |

**西班牙 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Calle de Preciados, 3, Madrid, 28013 | ACCEPT | PREMISE | Calle Preciados 3, 28013 Madrid |
| C/ Preciados, 3, Madrid, 28013 | ACCEPT | PREMISE | Calle Preciados 3, 28013 Madrid |
| Vía de los Poblados 3 Parque Empresarial Cristalia, Edificio 4B, Madrid, 28033 | ACCEPT | PREMISE | Calle Vía de los Poblados 3, 28033 Madrid |
| Calle Velázquez, 1, Madrid, 28001 | ACCEPT | PREMISE | Calle de Velázquez 1, 28001 Madrid |

**西班牙 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Capitán Muro Durán, 9, Leganés, 28911 | CONFIRM | PREMISE | FERROCARRIL MADRID-VALENCIA ALCANTARA 9, 28911 Leganés |
| Isabel Colbrand, 10 Edificio Alpha III. Nave 87 - Acceso 4, Madrid, 28050 | CONFIRM | PREMISE | Carretera de Fuencarral a Alcobendas 10, 28050 Madrid |
| Calle Monasterio de Arlanza, 13, Madrid, 28034 | CONFIRM | PREMISE | Calle Monasterio de Arlanza 13, 28049 Madrid |
| Alberto Alcocer, 48, Local 50, Madrid, 28016 | CONFIRM | PREMISE | Local 50, Calle de Triana 48, 28016 Madrid |

**葡萄牙 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| C. C. Colombo, Lj A003, Benfica, 1500-392 | FIX | ROUTE | Lj A003, Calçada do Combro, 1500-392 |
| de Abastecimento, Av. do Forte, 7-7APosto, B.P, Oeiras, 2790-074 | FIX | ROUTE | Avenida do Forte 7-7, 2790-074 |
| R. Vítor Cordon n5, Lisboa, 1200-482 | FIX | ROUTE | Rua Vítor Cordon, 1200-482 |
| Praça do Império, Lisboa, 1400-206 | FIX | ROUTE | Praça do Império, 1400-206 |

**葡萄牙 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Av. da Liberdade 36 B, Lisboa, 1250-145 | CONFIRM | PREMISE_PROXIMITY | Avenida da Liberdade 36, 2650-203 AMADORA |
| Centro Vasco da Gama, Av. Dom João II 1 2033/35, Lisboa, 1990-094 | CONFIRM | PREMISE | Rua Vasco da Gama 1, 1885-080 MOSCAVIDE |
| Rua da Conceição 2, Lisboa, 1100-404 | CONFIRM | PREMISE | Rua da Conceição 2, 2610-234 AMADORA |
| Av. Mar. Gomes da Costa n.º 35, Lisboa, 1800-255 | CONFIRM | PREMISE | R GOMES 35, 2720-319 AMADORA |

**葡萄牙 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Rua Alberto de Sousa 5, Lisboa, 1600-002 | CONFIRM_ADD_SUBPREMISES | PREMISE | Rua Alberto de Sousa 5, 1600-002 LISBOA |
| Rua da Cruz a Alcântara 2, Lisboa, 1300-159 | CONFIRM_ADD_SUBPREMISES | PREMISE | Rua da Cruz a Alcântara 2, 1300-159 LISBOA |
| Avenida Álvares Cabral 62, Lisboa, 1250-018 | CONFIRM_ADD_SUBPREMISES | PREMISE | Avenida Álvares Cabral 62, 1250-018 LISBOA |
| Avenida de Sidónio Pais 16, Lisboa, 1050-215 | CONFIRM_ADD_SUBPREMISES | PREMISE | Avenida Sidónio Pais 16, 1050-215 LISBOA |

**丹麦 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| C.M. LARSENS ALLÉ, COPENHAGEN, 2770 | FIX | ROUTE | C.M. Larsens Alle, 2770 |
| Egegårdsvej 75, Rødovre, 2610 | FIX | ROUTE | Egegårdsvej 75, 2610 Rødovre |
| Nørrebrogade, København | FIX | ROUTE | Nørrebrogade |
| P. Knudsens Gade, København SV, 2450 | FIX | ROUTE | P. Knudsens Gade, 2450 |

**丹麦 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| STRANDGADE 10D, KØBENHAVN, 1401 | ACCEPT | PREMISE | Strandgade 10D, 1401 København K |
| VIGERSLEVVEJ 54B, COPENHAGEN, 2500 | CONFIRM_ADD_SUBPREMISES | PREMISE | Vigerslevvej 54B, 2500 Valby |
| Frederiksborgvej 125, København NV, 2400 | ACCEPT | PREMISE | Frederiksborgvej 125, 2400 København NV |
| VESTERBROGADE 15A, KØBENHAVN, 1620 | CONFIRM_ADD_SUBPREMISES | PREMISE | Vesterbrogade 15A, 1620 København V |

**丹麦 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| PRAGS BOUL 51, KØBENHAVN, 2300 | CONFIRM | PREMISE | Ved Slusen 51, 2300 København S |
| Skole Allé 66, København | CONFIRM | PREMISE | Højskole Allé 66, 2770 Kastrup |
| HVIDOVRE STRANDVEJ 31, HVIDOVRE, 2650 | CONFIRM | PREMISE_PROXIMITY | Hvidovre Strandvej 31, 2650 Hvidovre |
| ÅBOUL 27, FREDERIKSBERG, 1960 | CONFIRM | PREMISE | Frederiksberggade 27, 1459 København K |

**瑞典 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Bryggerivägen 16, Huvudsta, 168 67 | ACCEPT | ROUTE | Bryggerivägen 16, 168 67 Huvudsta |
| Hagagatan 14, Stockholm, 113 48 | ACCEPT | ROUTE | Hagagatan 14, 113 48 |
| Västra Finnbodavägen 4, Nacka, 131 72 | ACCEPT | ROUTE | Västra Finnbodavägen 4, 131 72 |
| Västgötagränd 3, Stockholm, 118 28 | ACCEPT | ROUTE | Västgötagränd 3, 118 28 |

**瑞典 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Kungsgatan 54, Stockholm, 111 35 | CONFIRM | ROUTE | Kungsgatan 54, 111 35 |
| Kungsgatan 2, Stockholm, 111 43 | CONFIRM | ROUTE | Kungsgatan 2, 111 43 |
| Tenstagången 45, Spånga, 16364 | CONFIRM | ROUTE | Tenstavägen 45, 163 64 |
| Sätra Torg 18-20, Stockholm, 12738 | CONFIRM | ROUTE | Hagsätra Torg 18-20, 127 38 |

**瑞典 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Stockholm, Sweden, Stockholm | FIX | OTHER |  |
| Stockholmsv. 33, Stockholm, 181 33 | FIX | LOCALITY |  |
| Kommendörsg. 46, Stockholm | FIX | OTHER |  |

**挪威 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Bråteveien 200, Hellerud gård, Oslo, 2013 Skjetten | FIX | ROUTE | Hellerud gårdsvei 200, 2013 Hellerud |
| Apotekergata, Apotekergata, 0180 | FIX | ROUTE | Apotekergata, 0180 |
| Olav Vs gate, Oslo, 0161 | FIX | ROUTE | Olav Vs gate, 0161 |
| Jernbanegate, Oslo, 3044 | FIX | OTHER |  |

**挪威 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Grønland 1, Oslo, 0188 | CONFIRM | PREMISE | Tøyenbekken 1, 0188 OSLO |
| Balders gate 11, Oslo, 0263 | CONFIRM | PREMISE_PROXIMITY | Balders gate 11, 0263 OSLO |
| Turbinveien 24-6, Lysaker, 0196 | CONFIRM | PREMISE | Turbinveien 24, 0195 OSLO |
| Hausmanns gate 19, Oslo, 0182 | CONFIRM | PREMISE_PROXIMITY | Hausmanns gate 19, 0182 OSLO |

**挪威 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Møllergata 12, Oslo, 0179 | ACCEPT | PREMISE | Møllergata 12, 0179 OSLO |
| Post sendes til: postmottak@eby.oslo.kommune.no. Besøksadresse: Christian Krohgs gate 16,  | ACCEPT | PREMISE | Christian Krohgs gate 16, 0186 OSLO |
| Rostockgata 66, 0194 Oslo, Oslo, 0194 | ACCEPT | PREMISE | Rostockgata 66, 0194 OSLO |
| Storgata 32, Oslo, 0184 | ACCEPT | PREMISE | Storgata 32, 0184 OSLO |

**芬兰 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Mannerheimintie 3, Helsinki, 00100 | ACCEPT | PREMISE | Mannerheimintie 3, 00100 HELSINKI |
| Mechelininkatu 2 e, Helsinki, 00100 | ACCEPT | PREMISE | Mechelininkatu 2, 00100 HELSINKI |
| Kalevankatu 4, Helsinki, 00100 | ACCEPT | PREMISE | Kalevankatu 4, 00100 HELSINKI |
| Ratavartijankatu 2, A, 7 kerros, HELSINKI, 00520 | ACCEPT | PREMISE | Ratavartijankatu 2, 00520 HELSINKI |

**芬兰 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Ranckenintie, Helsinki, 00920 | FIX | ROUTE | Ranckenintie, 00920 |
| Itäkatu 1-5, Helsinki, 00930 | FIX | ROUTE | Itäkatu 1-5, 00930 |
| Lucina Hagmanin polku 2, Helsinki, 00710 | FIX | ROUTE | Lucina Hagmanin polku 2, 00710 |
| Saukonlaituri 1, Helsinki | FIX | ROUTE | Saukonlaituri 1 |

**芬兰 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Ruoholahdenkatu 4, Helsinki, 00100 | CONFIRM | PREMISE | Ruoholahdenkatu 4, 00180 HELSINKI |
| Tapionaukio 4, Espoo, 02100 | CONFIRM | PREMISE | Pohjanpolku 4, 02100 ESPOO |
| Aallonhalkoja 1, Helsinki, 00540 | CONFIRM | PREMISE | Kaasutehtaankatu 1, 00540 HELSINKI |
| Rintinpolku 7E, Helsinki, 00940 | CONFIRM | PREMISE_PROXIMITY | Rintinpolku 7E, 00940 HELSINKI |

**爱沙尼亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Mustika Keskuse apteek, Karjavälja 4, Tallinn, 12918 | CONFIRM | PREMISE | Keskuse 4, Mustamäe linnaosa |
| Tähetorni 100, Tallinn, 11625 | CONFIRM | PREMISE_PROXIMITY | Tähetorni 100, Haabersti linnaosa |
| Volta 7, Tallinn, 10411 | CONFIRM | PREMISE_PROXIMITY | Volta 7, Põhja-Tallinna linnaosa |
| Balti Jaama Turg, Kopli 1, Tallinn, 10412 | CONFIRM | PREMISE | Jaama 1, Nõmme linnaosa |

**爱沙尼亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Lennujaama tee 10, Tallinn, 11101 | ACCEPT | PREMISE | Lennujaama tee 10, Lasnamäe linnaosa |
| Paldiski mnt 102, Tallinn, 13522 | ACCEPT | PREMISE | Paldiski mnt 102, Haabersti linnaosa |
| Akadeemia tee 31, Tallinn, 12618 | ACCEPT | PREMISE | Akadeemia tee 31, Mustamäe linnaosa |
| Väike-Karja 4, Tallinn, 10140 | CONFIRM_ADD_SUBPREMISES | PREMISE | Väike-Karja 4, Kesklinna linnaosa |

**爱沙尼亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Spordiklubi ujumine, Tallinn | FIX | OTHER |  |
| www.salon24.eu, Tallinn | FIX | OTHER |  |
| Raeplatoo, Rae, 12915 | FIX | LOCALITY |  |
| Ahtri, Tallinn, 10151 | FIX | ROUTE | Ahtri, 10151 |

**拉脱维亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Braslas iela 29, Rīga, 1084 | CONFIRM | PREMISE | Braslas iela 29, LV-2167 Mārupe |
| Akmeņu iela 13, Rīga, 1048 | CONFIRM | PREMISE | Akmeņu iela 13, LV-2167 Mārupe |
| Kungu iela 3, Rīga, 1050 | CONFIRM | PREMISE | Kungu iela 3, LV-2167 Tīraine |
| Miera iela 11, Rīga, 1001 | CONFIRM | PREMISE | Miera iela 11, LV-2101 Mežāres |

**拉脱维亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Lidostas parks, Mārupe, LV-2167 | FIX | LOCALITY |  |
| Fabrika, Cenu pagasts, Jelgavas novads, Cena | FIX | ROUTE | Jelgavas iela |
| Kr Barona Iela 14, Riga, LV 1011 | FIX | OTHER |  |
| "Tc "spice"", Rīga | FIX | OTHER |  |

**拉脱维亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Brivibas Iela 49/53, Riga, LV 1010 | ACCEPT | PREMISE | Brīvības iela 49/53, LV-1010 Rīga |
| Kārļa Ulmaņa gatve 106, Rīga, 1029 | ACCEPT | PREMISE | Kārļa Ulmaņa gatve 106, LV-1029 Rīga |
| Granīta iela 13, Rīga, 1057 | ACCEPT | PREMISE | Granīta iela 13, LV-1057 Rīga |
| Balasta dambis 3, Rīga, 1048 | ACCEPT | PREMISE | Balasta dambis 3, LV-1048 Rīga |

**立陶宛 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Eitminų g., Vilnius, 12131 | FIX | ROUTE | Eitminų g., LT-12131 |
| Kalvarijų g., Vilnius | FIX | ROUTE | Kalvarijų g. |
| Ozo Str. 25, Vilnius | FIX | OTHER |  |
| Rodūnios kl., Vilnius, 02189 | FIX | ROUTE | Rodūnios kel., LT-02189 |

**立陶宛 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Oršos gatvė 4, Vilnius, 09300 | ACCEPT | PREMISE | Oršos g. 4, LT-09300 Vilniaus m. |
| Didžioji gatvė 5, Vilnius, 01128 | ACCEPT | PREMISE | Didžioji g. 5, LT-01128 Vilniaus m. |
| Z. Sierakausko gatvė 15, Vilnius, 03105 | ACCEPT | PREMISE | Z. Sierakausko g. 15, LT-03105 Vilniaus m. |
| Šermukšnių gatvė 1, Vilnius, 01106 | ACCEPT | PREMISE | Šermukšnių g. 1, LT-01106 Vilniaus m. |

**立陶宛 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Žydrių g 34, Lindiniškės, Vilniaus r. sav., Avižieniai, 14181 | CONFIRM | PREMISE | Žydrių g. 34, LT-14181 Lindiniškių k. |
| Wix.Com, Rūdninkų gatvė 2, Vilnius, 01135 | CONFIRM | PREMISE_PROXIMITY | Rūdninkų g. 2, LT-01135 Vilniaus m. |
| Dariaus ir Girėno g. 99, Vilnius, 02189 | CONFIRM | PREMISE_PROXIMITY | Dariaus ir Girėno g. 99, LT-02187 Vilniaus m. |
| Laisvės pr 71 b Irminta grožio studija, Vilnius, 07198 | CONFIRM | PREMISE | Laisvės pr. 71, LT-07189 Vilniaus m. |

**波兰 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Wilcza 29a/lok 7, Warszawa, 00-544 | CONFIRM | PREMISE | Wilcza 7, 00-538 Warszawa |
| ul. Korsaka 6, Warszawa, 03-744 | CONFIRM | PREMISE | Komorska 6, 04-161 Warszawa |
| ul. Wyszyńskiego 21, Zielonka, 05-220 | CONFIRM | PREMISE | Mazowiecka 21, 05-220 Zielonka |
| al. Szucha 7, Warszawa, 00-580 | CONFIRM | PREMISE | Sucha 7, 03-649 Warszawa |

**波兰 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Burakowska 16a/lok. 79, Warszawa, 01-066 | FIX | ROUTE | Burakowska 79, 01-066 |
| Krakowskie Przedmieście 16/17/27a, Warszawa, 00-325 | FIX | ROUTE | Krakowskie Przedmieście 16/17/27A, 00-325 |
| Dalibora, Warszawa, 01-439 | FIX | ROUTE | Dalibora, 01-439 |
| Włościańska, Warszawa, 01-710 | FIX | ROUTE | Włościańska, 01-710 |

**波兰 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| ulica Chłodna 52, Warszawa, 00-872 | ACCEPT | PREMISE | Chłodna 52, 00-872 Warszawa |
| Bartycka 175/13, Warszawa, 00-716 | ACCEPT | PREMISE | Bartycka 175, 00-716 Warszawa |
| ulica Karowa 18, Warszawa, 00-324 | ACCEPT | PREMISE | Karowa 18, 00-324 Warszawa |
| Księżycowa 76/9, Warszawa, 01-934 | ACCEPT | PREMISE | Księżycowa 70/9, 01-934 Warszawa |

**捷克 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Praha, Praha | FIX | OTHER |  |
| Czech republic, Praha | FIX | OTHER |  |
| Rašínovo nábř., Praha, 128 00 | FIX | ROUTE | Rašínovo nábřeží, 128 00 |
| Divišovská, Praha, 149 00 | FIX | ROUTE | Divišovská, 149 00 |

**捷克 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Koněvova 240 a/2497, Praha, 130 00 | CONFIRM | PREMISE | Sabinova 240/6, 130 00 Žižkov |
| Zdiměřice 42, Jesenice, 252 42 | CONFIRM | PREMISE | K Šeberovu 42, 252 42 Zdiměřice |
| belohoubkova 2, Praha, 16400 | CONFIRM | PREMISE | Divoká Šárka 8/2, 164 00 Liboc |
| Žižkov, Praha, 130 00 | CONFIRM | ROUTE | Žižkova, 130 00 |

**捷克 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Vladivostocká 1460/10, Praha, 100 00 | ACCEPT | PREMISE | Vladivostocká 1460/10, 100 00 Vršovice |
| Bohnická 15, Praha, 181 00 | ACCEPT | PREMISE | Bohnická 54/15, 181 00 Bohnice |
| Vodičkova 696/26, Praha, 110 00 | ACCEPT | PREMISE | Vodičkova 696/26, 110 00 Nové Město |
| Chlumecká 765/6, Praha 9, 198 00 | ACCEPT | PREMISE | Chlumecká 765/6, 198 00 Praha 9 |

**斯洛伐克 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Seberíniho 821 01, Bratislava, 821 03 | FIX | ROUTE | Seberíniho 821, 821 03 |
| Karpatské námestie 10/A, Bratislava, 831 06 | FIX | ROUTE | Karpatské námestie, 831 06 |
| Záhradnícka, Bratislava, 82108 | FIX | ROUTE | Záhradnícka, 821 08 |
| Jaskový rad, Bratislava, 831 01 | FIX | ROUTE | Jaskový rad, 831 01 |

**斯洛伐克 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Zámocká 6890/20, Bratislava, 811 01 | ACCEPT | PREMISE | Zámocká 6890/20, 811 01 Bratislava-Staré Mesto |
| Thule centrum, Rožňavská 1399/1, Bratislava, 831 04 | ACCEPT | PREMISE | Rožňavská 1399/1, 831 04 Bratislava-Nové Mesto |
| Žilinská 2953/5, Bratislava, 811 05 | ACCEPT | PREMISE | Žilinská 2953/5, 811 05 Bratislava-Staré Mesto |
| Námestie SNP 478/19, Bratislava, 811 01 | ACCEPT | PREMISE | Námestie SNP 478/19, 811 01 Bratislava-Staré Mesto |

**斯洛伐克 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Mlynské nivy 5501, Bratislava, 821 09 | CONFIRM | PREMISE_PROXIMITY | Bratislava I., 5501, 821 09 |
| 6284, Mlynská dolina 841 04, Bratislava, 841 04 | CONFIRM | PREMISE_PROXIMITY | Bratislava I., 6284, 841 04 |
| Lamačská cesta 1C 5959, OC Galéria, Bratislava | CONFIRM | PREMISE_PROXIMITY | Lamačská cesta 1C, 841 04 Bratislava-Lamač |
| Ferdiša Kostku 3291/1, Bratislava, 841 05 | CONFIRM | PREMISE_PROXIMITY | Bratislava I., 3291/1, 841 05 |

**匈牙利 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Duna utca 1, Budapest, 1221 | CONFIRM | ROUTE | Duna utca 1, 1221 |
| Mányoki út 9, Budapest, 1118 | CONFIRM | ROUTE | Mányoki út 9, 1118 |
| Király utca 15, Budapest, 1042 | CONFIRM | ROUTE | Király utca 15, 1042 |
| Sződi utca 55, Dunakeszi, 2120 | CONFIRM | ROUTE | Szondi utca 55, 2120 |

**匈牙利 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Maglódi út 59, Budapest X. kerület, 1106 | ACCEPT | ROUTE | Maglódi út 59, 1106 X. kerület |
| Kövér Lajos utca 21, Budapest, 1149 | ACCEPT | ROUTE | Kövér Lajos utca 21, 1149 |
| Erzsébet királyné útja 125., Budapest, 1142 | ACCEPT | ROUTE | Erzsébet királyné útja 125, 1142 |
| Podmaniczky utca 63, Budapest, 1064 | ACCEPT | ROUTE | Podmaniczky utca 63, 1064 |

**匈牙利 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| MOM Park, Fórum szint, Budapest, 1124 | FIX | LOCALITY |  |
| 14 Tôn Đức Thắng, Budapest, 70000 | FIX | OTHER |  |
| Budapest, Budapest, 1139 | FIX | LOCALITY |  |
| 3. Kerulet, Budapest, 1037 | FIX | LOCALITY |  |

**斯洛文尼亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Podmolniška cesta 14, Ljubljana, 1261 | ACCEPT | PREMISE | Podmolniška cesta 14, 1261 Ljubljana - Dobrunje |
| Litijska cesta 38, Ljubljana, 1000 | ACCEPT | PREMISE | Litijska cesta 38, 1000 Ljubljana |
| Trg komandanta Staneta 12, Ljubljana, 1000 | ACCEPT | PREMISE | Trg komandanta Staneta 12, 1000 Ljubljana |
| Na jami 2, Ljubljana, 1000 | ACCEPT | PREMISE | Na jami 2, 1000 Ljubljana |

**斯洛文尼亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Pod gradom 1, Slovenj Gradec, 2380 | FIX | OTHER |  |
| Dolenjska Cesta157 A, Ljubljana, 1000 | FIX | ROUTE | Dolenjska cesta, 1000 |
| Kolinska ulica 32, Ljubljana, 1000 | FIX | ROUTE | Kolinska ulica 32, 1000 |
| Ameriška ulica, Ljubljana, 1000 | FIX | ROUTE | Ameriška ulica, 1000 |

**斯洛文尼亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Šmartinska cesta 152, Ljubljana, 1000 | CONFIRM | PREMISE_PROXIMITY | Šmartinska cesta 152, 1000 Ljubljana |
| Grič 56, Ljubljana, 1000 | CONFIRM | PREMISE | Peruzzijeva ulica 56, 1000 Ljubljana |
| Jurčkova 232, Ljubljana, 1000 | CONFIRM | PREMISE_PROXIMITY | Jurčkova cesta 232, 1000 Ljubljana |
| Bežigrad 19, Ljubljana, 1000 | CONFIRM | PREMISE | Tomišeljska ulica 19, 1000 Ljubljana |

**克罗地亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Zagreb, Zagreb | FIX | OTHER |  |
| Harmica, Dubravička 6, Zagreb, 10292 | FIX | ROUTE | Harmica 6, 10292 |
| Ulica Josipa Slavenskog 8, Zagreb, 10104 | FIX | ROUTE | Ulica Josipa Slavenskog 8, 10104 |
| Vlaška Ulica, Zagreb | FIX | ROUTE | Vlaška ulica |

**克罗地亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Martićeva 21, Zagreb, 10000 | CONFIRM | PREMISE | Veslačka ulica 21, 10000 Zagreb |
| Nova Ves 8, Zagreb, 10000 | CONFIRM | PREMISE | Stupnička ulica 8, 10000 Zagreb |
| Pantovčak 101, Zagreb, 10000 | CONFIRM | PREMISE | Ilica 101, 10000 Zagreb |
| Mahatma Gandhija 2, Zagreb, 10000 | CONFIRM | PREMISE | Veslačka ulica 2, 10000 Zagreb |

**克罗地亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Radnička cesta 1A, Zagreb, 10000 | ACCEPT | PREMISE | Radnička cesta 1A, 10000 Zagreb |
| Slavonska avenija 6, Zagreb, 10000 | ACCEPT | PREMISE | Slavonska avenija 6, 10000 Zagreb |
| Posedarska ulica 24, Zagreb, 10020 | ACCEPT | PREMISE | Posedarska ulica 24, 10020 Zagreb |
| Čulinečka cesta 223, Zagreb, 10040 | ACCEPT | PREMISE | Čulinečka cesta 223, 10040 Zagreb |

**保加利亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| жк.Сухата река, бл.102А вх.А, София, 1517 | CONFIRM | ROUTE | Суха река 102A, 1517 |
| Бул. Филип Аврамов, София | CONFIRM | ROUTE | Филип Аврамов |
| Улица Дунав 2, София, 1000 | CONFIRM | ROUTE | ул. Дунав 2, 1000 |
| жк Люлин 2 279а, София, 1336 | CONFIRM | ROUTE | Люлин 2, 1336 |

**保加利亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Булевард Първа българска армия 2, София, 1220 | ACCEPT | ROUTE | Първа българска армия 2, 1220 |
| ул. Опълченска 105, бл 42а, София, 1233 | ACCEPT | ROUTE | Ул. Опълченска 105, 1233 |
| Булевард Евлоги и Христо Георгиеви 77, София, 1142 | ACCEPT | ROUTE | бул. Евлоги и Христо Георгиеви 77, 1142 |
| Улица Манол Тошев 1, София, 1000 | ACCEPT | ROUTE | Манол Тошев 1, 1000 |

**保加利亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Столичен Колодрум Сердика, София, 1000 | FIX | LOCALITY |  |
| Модерно предградие, София, 1345 | FIX | LOCALITY |  |
| South Park II, София | FIX | OTHER |  |
| жк Изток 50, София, 1113 | FIX | LOCALITY |  |

**新西兰 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 151 Arthur Street, DressSmart Outlet Centre, Shop 14B, Auckland, 1061 | ACCEPT | PREMISE | Shop 14B, 151 Arthur Street, Onehunga |
| 99 Motions Rd, Auckland, 1022 | ACCEPT | PREMISE | 99 Motions Road, Western Springs |
| 345 Dominion Road, Auckland, 1024 | ACCEPT | PREMISE | 345 Dominion Road, Mount Eden |
| 7, Level 1, Store 57/21 Queen St, Auckland, 1010 | ACCEPT | PREMISE | Level 1, 21 Queen Street, Northcote Point |

**新西兰 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Shop 3/754 Manukau Rd, Auckland, 1023 | FIX | ROUTE | Shop 3, 754 Manukau Road, 1023 |
| 5 Kurnell Drive, Howick, Auckland, 2010 | FIX | LOCALITY |  |
| Cnr of Grey Street & Onehunga Mall Road, Auckland, 1061 | FIX | ROUTE | Grey Street, 1061 |
| Karangahape Road, Auckland | FIX | ROUTE | Karangahape Road |

**新西兰 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Beach Road, Long Bay, Auckland | CONFIRM | ROUTE | Beach Road |
| 17b Farnham Street, Parnell, Auckland, 1052 | CONFIRM | PREMISE_PROXIMITY | 17B Farnham Street, Parnell |
| 63-65 Maki Street, Auckland | CONFIRM | ROUTE | 63-65 Mauī Street |
| 3a Melrose Street, Auckland, 1023 | CONFIRM | PREMISE_PROXIMITY | 3A Melrose Street, Newmarket |

**日本 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 西麻布1-12-4  nishiazabu1124ビルB1, 中央区, 106‐0031 | ACCEPT | PREMISE | 港区西麻布一丁目12 |
| 東京都新宿区新宿３丁目３８−１, 新宿区, 160-0022 | ACCEPT | PREMISE | 新宿区新宿三丁目38 |
| 西日暮里2-18-1, 台東区, 116-0013 | ACCEPT | PREMISE | 荒川区西日暮里二丁目18 |
| 日本橋人形町2-16-1, 中央区 | ACCEPT | PREMISE | 中央区日本橋人形町二丁目16 |

**日本 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 麹町2-10-10-102, 千代田区, 102-0083 | FIX | ROUTE | 〒102-0083 千代田区麹町二丁目10-10-102 |
| 東京都新宿区神楽坂3丁目1 KARUKOZAKA PLACE501, 新宿区, 1620825 | FIX | ROUTE | 〒162-0825 Karukozaka3 |
| 荒川6-2-7, 荒川区, 116-0002 | FIX | LOCALITY |  |
| 恵比寿2-6-25-1F, 渋谷区, 150-0013 | FIX | ROUTE | 〒150-0013 恵比寿二丁目6-25-1F |

**日本 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 新宿３丁目２−７, 港区, 104-0061 | CONFIRM | PREMISE | 新宿区新宿三丁目2 |
| 三田1-11-22 SSTビル2-B, 港区 | CONFIRM | PREMISE | 目黒区三田一丁目11 |

**印度 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| shop no, Shahin Bazar, 3, station Road, near Bandra Depot, Mumbai, 400050 | CONFIRM | ROUTE | 3 Station Road, 400050 |
| Santacruz East Nehru Road, Mumbai, 400055 | CONFIRM | ROUTE | Nehru Road, 400055 |
| Next to Samrudh CNG Filling Station, Near Nexa Showroom, L.B.S. Marg, Kurla (West), Mumbai | CONFIRM | ROUTE | LBS Marg, 400070 |
| Plej Fitness - H Wing, Bldg No. 3, Next to HDFC Bank, 90 Feet, D P Road, Thakur Complex, K | CONFIRM | PREMISE_PROXIMITY | HDFC Bank, 90, 400101 |

**印度 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Chandiwali Road, Mumbai, 400069 | FIX | LOCALITY |  |
| Dubai, Mumbai, Mumbai | FIX | OTHER |  |
| Office No 408; Mohan Trebeca ;Near K M Agarwal College; Ghandhar Road ; Kalyan West 421301 | FIX | LOCALITY |  |
| krishna city, Mumbai | FIX | OTHER |  |

**印度 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| bldg, 3rd Floor, Unit, MOHID HEIGHTS, 1, Lokhandwala Circle, Mumbai, 400053 | ACCEPT | ROUTE | 3Rd Floor, 1 Lokhandwala Circle, 400053 |
| 3/4, 1St Floor, Giriraj Building, Ram Tekdi, Tokershi Jivraj Rd, Mumbai, 400015 | ACCEPT | ROUTE | 1St Floor, 3/4 Jivraj Road, 400015 |
| A-104, Naman Midtown, Senapati Bapat Road, Fitwala Road, Mumbai, 400013 | ACCEPT | ROUTE | 104 Fitwala Road, 400013 |
| Room No 2, Atharva CHS, NM Joshi Marg, Arthur Road Naka, Chinchpokli, Mumbai, 400011 | ACCEPT | PREMISE_PROXIMITY | Chinchpokli, 2 N M Joshi Marg, 400011 |

