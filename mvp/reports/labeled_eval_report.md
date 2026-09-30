# 标注数据评测报告（自动生成）

- 数据：`labeled/orders_sg_v1.csv`，指标均在其测试部分 4,000 条上计算
- 置信度：用 `labeled/orders_sg_v1.csv` 的训练部分 6,000 条统计（按真实地址切分，与测试部分不重叠）
- 校验器：规则方案，默认 BALANCED 档，未加载楼栋属性表
- 单条延迟 P50 1.2 ms / P95 8.9 ms

## 1. 总体

| 指标 | 数值 | 说明 |
|---|---|---|
| 自动通过率 | 78.6% | 结论为 ACCEPT 的订单占比 |
| 直接通过率 | 78.6% | ACCEPT + 仅提示补单元号 |
| 直接通过中的错误率 | 0.41% | 直接通过的订单里地址不对的比例 |
| 静默错误率 | 0.33% | 地址不对却直接通过，占全部订单 |
| 可确定地址的识别率 | 98.9% | 文字足以确定地址的订单里，找对地址的比例 |
| 误拒率 | 1.0% | 文字足以确定地址，却判 FIX |
| 结论合理率 | 85.6% | 结论符合标注规范（不含"误导"类） |
| 缺单元号检出率 | 22.5% | 多单元楼缺单元号时，提示补充的比例（436 单） |
| 单元号解析正确率 | 99.7% | 写了单元号且地址找对时，单元号解析正确的比例 |

### 结论分布

| 结果 | 占比 | 含义 |
|---|---|---|
| 正确 | 81.4% | 地址对，结论符合标注规范 |
| 正确拒绝 | 3.8% | 判 FIX，且仅凭文字确实无法确定真实地址 |
| 多余确认 | 4.5% | 地址对，本可直接通过却要求用户确认（多一次打扰，不造成错误） |
| 漏报 | 8.5% | 地址对，但该提示的没提示（如缺单元号、需纠错的改动）就直接通过 |
| 误拒 | 1.0% | 文字足以确定地址，却判 FIX |
| 错误建议 | 0.5% | 给出的地址不对，但要求用户确认（用户有机会发现） |
| 静默错误 | 0.3% | 给出的地址不对，却直接通过（ACCEPT / 仅提示补单元号） |

## 2. 分场景


### 按"仅凭文字能判断到什么程度"

| 分组 | 单数 | 正确 + 正确拒绝 | 多余确认 | 漏报 | 误拒 | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|---|
| RESOLVABLE | 3818 | 85.3% | 4.8% | 8.9% | 1.0% | 0.0% | 0.0% |
| AMBIGUOUS | 32 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| CONFLICTING | 8 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| MISLEADING | 20 | 0.0% | 0.0% | 0.0% | 0.0% | 35.0% | 65.0% |
| NOT_IN_REFERENCE | 71 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| OUT_OF_REGION | 25 | 60.0% | 0.0% | 0.0% | 0.0% | 40.0% | 0.0% |
| NO_ADDRESS | 26 | 96.2% | 0.0% | 0.0% | 0.0% | 3.8% | 0.0% |

### 按渠道

| 分组 | 单数 | 正确 + 正确拒绝 | 多余确认 | 漏报 | 误拒 | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|---|
| web_form | 1644 | 82.4% | 5.2% | 10.6% | 1.0% | 0.4% | 0.4% |
| mobile_app | 992 | 92.7% | 1.3% | 4.8% | 0.0% | 0.5% | 0.6% |
| chat | 578 | 75.3% | 12.1% | 8.8% | 2.6% | 1.0% | 0.2% |
| marketplace | 422 | 87.9% | 1.4% | 9.5% | 1.2% | 0.0% | 0.0% |
| b2b_upload | 364 | 90.1% | 2.2% | 6.6% | 0.8% | 0.3% | 0.0% |

### 按物业类型

