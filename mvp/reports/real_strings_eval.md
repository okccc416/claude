# 真实人写地址评测（自动生成）

- 样本：Overture places 中新加坡商户自填地址 8,000 条（按"地址 + 邮编"去重后随机抽样）；其中 7,999 条的真实地址在 2026 参考库里，1 条是参考库没有的新地址
- 标准答案：邮编在 2026 年官方地址表里只对应一个地址、且文字里的门牌 / 道路不与之矛盾的记录（弱标注）
- 来源构成：meta 7,148，Microsoft 405，Foursquare 391，AllThePlaces 50，PinMeTo 5，DAC 1

## 1. 总体

| 结果 | 带邮编 | 不带邮编 |
|---|---|---|
| 找对 · 直接通过 | 85.9%（6875） | 1.3%（102） |
| 找对 · 要求确认 | 13.3%（1064） | 93.2%（7453） |
| 判 FIX | 0.7%（57） | 4.6%（370） |
| 正确拒绝（参考库没有） | 0.0%（1） | 0.0%（1） |
| 错误建议 | 0.0%（3） | 0.9%（73） |
| 静默错误 | 0.0%（0） | 0.0%（1） |

"判 FIX"指真实地址在参考库里却没找到（相当于误拒）；"正确拒绝"指参考库里没有这个新地址、校验器判 FIX。

## 2. 按真实写法特征（带邮编，参考库里有的地址）

| 特征 | 条数 | 找对 | 其中直接通过 | 判 FIX | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|
| 门牌：一致 | 7,282 | 99.9% | 92.0% | 0.0% | 0.0% | 0.0% |
| 道路：缩写 | 5,275 | 99.8% | 91.5% | 0.2% | 0.0% | 0.0% |
| 带单元号 | 4,574 | 99.3% | 87.2% | 0.7% | 0.0% | 0.0% |
| 带楼宇名 | 2,850 | 99.3% | 86.9% | 0.7% | 0.0% | 0.0% |
| 道路：全称 | 2,293 | 99.9% | 88.4% | 0.1% | 0.0% | 0.0% |
| 地址前有楼宇 / 商户名 | 1,189 | 97.5% | 69.2% | 2.5% | 0.0% | 0.0% |
| 带 Blk 前缀 | 480 | 98.8% | 89.4% | 1.0% | 0.2% | 0.0% |
| 门牌：没写 | 476 | 88.2% | 2.5% | 11.3% | 0.4% | 0.0% |
| 道路：没写 / 认不出 | 346 | 87.0% | 4.9% | 12.4% | 0.6% | 0.0% |
| 门牌：写在别处（如道路后面的 Block 177） | 241 | 100.0% | 69.3% | 0.0% | 0.0% | 0.0% |
| 道路：拼错（可认出） | 85 | 96.5% | 5.9% | 3.5% | 0.0% | 0.0% |
| 夹杂中文 | 45 | 100.0% | 82.2% | 0.0% | 0.0% | 0.0% |

## 3. 错误样例

**带邮编 · 错误建议**（3 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| 53 Ubi Cr, Singapore 408653 | CONFIRM | 53 UBI CRESCENT 408594 | 3025 UBI ROAD 3 408653 |
| 9 Temasek Boulvard, Suntec Tower Two,#07-01, Singapore 048943 | CONFIRM | 9 TEMASEK BOULEVARD 038989 | 137 MARKET STREET 048943 |
| 11 Jln Ubi, #01-51 Kembangan Chai Chee Community Hub, Block 6, Singapore 409074 | CONFIRM | 6 JALAN KEMBANGAN 419164 | 11 JALAN UBI 409074 |

**带邮编 · 判 FIX**（57 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| Changi Airport Terminal 1, Departure/Transit Lounge East, Mezzanine, Level, #03-47/48 @SG Hawker Foodcourt, Singapore 819642 | FIX | — | 80 AIRPORT BOULEVARD 819642 |
| Level 11, Tower 1, Marina Bay Financial Centre, Singapore 018981 | FIX | — | 8 MARINA BOULEVARD 018981 |
| #03-05/06, Lot 1 Shoppers' Mall, Singapore 689812 | FIX | — | 21 CHOA CHU KANG AVENUE 4 689812 |
| 391A Orchard Road, Ngee Ann City Tower A Takashimaya Department Store Stall No.3 Food Village Basement 2, Singapore 238873 | FIX | — | 391A ORCHARD ROAD 238873 |
| #01-29 Kallang Wave, Singapore 397691 | FIX | — | 2 STADIUM WALK 397691 |
| #B1-51C AMK Hub, Singapore 569933 | FIX | — | 53 ANG MO KIO AVENUE 3 569933 |

**不带邮编 · 静默错误**（1 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| 4190 Broadway Plaza 569841, 01-07 Ang Mo Kio Ave 6 | ACCEPT | 4190 ANG MO KIO AVENUE 6 569841 | 716 ANG MO KIO AVENUE 6 560716 |

**不带邮编 · 错误建议**（73 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| Terminal 1 Changi Airport | CONFIRM | 80 AIRPORT BOULEVARD 819642 | 65 AIRPORT BOULEVARD 819663 |
| 391A Orchard Road, Ngee Ann City Tower A Takashimaya Department Store Stall No.3 Food Village Basement 2 | CONFIRM | 3 ORCHARD ROAD 238825 | 391A ORCHARD ROAD 238873 |
| 71 Geylang Lorong 23 WPS805, Work+Store @ 71G | CONFIRM | 71 GEYLANG ROAD 389194 | 71 LORONG 23 GEYLANG 388386 |
| 54 Genting Lane #05-01, Ruby Land Complex .blk 2 | CONFIRM | 2 RUBY LANE 328277 | 54 GENTING LANE 349562 |
| Win 5, 15 Yishun Ind St 1 | CONFIRM | 5 YISHUN INDUSTRIAL STREET 1 768161 | 15 YISHUN INDUSTRIAL STREET 1 768091 |
| 15 Changi North Street 1, #01-13 i-lofts@changi | CONFIRM | 15 CHANGI SOUTH STREET 1 486783 | 15 CHANGI NORTH STREET 1 498765 |

**不带邮编 · 判 FIX**（370 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| Bedok Reservoir Rd, #01-3516 | FIX | — | 703 BEDOK RESERVOIR ROAD 470703 |
| Changi Airport Terminal 1, Departure/Transit Lounge East, Mezzanine, Level, #03-47/48 @SG Hawker Foodcourt | FIX | — | 80 AIRPORT BOULEVARD 819642 |
| #01-572 Lor. 5 Toa Payoh, #01-572 | FIX | — | 72 LORONG 5 TOA PAYOH 310072 |
| 52 Chin Swee Rd, #03-27 | FIX | — | 52 CHIN SWEE ROAD 160052 |
| Level 11, Tower 1, Marina Bay Financial Centre | FIX | — | 8 MARINA BOULEVARD 018981 |
| 34 Upper Cross St | FIX | — | 34 UPPER CROSS STREET 050034 |

