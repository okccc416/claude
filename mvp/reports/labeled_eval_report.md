# 标注数据评测报告（自动生成）

- 数据：`labeled/orders_sg_v1.csv`，指标均在其测试部分 4,000 条上计算
- 置信度：用 `labeled/orders_sg_v1.csv` 的训练部分 6,000 条统计（按真实地址切分，与测试部分不重叠）
- 校验器：规则方案，默认 BALANCED 档，未加载楼栋属性表
- 单条延迟 P50 1.1 ms / P95 7.2 ms

## 1. 总体

| 指标 | 数值 | 说明 |
|---|---|---|
| 自动通过率 | 77.2% | 结论为 ACCEPT 的订单占比 |
| 直接通过率 | 83.5% | ACCEPT + 仅提示补单元号 |
| 直接通过中的错误率 | 0.54% | 直接通过的订单里地址不对的比例 |
| 静默错误率 | 0.45% | 地址不对却直接通过，占全部订单 |
| 可确定地址的识别率 | 99.7% | 文字足以确定地址的订单里，找对地址的比例 |
| 误拒率 | 0.3% | 文字足以确定地址，却判 FIX |
| 结论合理率 | 96.1% | 结论符合标注规范（不含"误导"类） |
| 缺单元号检出率 | 74.0% | 多单元楼缺单元号时，提示补充的比例（443 单） |
| 单元号解析正确率 | 99.7% | 写了单元号且地址找对时，单元号解析正确的比例 |

### 结论分布

| 结果 | 占比 | 含义 |
|---|---|---|
| 正确 | 91.6% | 地址对，结论符合标注规范 |
| 正确拒绝 | 4.0% | 判 FIX，且仅凭文字确实无法确定真实地址 |
| 多余确认 | 0.7% | 地址对，本可直接通过却要求用户确认（多一次打扰，不造成错误） |
| 漏报 | 2.9% | 地址对，但该提示的没提示（如缺单元号、需纠错的改动）就直接通过 |
| 误拒 | 0.2% | 文字足以确定地址，却判 FIX |
| 错误建议 | 0.1% | 给出的地址不对，但要求用户确认（用户有机会发现） |
| 静默错误 | 0.4% | 给出的地址不对，却直接通过（ACCEPT / 仅提示补单元号） |

## 2. 分场景


### 按"仅凭文字能判断到什么程度"

| 分组 | 单数 | 正确 + 正确拒绝 | 多余确认 | 漏报 | 误拒 | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|---|
| RESOLVABLE | 3818 | 96.0% | 0.7% | 3.0% | 0.3% | 0.0% | 0.0% |
| AMBIGUOUS | 32 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| CONFLICTING | 8 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| MISLEADING | 20 | 0.0% | 0.0% | 0.0% | 0.0% | 15.0% | 85.0% |
| NOT_IN_REFERENCE | 71 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| OUT_OF_REGION | 25 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| NO_ADDRESS | 26 | 96.2% | 0.0% | 0.0% | 0.0% | 3.8% | 0.0% |

### 按渠道

| 分组 | 单数 | 正确 + 正确拒绝 | 多余确认 | 漏报 | 误拒 | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|---|
| web_form | 1644 | 95.0% | 0.9% | 3.5% | 0.2% | 0.0% | 0.4% |
| mobile_app | 992 | 98.0% | 0.0% | 1.1% | 0.0% | 0.0% | 0.9% |
| chat | 578 | 94.5% | 1.0% | 3.1% | 0.5% | 0.7% | 0.2% |
| marketplace | 422 | 97.4% | 0.2% | 2.1% | 0.2% | 0.0% | 0.0% |
| b2b_upload | 364 | 92.3% | 1.1% | 5.5% | 0.8% | 0.0% | 0.3% |

### 按物业类型