| 分组 | 单数 | 正确 + 正确拒绝 | 多余确认 | 漏报 | 误拒 | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|---|
| HDB | 2412 | 83.4% | 5.3% | 9.7% | 1.3% | 0.1% | 0.2% |
| COMMERCIAL | 682 | 87.4% | 2.8% | 8.5% | 0.6% | 0.4% | 0.3% |
| CONDO | 564 | 86.5% | 4.1% | 8.3% | 0.4% | 0.4% | 0.4% |
| LANDED | 291 | 93.5% | 4.5% | 0.0% | 0.7% | 0.0% | 1.4% |
| （非地址） | 51 | 78.4% | 0.0% | 0.0% | 0.0% | 21.6% | 0.0% |

### 按错误标签（一单可有多个标签，至少 15 单才列出）

| 分组 | 单数 | 正确 + 正确拒绝 | 多余确认 | 漏报 | 误拒 | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|---|
| （无错误） | 1560 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| UNIT_FORMAT | 973 | 91.0% | 7.1% | 0.0% | 1.3% | 0.3% | 0.3% |
| ABBREV | 884 | 77.0% | 10.7% | 10.7% | 1.1% | 0.2% | 0.1% |
| NOISE_PHONE | 544 | 75.9% | 12.3% | 8.5% | 2.4% | 0.6% | 0.4% |
| NOISE_NAME | 538 | 75.5% | 12.5% | 8.6% | 2.6% | 0.7% | 0.2% |
| UNIT_MISSING | 452 | 23.7% | 0.0% | 74.8% | 1.5% | 0.0% | 0.0% |
| NOISE_NOTE | 218 | 74.8% | 14.2% | 8.7% | 2.3% | 0.0% | 0.0% |
| POSTAL_MISSING | 207 | 96.1% | 0.0% | 0.0% | 2.4% | 1.4% | 0.0% |
| NOISE_COMPANY | 184 | 89.7% | 2.2% | 6.5% | 1.1% | 0.5% | 0.0% |
| STREET_TYPO | 158 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| DUPLICATED_TEXT | 101 | 62.4% | 29.7% | 5.0% | 2.0% | 1.0% | 0.0% |
| TOWN_ABBREV | 88 | 69.3% | 15.9% | 10.2% | 4.5% | 0.0% | 0.0% |
| LOCATION_HINT | 58 | 29.3% | 63.8% | 1.7% | 3.4% | 1.7% | 0.0% |
| BUILDING_ONLY | 55 | 96.4% | 0.0% | 0.0% | 3.6% | 0.0% | 0.0% |
| BLOCK_LETTER_DROPPED | 48 | 10.4% | 0.0% | 0.0% | 64.6% | 10.4% | 14.6% |
| NEW_HDB_BLOCK | 45 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| POSTAL_TYPO | 44 | 79.5% | 0.0% | 0.0% | 4.5% | 2.3% | 13.6% |
| BLOCK_MISSING | 41 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| NO_ADDRESS | 26 | 96.2% | 0.0% | 0.0% | 0.0% | 3.8% | 0.0% |
| BUILDING_TYPO | 26 | 92.3% | 0.0% | 7.7% | 0.0% | 0.0% | 0.0% |
| OUT_OF_REGION | 25 | 60.0% | 0.0% | 0.0% | 0.0% | 40.0% | 0.0% |
| BLOCK_TYPO | 19 | 94.7% | 0.0% | 0.0% | 5.3% | 0.0% | 0.0% |
| POSTAL_OTHER_ADDRESS | 15 | 86.7% | 0.0% | 0.0% | 0.0% | 13.3% | 0.0% |

## 3. 置信度：旧模型 vs 用订单数据重新统计

| 模型 | 校准误差 ECE | Brier | 区分度 AUROC（给出地址的结论） |
|---|---|---|---|
| 旧模型（合成测试集统计） | 0.0180 | 0.0179 | 0.735 |
| 新模型（订单训练部分统计） | 0.0050 | 0.0095 | 0.677 |

AUROC：随机取一条对的、一条错的结论，对的那条置信度更高的概率；0.5 = 完全没有区分度，1 = 完美区分。

### 旧模型（合成测试集统计）：置信度区间 vs 实际正确率

