# 真实人写地址评测（自动生成）

- 样本：Overture places 中新加坡商户自填地址 8,000 条（按"地址 + 邮编"去重后随机抽样）；其中 7,939 条的真实地址在 2017 参考库里，61 条是参考库没有的新地址
- 标准答案：邮编在 2026 年官方地址表里只对应一个地址、且文字里的门牌 / 道路不与之矛盾的记录（弱标注）
- 来源构成：meta 7,148，Microsoft 405，Foursquare 391，AllThePlaces 50，PinMeTo 5，DAC 1

## 1. 总体

| 结果 | 带邮编 | 不带邮编 |
|---|---|---|
| 找对 · 直接通过 | 76.5%（6121） | 1.2%（94） |
| 找对 · 要求确认 | 21.4%（1711） | 92.3%（7388） |
| 判 FIX | 1.2%（98） | 4.5%（363） |
| 正确拒绝（参考库没有） | 0.7%（55） | 0.7%（55） |
| 错误建议 | 0.2%（15） | 1.2%（99） |
| 静默错误 | 0.0%（0） | 0.0%（1） |

"判 FIX"指真实地址在参考库里却没找到（相当于误拒）；"正确拒绝"指参考库里没有这个新地址、校验器判 FIX。

## 2. 按真实写法特征（带邮编，参考库里有的地址）

| 特征 | 条数 | 找对 | 其中直接通过 | 判 FIX | 错误建议 | 静默错误 |
|---|---|---|---|---|---|---|
| 门牌：一致 | 7,226 | 99.9% | 82.6% | 0.1% | 0.0% | 0.0% |
| 道路：缩写 | 5,241 | 99.8% | 80.8% | 0.2% | 0.0% | 0.0% |
| 带单元号 | 4,542 | 98.4% | 76.7% | 1.5% | 0.1% | 0.0% |
| 带楼宇名 | 2,831 | 98.0% | 84.3% | 1.8% | 0.2% | 0.0% |
| 道路：全称 | 2,273 | 99.7% | 82.4% | 0.2% | 0.0% | 0.0% |
| 地址前有楼宇 / 商户名 | 1,181 | 97.0% | 65.8% | 2.9% | 0.1% | 0.0% |
| 带 Blk 前缀 | 477 | 98.1% | 68.1% | 1.5% | 0.4% | 0.0% |
| 门牌：没写 | 474 | 80.0% | 2.1% | 19.6% | 0.4% | 0.0% |
| 道路：没写 / 认不出 | 344 | 75.9% | 2.3% | 22.7% | 1.5% | 0.0% |
| 门牌：写在别处（如道路后面的 Block 177） | 239 | 97.9% | 59.4% | 0.4% | 1.7% | 0.0% |
| 道路：拼错（可认出） | 81 | 93.8% | 4.9% | 3.7% | 2.5% | 0.0% |
| 夹杂中文 | 44 | 100.0% | 68.2% | 0.0% | 0.0% | 0.0% |

## 3. 错误样例

**带邮编 · 错误建议**（15 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| Woodlands Train Checkpoint, 11 Woodlands Xing, Singapore 738103 | CONFIRM | 11 WOODLANDS TERRACE 738436 | 11 WOODLANDS CROSSING 738103 |
| 71 Geylang Lorong 23 WPS805, Work+Store @ 71G, Singapore 388386 | CONFIRM | 71 GEYLANG ROAD 389194 | 71 LORONG 23 GEYLANG 388386 |
| 54 Genting Lane #05-01, Ruby Land Complex .blk 2, Singapore 349562 | CONFIRM | 2 RUBY LANE 328277 | 54 GENTING LANE 349562 |
| 10 Sin Ming Industrial Estate Sector C, #01 10, Singapore 575645 | CONFIRM | 10 SIN MING DRIVE 575701 | 10 SECTOR C SIN MING INDUSTRIAL ESTATE 575645 |
| 1 Tai Seng Ave #02-12, Tai Seng Dr, Tower A Exchange, Singapore 536464 | CONFIRM | 1 TAI SENG DRIVE 535215 | 1 TAI SENG AVENUE 536464 |
| Northumberland Road, 1号, Piccadilly Galleria, #01-03, Singapore 219568 | CONFIRM | 1 PICCADILLY 798364 | 1 NORTHUMBERLAND ROAD 219568 |