| 分组 | 单数 | 正确 + 正确拒绝 | 多余确认 | 漏报 | 误拒 | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|---|
| HDB | 2412 | 98.7% | 0.7% | 0.0% | 0.2% | 0.1% | 0.2% |
| COMMERCIAL | 682 | 87.7% | 1.3% | 9.7% | 0.6% | 0.0% | 0.7% |
| CONDO | 564 | 90.4% | 0.2% | 8.7% | 0.0% | 0.0% | 0.7% |
| LANDED | 291 | 98.6% | 0.0% | 0.0% | 0.0% | 0.0% | 1.4% |
| （非地址） | 51 | 98.0% | 0.0% | 0.0% | 0.0% | 2.0% | 0.0% |

### 按错误标签（一单可有多个标签，至少 15 单才列出）

| 分组 | 单数 | 正确 + 正确拒绝 | 多余确认 | 漏报 | 误拒 | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|---|
| （无错误） | 1560 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| UNIT_FORMAT | 973 | 97.1% | 1.7% | 0.1% | 0.4% | 0.2% | 0.4% |
| ABBREV | 884 | 94.3% | 0.9% | 4.2% | 0.2% | 0.2% | 0.1% |
| NOISE_PHONE | 544 | 94.9% | 0.7% | 2.9% | 0.6% | 0.6% | 0.4% |
| NOISE_NAME | 538 | 93.5% | 1.3% | 3.7% | 0.6% | 0.6% | 0.4% |
| UNIT_MISSING | 452 | 74.6% | 0.0% | 25.4% | 0.0% | 0.0% | 0.0% |
| NOISE_NOTE | 218 | 94.5% | 0.9% | 4.1% | 0.5% | 0.0% | 0.0% |
| POSTAL_MISSING | 207 | 96.1% | 0.0% | 0.0% | 2.4% | 1.4% | 0.0% |
| NOISE_COMPANY | 184 | 91.3% | 1.6% | 5.4% | 1.1% | 0.0% | 0.5% |
| STREET_TYPO | 158 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| DUPLICATED_TEXT | 101 | 86.1% | 8.9% | 3.0% | 1.0% | 0.0% | 1.0% |
| TOWN_ABBREV | 88 | 85.2% | 10.2% | 1.1% | 3.4% | 0.0% | 0.0% |
| LOCATION_HINT | 58 | 96.6% | 1.7% | 0.0% | 0.0% | 0.0% | 1.7% |
| BUILDING_ONLY | 55 | 96.4% | 0.0% | 0.0% | 3.6% | 0.0% | 0.0% |
| BLOCK_LETTER_DROPPED | 48 | 72.9% | 0.0% | 0.0% | 2.1% | 6.2% | 18.8% |
| NEW_HDB_BLOCK | 45 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| POSTAL_TYPO | 44 | 79.5% | 0.0% | 0.0% | 4.5% | 0.0% | 15.9% |
| BLOCK_MISSING | 41 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| NO_ADDRESS | 26 | 96.2% | 0.0% | 0.0% | 0.0% | 3.8% | 0.0% |
| BUILDING_TYPO | 26 | 88.5% | 0.0% | 11.5% | 0.0% | 0.0% | 0.0% |
| OUT_OF_REGION | 25 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| BLOCK_TYPO | 19 | 89.5% | 0.0% | 5.3% | 5.3% | 0.0% | 0.0% |
| POSTAL_OTHER_ADDRESS | 15 | 86.7% | 0.0% | 0.0% | 0.0% | 0.0% | 13.3% |

## 3. 置信度：旧模型 vs 用订单数据重新统计

| 模型 | 校准误差 ECE | Brier | 区分度 AUROC（给出地址的结论） |
|---|---|---|---|
| 旧模型（合成测试集统计） | 0.0080 | 0.0080 | 0.534 |
| 新模型（订单训练部分统计） | 0.0048 | 0.0074 | 0.602 |

AUROC：随机取一条对的、一条错的结论，对的那条置信度更高的概率；0.5 = 完全没有区分度，1 = 完美区分。

### 旧模型（合成测试集统计）：置信度区间 vs 实际正确率