| 置信度区间 | 单数 | 平均置信度 | 实际正确率 |
|---|---|---|---|
| 0.950 – 0.990 | 37 | 98.69% | 100.00% |
| 0.990 – 0.999 | 72 | 99.47% | 48.61% |
| 0.999 – 1.000 | 3891 | 100.00% | 99.10% |

### 新模型（订单训练部分统计）：置信度区间 vs 实际正确率

| 置信度区间 | 单数 | 平均置信度 | 实际正确率 |
|---|---|---|---|
| 0.000 – 0.500 | 44 | 22.85% | 18.18% |
| 0.500 – 0.700 | 15 | 63.25% | 40.00% |
| 0.900 – 0.950 | 67 | 93.68% | 100.00% |
| 0.950 – 0.990 | 188 | 96.67% | 97.34% |
| 0.990 – 0.999 | 3308 | 99.61% | 99.49% |
| 0.999 – 1.000 | 378 | 99.99% | 98.68% |

### 按置信度门槛自动通过（ACCEPT 且置信度 ≥ 门槛，否则降为 CONFIRM）

| 模型 | 门槛 | 自动通过率 | 静默错误率 | 直接通过中的错误率 |
|---|---|---|---|---|
| 旧模型（合成测试集统计） | 0.0 | 78.6% | 0.33% | 0.41% |
| 旧模型（合成测试集统计） | 0.9 | 78.6% | 0.33% | 0.41% |
| 旧模型（合成测试集统计） | 0.95 | 78.6% | 0.33% | 0.41% |
| 旧模型（合成测试集统计） | 0.97 | 78.6% | 0.33% | 0.41% |
| 旧模型（合成测试集统计） | 0.99 | 78.6% | 0.33% | 0.41% |
| 旧模型（合成测试集统计） | 0.995 | 78.6% | 0.33% | 0.41% |
| 新模型（订单训练部分统计） | 0.0 | 78.6% | 0.33% | 0.41% |
| 新模型（订单训练部分统计） | 0.9 | 78.6% | 0.33% | 0.41% |
| 新模型（订单训练部分统计） | 0.95 | 78.6% | 0.33% | 0.41% |
| 新模型（订单训练部分统计） | 0.97 | 78.6% | 0.33% | 0.41% |
| 新模型（订单训练部分统计） | 0.99 | 78.6% | 0.33% | 0.41% |
| 新模型（订单训练部分统计） | 0.995 | 68.0% | 0.25% | 0.37% |

### 新模型：风险最高的结论类别（训练部分至少 20 单）

| 结论类别 | 训练单数 | 其中正确 | 实际正确率 |
|---|---|---|---|
| 判 FIX：POSTCODE_BLOCK_CONFLICT | 124 | 26 | 21.0% |
| 楼栋确认 · 道路确认 · 邮编补全 · 有未识别文字 | 39 | 36 | 92.3% |
| 判 FIX：NO_MATCH | 136 | 128 | 94.1% |
| 楼栋确认 · 道路纠错 · 邮编补全 | 22 | 21 | 95.5% |
| 楼栋补全 · 道路补全 · 邮编补全 · 楼宇名吻合 · 仅楼宇名 | 24 | 23 | 95.8% |
| 楼栋确认 · 道路确认 · 邮编补全 · 楼宇名吻合 | 27 | 26 | 96.3% |
| 楼栋确认 · 道路确认 · 邮编补全 | 149 | 144 | 96.6% |
| 楼栋确认 · 道路确认 · 邮编替换 | 59 | 58 | 98.3% |
| 判 FIX：PREMISE_NOT_FOUND | 250 | 248 | 99.2% |
| 楼栋确认 · 道路确认 · 邮编确认 · 楼宇名吻合 | 607 | 603 | 99.3% |
| 楼栋确认 · 道路确认 · 邮编确认 | 4072 | 4058 | 99.7% |
| 楼栋确认 · 道路确认 · 邮编确认 · 有未识别文字 | 230 | 230 | 100.0% |

### 新模型：最常见的结论类别