**带邮编 · 判 FIX**（98 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| Changi Airport Terminal 1, Departure/Transit Lounge East, Mezzanine, Level, #03-47/48 @SG Hawker Foodcourt, Singapore 819642 | FIX | — | 80 AIRPORT BOULEVARD 819642 |
| Level 11, Tower 1, Marina Bay Financial Centre, Singapore 018981 | FIX | — | 8 MARINA BOULEVARD 018981 |
| #03-05/06, Lot 1 Shoppers' Mall, Singapore 689812 | FIX | — | 21 CHOA CHU KANG AVENUE 4 689812 |
| #02-38/#02-56 CITY GATE MALL, Singapore 199597 | FIX | — | 371 BEACH ROAD 199597 |
| 391A Orchard Road, Ngee Ann City Tower A Takashimaya Department Store Stall No.3 Food Village Basement 2, Singapore 238873 | FIX | — | 391A ORCHARD ROAD 238873 |
| #01-28/29 DUO Galleria, Singapore 189356 | FIX | — | 7 FRASER STREET 189356 |

**不带邮编 · 静默错误**（1 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| 4190 Broadway Plaza 569841, 01-07 Ang Mo Kio Ave 6 | ACCEPT | 4190 ANG MO KIO AVENUE 6 569841 | 716 ANG MO KIO AVENUE 6 560716 |

**不带邮编 · 错误建议**（99 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| 13 N Bridge Rd, #01-3972 Golden Beach Vista | CONFIRM | 13 NEW BRIDGE ROAD 059384 | 13 NORTH BRIDGE ROAD 190013 |
| 391A Orchard Road, Ngee Ann City Tower A Takashimaya Department Store Stall No.3 Food Village Basement 2 | CONFIRM | 3 ORCHARD ROAD 238825 | 391A ORCHARD ROAD 238873 |
| Woodlands Train Checkpoint, 11 Woodlands Xing | CONFIRM | 11 WOODLANDS TERRACE 738436 | 11 WOODLANDS CROSSING 738103 |
| 71 Geylang Lorong 23 WPS805, Work+Store @ 71G | CONFIRM | 71 GEYLANG ROAD 389194 | 71 LORONG 23 GEYLANG 388386 |
| 54 Genting Lane #05-01, Ruby Land Complex .blk 2 | CONFIRM | 2 RUBY LANE 328277 | 54 GENTING LANE 349562 |
| Win 5, 15 Yishun Ind St 1 | CONFIRM | 5 YISHUN INDUSTRIAL STREET 1 768161 | 15 YISHUN INDUSTRIAL STREET 1 768091 |

**不带邮编 · 判 FIX**（363 条，列出前 6 条）

| 输入 | 结论 | 给出的地址 | 真实地址 |
|---|---|---|---|
| #01-K3, Bugis Junction | FIX | — | 200 VICTORIA STREET 188021 |
| Bedok Reservoir Rd, #01-3516 | FIX | — | 703 BEDOK RESERVOIR ROAD 470703 |
| Changi Airport Terminal 1, Departure/Transit Lounge East, Mezzanine, Level, #03-47/48 @SG Hawker Foodcourt | FIX | — | 80 AIRPORT BOULEVARD 819642 |
| #02-39, Singapore Changi Airport (Terminal 1) | FIX | — | 80 AIRPORT BOULEVARD 819642 |
| #01-572 Lor. 5 Toa Payoh, #01-572 | FIX | — | 72 LORONG 5 TOA PAYOH 310072 |
| 52 Chin Swee Rd, #03-27 | FIX | — | 52 CHIN SWEE ROAD 160052 |