| 置信度区间 | 单数 | 平均置信度 | 实际正确率 |
|---|---|---|---|
| 0.950 – 0.990 | 29 | 98.69% | 100.00% |
| 0.990 – 0.999 | 67 | 99.49% | 89.55% |
| 0.999 – 1.000 | 3904 | 100.00% | 99.36% |

### 新模型（订单训练部分统计）：置信度区间 vs 实际正确率

| 置信度区间 | 单数 | 平均置信度 | 实际正确率 |
|---|---|---|---|
| 0.500 – 0.700 | 3 | 54.10% | 0.00% |
| 0.700 – 0.900 | 10 | 87.27% | 80.00% |
| 0.900 – 0.950 | 59 | 92.99% | 100.00% |
| 0.950 – 0.990 | 205 | 96.80% | 98.05% |
| 0.990 – 0.999 | 3442 | 99.63% | 99.39% |
| 0.999 – 1.000 | 281 | 99.98% | 99.29% |

### 按置信度门槛自动通过（ACCEPT 且置信度 ≥ 门槛，否则降为 CONFIRM）

| 模型 | 门槛 | 自动通过率 | 静默错误率 | 直接通过中的错误率 |
|---|---|---|---|---|
| 旧模型（合成测试集统计） | 0.0 | 77.2% | 0.45% | 0.54% |
| 旧模型（合成测试集统计） | 0.9 | 77.2% | 0.45% | 0.54% |
| 旧模型（合成测试集统计） | 0.95 | 77.2% | 0.45% | 0.54% |
| 旧模型（合成测试集统计） | 0.97 | 77.2% | 0.45% | 0.54% |
| 旧模型（合成测试集统计） | 0.99 | 77.2% | 0.45% | 0.54% |
| 旧模型（合成测试集统计） | 0.995 | 77.2% | 0.45% | 0.54% |
| 新模型（订单训练部分统计） | 0.0 | 77.2% | 0.45% | 0.54% |
| 新模型（订单训练部分统计） | 0.9 | 77.2% | 0.45% | 0.54% |
| 新模型（订单训练部分统计） | 0.95 | 77.2% | 0.45% | 0.54% |
| 新模型（订单训练部分统计） | 0.97 | 77.2% | 0.45% | 0.54% |
| 新模型（订单训练部分统计） | 0.99 | 77.2% | 0.45% | 0.54% |
| 新模型（订单训练部分统计） | 0.995 | 66.6% | 0.38% | 0.51% |

### 新模型：风险最高的结论类别（训练部分至少 20 单）

| 结论类别 | 训练单数 | 其中正确 | 实际正确率 |
|---|---|---|---|
| 判 FIX：POSTCODE_BLOCK_CONFLICT | 30 | 26 | 86.7% |
| 楼栋确认 · 道路确认 · 邮编补全 · 有未识别文字 | 42 | 38 | 90.5% |
| 判 FIX：NO_MATCH | 122 | 116 | 95.1% |
| 楼栋补全 · 道路补全 · 邮编补全 · 楼宇名吻合 · 仅楼宇名 | 24 | 23 | 95.8% |
| 楼栋确认 · 道路确认 · 邮编补全 | 159 | 154 | 96.9% |
| 楼栋确认 · 道路确认 · 邮编替换 | 64 | 62 | 96.9% |
| 判 FIX：PREMISE_NOT_FOUND | 222 | 220 | 99.1% |
| 楼栋确认 · 道路确认 · 邮编确认 · 楼宇名吻合 | 597 | 593 | 99.3% |
| 楼栋确认 · 道路确认 · 邮编确认 | 4381 | 4367 | 99.7% |
| 楼栋替换 · 道路确认 · 邮编确认 | 45 | 45 | 100.0% |
| 楼栋确认 · 道路纠错 · 邮编确认 | 166 | 166 | 100.0% |
| 楼栋补全 · 道路补全 · 邮编确认 · 楼宇名吻合 | 20 | 20 | 100.0% |

### 新模型：最常见的结论类别