| 结论类别 | 训练单数 | 其中正确 | 实际正确率 |
|---|---|---|---|
| 楼栋确认 · 道路确认 · 邮编确认 | 4072 | 4058 | 99.7% |
| 楼栋确认 · 道路确认 · 邮编确认 · 楼宇名吻合 | 607 | 603 | 99.3% |
| 判 FIX：PREMISE_NOT_FOUND | 250 | 248 | 99.2% |
| 楼栋确认 · 道路纠错 · 邮编确认 | 246 | 246 | 100.0% |
| 楼栋确认 · 道路确认 · 邮编确认 · 有未识别文字 | 230 | 230 | 100.0% |
| 楼栋确认 · 道路确认 · 邮编补全 | 149 | 144 | 96.6% |
| 判 FIX：NO_MATCH | 136 | 128 | 94.1% |
| 判 FIX：POSTCODE_BLOCK_CONFLICT | 124 | 26 | 21.0% |
| 判 FIX：AMBIGUOUS_MULTIPLE_CANDIDATES | 80 | 80 | 100.0% |
| 楼栋确认 · 道路确认 · 邮编替换 | 59 | 58 | 98.3% |

## 4. 错误样例（测试部分，每类最多 3 条）

**静默错误 · MISLEADING · BLOCK_LETTER_DROPPED**（7 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-02942 | 03-01 63 Nanyang View, NANYANG TECHNOLOGICAL UNIVERSITY (NANYANG VIEW STAFF HOUSING), Singapore 639650 | ACCEPT | 63 NANYANG VIEW 639650 | 63A NANYANG VIEW 639650 |
| ORD-03487 | Unit B1-53 205 Thomson Road, goldhill shopping centre, Singapore, S307639 | ACCEPT | 205 THOMSON ROAD 307639 | 205B THOMSON ROAD 307639 |
| ORD-03494 | No. 107 Sophia Road, HP 87740395, 228172 | ACCEPT | 107 SOPHIA ROAD 228172 | 107A SOPHIA ROAD 228172 |

**静默错误 · MISLEADING · POSTAL_TYPO+AUTOFILL_WRONG**（6 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-04158 | Block 166 Yung Kuang Road, #02-302, Singapore 610166 | ACCEPT | 166 YUNG KUANG ROAD 610166 | 166A YUNG KUANG ROAD 611166 |
| ORD-05137 | 26 Bridport Avenue, Singapore 559316 | ACCEPT | 26 BRIDPORT AVENUE 559316 | 23 BRIDPORT AVENUE 559313 |
| ORD-06468 | Block 451 Choa Chu Kang Avenue 4, #06-41, Singapore 680451 | ACCEPT | 451 CHOA CHU KANG AVENUE 4 680451 | 541 CHOA CHU KANG STREET 52 680541 |

**错误建议 · OUT_OF_REGION · OUT_OF_REGION**（10 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00082 | NO. 31, JALAN SETIA 5/4, TAMAN SETIA, 80879 JOHOR BAHRU, JOHOR | CONFIRM | 31 JALAN SETIA 368449 | 80879 |
| ORD-00100 | no. 29, jalan daya 5/5, taman daya, 81179 masai, johor, malaysia | CONFIRM | 29 JALAN RAYA 368581 | 81179 |
| ORD-00744 | no. 18, jalan molek 8/8, taman molek, 79225 iskandar puteri, johor, malaysia | CONFIRM | 18 JALAN MOLEK 399535 | 79225 |

**错误建议 · MISLEADING · POSTAL_MISSING+BLOCK_LETTER_DROPPED**（3 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01475 | blk 447 bukit batok w ave 9 #11-97 / to Ravi Shankar / Contact: +6584255078 | CONFIRM | 447 BUKIT BATOK WEST AVENUE 9 650447 | 447A BUKIT BATOK WEST AVENUE 9 651447 |
| ORD-04087 | Name: Nurul Huda, unit 16-313 blk 311 anchorvale lane, hp +6582822806 | CONFIRM | 311 ANCHORVALE LANE 540311 | 311D ANCHORVALE LANE 544311 |
| ORD-06567 | Name: Priscilla Goh UNIT 05-273 BLK 781 WOODLANDS AVE 9 hp 87550923 | CONFIRM | 781 WOODLANDS AVENUE 9 730781 | 781E WOODLANDS AVENUE 9 735781 |

**错误建议 · MISLEADING · POSTAL_OTHER_ADDRESS+AUTOFILL_WRONG**（2 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00780 | 106 Bukit Batok Central, #05-03 Ppis Child Development Centre - Bukit Batok, Singapore 650106 | CONFIRM | 106 BUKIT BATOK CENTRAL 650106 | 21 BUKIT BATOK EAST AVENUE 6 659759 |
| ORD-05429 | 94 Geylang Bahru, #09-06 Eight Riversuites, Singapore 330094 | CONFIRM | 94 GEYLANG BAHRU 330094 | 48 WHAMPOA EAST 338540 |

**错误建议 · MISLEADING · POSTAL_TYPO+AUTOFILL_WRONG+LOCATION_HINT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01152 | 57 Jansen Road, #01-12 lift lobby B, Singapore 548456 | CONFIRM | 57 JANSEN ROAD 548456 | 45C SIMON PLACE 544856 |

**错误建议 · RESOLVABLE · BLOCK_LETTER_DROPPED**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-02744 | Redhill Foods Pte. Ltd., Attn: Wendy Lau, #06-08 46 Lorong 32 Geylang, Bodhi Compassion Buddhist Centre, Singapore 398306 | CONFIRM | 46 LORONG 32 GEYLANG 398306 | 46A LORONG 32 GEYLANG 398306 |

**错误建议 · NO_ADDRESS · NO_ADDRESS**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-02831 | 0 | CONFIRM | 3 RESEARCH LINK 117602 | — |

**错误建议 · MISLEADING · BLOCK_LETTER_DROPPED+DUPLICATED_TEXT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-05685 | 45 Beach rOad, 01-20 45 Beach Road, Singapore, 189682 | CONFIRM | 45 BEACH ROAD 189682 | 45A BEACH ROAD 189682 |

**误拒 · RESOLVABLE · BLOCK_LETTER_DROPPED**（20 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00611 | BLK 516 WOODLANDS DRIVE 14, 22-253, Singapore, 731516 | FIX | — | 516A WOODLANDS DRIVE 14 731516 |
| ORD-01926 | 66 Circuit Road, #07-205, 371066 | FIX | — | 66A CIRCUIT ROAD 371066 |
| ORD-02295 | Name: Arjun Nair / blk 450 bukit batok west avenue 6 #2-63 singapore 653450 / Contact: 86347129 | FIX | — | 450C BUKIT BATOK WEST AVENUE 6 653450 |

**误拒 · RESOLVABLE · UNIT_MISSING+BLOCK_LETTER_DROPPED**（6 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01119 | Blk 954 Tampines Street 96, 522954 | FIX | — | 954B TAMPINES STREET 96 522954 |
| ORD-04457 | to Siti Rahmah, 133 Jalan Bukit Merah spore 161133, hp 8938 4382, put at letterbox | FIX | — | 133A JALAN BUKIT MERAH 161133 |
| ORD-04937 | Blk 505 Bishan Street 11, 571505 | FIX | — | 505A BISHAN STREET 11 571505 |

**误拒 · RESOLVABLE · CHINESE_ADDRESS+POSTAL_MISSING**（2 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00074 | Blk 755 兀兰4道 Unit 17-1267, Singapore | FIX | — | 755 WOODLANDS AVENUE 4 730755 |
| ORD-07938 | #10-332 blk 144 碧山12街 / Name: Aishah Rahman / 98049968 | FIX | — | 144 BISHAN STREET 12 570144 |

**误拒 · RESOLVABLE · POSTAL_MISSING+TOWN_ABBREV**（2 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01352 | Name: Farhan Ismail, Blk 256 S'goon Cent Drive #13-105, hp 99244055, don't ring bell baby sleeping | FIX | — | 256 SERANGOON CENTRAL DRIVE 550256 |
| ORD-08367 | #18-57 101 bt batok west avenue 6 to Benjamin Ho hp 84132123 | FIX | — | 101 BUKIT BATOK WEST AVENUE 6 650101 |