| 结论类别 | 训练单数 | 其中正确 | 实际正确率 |
|---|---|---|---|
| 楼栋确认 · 道路确认 · 邮编确认 | 4381 | 4367 | 99.7% |
| 楼栋确认 · 道路确认 · 邮编确认 · 楼宇名吻合 | 597 | 593 | 99.3% |
| 判 FIX：PREMISE_NOT_FOUND | 222 | 220 | 99.1% |
| 楼栋确认 · 道路纠错 · 邮编确认 | 166 | 166 | 100.0% |
| 楼栋确认 · 道路确认 · 邮编补全 | 159 | 154 | 96.9% |
| 判 FIX：NO_MATCH | 122 | 116 | 95.1% |
| 判 FIX：AMBIGUOUS_MULTIPLE_CANDIDATES | 80 | 80 | 100.0% |
| 判 FIX：OUT_OF_REGION | 72 | 72 | 100.0% |
| 楼栋确认 · 道路确认 · 邮编替换 | 64 | 62 | 96.9% |
| 楼栋替换 · 道路确认 · 邮编确认 | 45 | 45 | 100.0% |

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

**静默错误 · MISLEADING · POSTAL_OTHER_ADDRESS+AUTOFILL_WRONG**（2 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00780 | 106 Bukit Batok Central, #05-03 Ppis Child Development Centre - Bukit Batok, Singapore 650106 | ACCEPT | 106 BUKIT BATOK CENTRAL 650106 | 21 BUKIT BATOK EAST AVENUE 6 659759 |
| ORD-05429 | 94 Geylang Bahru, #09-06 Eight Riversuites, Singapore 330094 | ACCEPT | 94 GEYLANG BAHRU 330094 | 48 WHAMPOA EAST 338540 |

**静默错误 · MISLEADING · POSTAL_TYPO+AUTOFILL_WRONG+LOCATION_HINT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01152 | 57 Jansen Road, #01-12 lift lobby B, Singapore 548456 | ACCEPT | 57 JANSEN ROAD 548456 | 45C SIMON PLACE 544856 |

**静默错误 · RESOLVABLE · BLOCK_LETTER_DROPPED**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-02744 | Redhill Foods Pte. Ltd., Attn: Wendy Lau, #06-08 46 Lorong 32 Geylang, Bodhi Compassion Buddhist Centre, Singapore 398306 | ACCEPT | 46 LORONG 32 GEYLANG 398306 | 46A LORONG 32 GEYLANG 398306 |

**静默错误 · MISLEADING · BLOCK_LETTER_DROPPED+DUPLICATED_TEXT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-05685 | 45 Beach rOad, 01-20 45 Beach Road, Singapore, 189682 | ACCEPT | 45 BEACH ROAD 189682 | 45A BEACH ROAD 189682 |

**错误建议 · MISLEADING · POSTAL_MISSING+BLOCK_LETTER_DROPPED**（3 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01475 | blk 447 bukit batok w ave 9 #11-97 / to Ravi Shankar / Contact: +6584255078 | CONFIRM | 447 BUKIT BATOK WEST AVENUE 9 650447 | 447A BUKIT BATOK WEST AVENUE 9 651447 |
| ORD-04087 | Name: Nurul Huda, unit 16-313 blk 311 anchorvale lane, hp +6582822806 | CONFIRM | 311 ANCHORVALE LANE 540311 | 311D ANCHORVALE LANE 544311 |
| ORD-06567 | Name: Priscilla Goh UNIT 05-273 BLK 781 WOODLANDS AVE 9 hp 87550923 | CONFIRM | 781 WOODLANDS AVENUE 9 730781 | 781E WOODLANDS AVENUE 9 735781 |

**错误建议 · NO_ADDRESS · NO_ADDRESS**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-02831 | 0 | CONFIRM | 3 RESEARCH LINK 117602 | — |

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

**误拒 · RESOLVABLE · BUILDING_ONLY+POSTAL_MISSING**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00355 | Redhill Foods Pte. Ltd., Santa Grand Hotel East Coast B1-70 | FIX | — | 171 EAST COAST ROAD 428877 |