**误拒 · RESOLVABLE · BLOCK_LETTER_DROPPED+TOWN_ABBREV**（2 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-03633 | Block 228 PG Field #08-291, Singapore 821228 | FIX | — | 228A PUNGGOL FIELD 821228 |
| ORD-05452 | Name: Yeo Hui Min / Blk 918 HG Avenue 9, #08-350 S531918 | FIX | — | 918A HOUGANG AVENUE 9 531918 |

**误拒 · RESOLVABLE · BUILDING_ONLY+POSTAL_MISSING**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00355 | Redhill Foods Pte. Ltd., Santa Grand Hotel East Coast B1-70 | FIX | — | 171 EAST COAST ROAD 428877 |

**误拒 · RESOLVABLE · POSTAL_TYPO**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01246 | Siglap Shopping Centre, 897 E Coast Rd. #03-18, 459120 | FIX | — | 897 EAST COAST ROAD 459100 |

**误拒 · RESOLVABLE · BLOCK_LETTER_DROPPED+LOCATION_HINT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01588 | Priscilla Goh 485 choa chu kang avenue 5 unit #05-314 lift lobby b s681485 | FIX | — | 485A CHOA CHU KANG AVENUE 5 681485 |

**误拒 · RESOLVABLE · UNIT_MISSING+BLOCK_LETTER_DROPPED+LOCATION_HINT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-02702 | Name: Ravi Shankar, blk 225 pasir ris st. 21 guardhouse singapore 511225 | FIX | — | 225A PASIR RIS STREET 21 511225 |

**误拒 · RESOLVABLE · BLOCK_TYPO+STREET_TRUNCATED**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-03795 | BLK 626B TAMPINES NORTH DRI # 02-128, SINGAPORE, 522636 | FIX | — | 636B TAMPINES NORTH DRIVE 2 522636 |

**误拒 · RESOLVABLE · BLOCK_LETTER_DROPPED+DUPLICATED_TEXT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-05262 | BLK 132 JALAN BUKIT MERAH #4-04, SINGAPORE, SINGAPORE, 161132 (+65) 8806 9586 | FIX | — | 132A JALAN BUKIT MERAH 161132 |

**误拒 · RESOLVABLE · BUILDING_ONLY**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-07305 | Brightpath Education Pte Ltd, Tuas Bay Industrial Centre # 01-12, 637519 | FIX | — | 76 TUAS SOUTH AVENUE 2 637519 |

**误拒 · RESOLVABLE · POSTAL_TYPO+DUPLICATED_TEXT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-08916 | 10 MARINA BOULEVARD, #14-05 Marina Bay Financial Centre 10 Marina Boulevard, 018986 | FIX | — | 10 MARINA BOULEVARD 018983 |

**漏报 · RESOLVABLE · UNIT_MISSING**（323 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00030 | blk103 ang mo kio ave 3, Singapore 560103 | ACCEPT | 103 ANG MO KIO AVENUE 3 560103 | 103 ANG MO KIO AVENUE 3 560103 |
| ORD-00045 | 62 KIM YAM ROAD, SINGAPORE, 239363 | ACCEPT | 62 KIM YAM ROAD 239363 | 62 KIM YAM ROAD 239363 |
| ORD-00046 | 32 jln limau nipis, 468285 | ACCEPT | 32 JALAN LIMAU NIPIS 468285 | 32 JALAN LIMAU NIPIS 468285 |

**漏报 · RESOLVABLE · UNIT_MISSING+TOWN_ABBREV**（9 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-02627 | Blk 169 WDL St. 11, Singapore, 730169 | ACCEPT | 169 WOODLANDS STREET 11 730169 | 169 WOODLANDS STREET 11 730169 |
| ORD-03120 | BLK 277 TAMP ST 22, Singapore, 520277 | ACCEPT | 277 TAMPINES STREET 22 520277 | 277 TAMPINES STREET 22 520277 |
| ORD-03147 | block 172 bt batok west avenue 8, Singapore, 650172 | ACCEPT | 172 BUKIT BATOK WEST AVENUE 8 650172 | 172 BUKIT BATOK WEST AVENUE 8 650172 |