**误拒 · RESOLVABLE · POSTAL_TYPO**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01246 | Siglap Shopping Centre, 897 E Coast Rd. #03-18, 459120 | FIX | — | 897 EAST COAST ROAD 459100 |

**误拒 · RESOLVABLE · BLOCK_LETTER_DROPPED+TOWN_ABBREV**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-03633 | Block 228 PG Field #08-291, Singapore 821228 | FIX | — | 228A PUNGGOL FIELD 821228 |

**误拒 · RESOLVABLE · BLOCK_TYPO+STREET_TRUNCATED**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-03795 | BLK 626B TAMPINES NORTH DRI # 02-128, SINGAPORE, 522636 | FIX | — | 636B TAMPINES NORTH DRIVE 2 522636 |

**误拒 · RESOLVABLE · BUILDING_ONLY**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-07305 | Brightpath Education Pte Ltd, Tuas Bay Industrial Centre # 01-12, 637519 | FIX | — | 76 TUAS SOUTH AVENUE 2 637519 |

**误拒 · RESOLVABLE · POSTAL_TYPO+DUPLICATED_TEXT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-08916 | 10 MARINA BOULEVARD, #14-05 Marina Bay Financial Centre 10 Marina Boulevard, 018986 | FIX | — | 10 MARINA BOULEVARD 018983 |

**漏报 · RESOLVABLE · UNIT_MISSING**（109 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00045 | 62 KIM YAM ROAD, SINGAPORE, 239363 | ACCEPT | 62 KIM YAM ROAD 239363 | 62 KIM YAM ROAD 239363 |
| ORD-00046 | 32 jln limau nipis, 468285 | ACCEPT | 32 JALAN LIMAU NIPIS 468285 | 32 JALAN LIMAU NIPIS 468285 |
| ORD-00056 | 21 CHURCH ST, SINGAPORE, 049480 | ACCEPT | 21 CHURCH STREET 049480 | 21 CHURCH STREET 049480 |

**漏报 · RESOLVABLE · BUILDING_TYPO+UNIT_MISSING**（2 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-00913 | Name: Ravi Shankar 7 hindoo rd chern seng buliding s209108 Contact: 9879 0009 | ACCEPT | 7 HINDOO ROAD 209108 | 7 HINDOO ROAD 209108 |
| ORD-09052 | Name: Wendy Lau / 23 Yishun Cl Symphony Xuites S768015 | ACCEPT | 23 YISHUN CLOSE 768015 | 23 YISHUN CLOSE 768015 |

**漏报 · RESOLVABLE · UNIT_MISSING+DUPLICATED_TEXT**（2 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-01499 | 8 Miltonia Close, 8 miltonia close, Singapore 768190 | ACCEPT | 8 MILTONIA CLOSE 768190 | 8 MILTONIA CLOSE 768190 |
| ORD-02469 | 10 TANNERY LANE, BBS BUILDING, SINGAPORE, SINGAPORE, 347773 | ACCEPT | 10 TANNERY LANE 347773 | 10 TANNERY LANE 347773 |

**漏报 · RESOLVABLE · UNIT_MISSING+TOWN_ABBREV**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-03669 | Tan Wei Ming / 21 sbw cres 757053 / +65 8345 4490 | ACCEPT | 21 SEMBAWANG CRESCENT 757053 | 21 SEMBAWANG CRESCENT 757053 |

**漏报 · RESOLVABLE · BUILDING_TYPO+UNIT_MISSING+DUPLICATED_TEXT**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-06399 | 2 JL LYE KWEE, JUNILR PLAYWORLD CHILD CARE & DEVELOPMENT CENTRE, SINGAPORE, SINGAPORE, 537822 | ACCEPT | 2 JALAN LYE KWEE 537822 | 2 JALAN LYE KWEE 537822 |

**漏报 · RESOLVABLE · BLOCK_TYPO**（1 单）

| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|---|
| ORD-07980 | Block 227 Jurong E St 21, #11 - 73, Singapore, 600227 | ACCEPT | 227 JURONG EAST STREET 21 600227 | 227 JURONG EAST STREET 21 600227 |

