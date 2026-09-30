# 多市场评测报告（自动生成）

- 真实地址：各城市留出的 20% 商户（不在参考库里）的自填地址，标准答案为商户坐标（弱标注）
- 合成地址：按各市场写法渲染的测试部分道路（AI 解析器训练时没见过），标准答案已知
- 解析方式：rules = 规则 + 地名表；crf = 机器学习（条件随机场）；hybrid = 两者都出候选，由参考数据裁决
- 判对标准（真实地址）：门牌级 ≤ 250 米、楼宇级 ≤ 400 米、道路级为该道路经过商户 250 米内；"偏差 >1 公里"的静默错误不是商户坐标不准能解释的，是真正的错

## 真实商户地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 阿联酋（AE） | B | rules | 600 | 7.5% | 24.0% | 11.8% | 25.0% | 27.2% | 4.5% | 3.2% | 18.2% | 3 |
| 沙特（SA） | B | rules | 600 | 7.3% | 22.8% | 11.3% | 14.3% | 41.7% | 2.5% | 2.5% | 16.2% | 2 |
| 印尼（ID） | C | rules | 600 | 37.2% | 16.3% | 2.3% | 4.2% | 30.8% | 9.2% | 3.7% | 38.7% | 2 |
| 泰国（TH） | C | rules | 600 | 38.3% | 19.2% | 11.5% | 8.3% | 15.7% | 7.0% | 3.2% | 27.7% | 5 |
| 越南（VN） | C | rules | 600 | 16.8% | 45.3% | 2.0% | 4.5% | 25.7% | 5.7% | 3.8% | 48.0% | 1 |
| 马来西亚（MY） | C | rules | 600 | 51.3% | 17.0% | 4.7% | 6.5% | 12.8% | 7.7% | 4.0% | 54.3% | 2 |
| 菲律宾（PH） | C | rules | 600 | 32.8% | 19.8% | 16.2% | 9.7% | 17.0% | 4.5% | 2.7% | 37.3% | 3 |

## 合成地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 阿联酋（AE） | B | rules | 600 | 33.7% | 17.2% | 0.0% | 31.3% | 16.3% | 1.5% | 0.5% | 52.3% | 2 |
| 沙特（SA） | B | rules | 600 | 50.2% | 26.5% | 0.0% | 6.7% | 15.8% | 0.8% | 0.3% | 75.3% | 2 |
| 印尼（ID） | C | rules | 600 | 53.3% | 33.7% | 0.0% | 0.7% | 11.0% | 1.3% | 1.2% | 87.0% | 1 |
| 泰国（TH） | C | rules | 600 | 71.8% | 22.3% | 0.0% | 2.0% | 2.8% | 1.0% | 0.5% | 93.0% | 3 |
| 越南（VN） | C | rules | 600 | 60.5% | 30.3% | 0.0% | 0.8% | 7.7% | 0.7% | 0.3% | 90.7% | 2 |
| 马来西亚（MY） | C | rules | 600 | 62.2% | 27.8% | 0.0% | 1.5% | 6.8% | 1.7% | 1.2% | 89.8% | 2 |
| 菲律宾（PH） | C | rules | 600 | 59.5% | 23.8% | 0.0% | 5.0% | 10.7% | 1.0% | 1.0% | 82.5% | 2 |

## 错误样例（规则解析，真实地址）

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
| Al Hammadi 01, Ras Al Khor Industrial First, دبي | CONFIRM | ROUTE | 01, شارع رأس الخور |
| 27/2 10th St, دبي | CONFIRM | ROUTE | 27/2, شارع 10 |
| Saraya Cafe & Roasters SHJ Warehouses Land Service Road Industrial Area 18, Sharjah, 14053 | CONFIRM | ROUTE | 18, Service Road |
| Ground Floor، Auto Center Building - Showroom#5 - Office #105 22A St, دبي, 22542 | CONFIRM | ROUTE | #105, 22a شارع |

**阿联酋 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 31394 97957, شارع الحمرية, دبي | ACCEPT | ROUTE | شارع الحمرية |
| Opposite Deira Palace Hotel, 107 Sikkat Al Khail St, Deira, Dubai, UAE, دبي | ACCEPT | ROUTE | 107, طريق سكة الخيل, ديرة |
| 28291 95853, شارع الخور, دبي | ACCEPT | ROUTE | شارع الخور |
| 24965 90410, شارع الوصل 35, دبي | ACCEPT | ROUTE | 35, شارع الوصل |

**沙特 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Prince Muhammad Ibn Saad Ibn Abdulaziz Rd, الرياض, 13512 | CONFIRM | ROUTE | طريق الأمير محمد بن سعد بن عبدالعزيز, 13512 |
| Prince Ahmad Bin Abdulaziz Street Riyadh, الرياض, 11461 | CONFIRM | ROUTE | Ahmad, 11461 |
| Saeed Bin Zaid St, الرياض | CONFIRM | ROUTE | سعيد بن زيد |
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
| Al Thoumamah Road 3178, الرياض, 13322 | ACCEPT | ROUTE | 3178, طريق الثمامة, 13322 |
| 6526 التخصصي, الرياض, 12332 | ACCEPT | ROUTE | 6526, التخصصي, 12332 |
| HH6V+683، العوالي، الرياض 14926، المملكة العربية السعودية, الرياض, 14926 | ACCEPT | PREMISE_PROXIMITY | 14926 |
| 2418 Al Olaya, Al Wurud, Riyadh, 12253 | ACCEPT | ROUTE | 2418, العليا, الورود, 12253 |

**印尼 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Jl. Raya Bekasi No.KM 26, RW.5, Jakarta Timur, 13960 | ACCEPT | ROUTE | Jalan Raya Bekasi, 26, Jakarta Timur, 13960 |
| Jl. Kamal Raya No.32 Blk C7, RT.6/RW.14, Jakarta Barat, 11730 | ACCEPT | ROUTE | Jalan Kamal Raya, 32, Jakarta Barat, 11730 |
| Jl. Enim 2 No.87, RT.3/RW.3, Jakarta Utara, 14330 | ACCEPT | ROUTE | Jalan Enim, 2, Jakarta Utara, 14330 |
| Jalan Senopati 8B, Jakarta, 12190 | ACCEPT | ROUTE | Jalan Senopati, 8B, 12190 |

**印尼 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Jalan M H Thamrin 28, Jakarta Pusat, 10350 | CONFIRM | ROUTE | MH Thamrin, 28, 10350 |
| Pusdiklat Kemenag RI Ciputat, Tangerang Selatan | CONFIRM | ROUTE | Jalan Tangerang |
| Jalan M H Thamrin 28, RT09/RW05, Gondangdia Kel., Menteng, Jakarta, 10350, Indonesia, Jaka | CONFIRM | ROUTE | MH Thamrin, 28, 10350 |
| Jl. SMPN 207 No.77, RT.4/RW.8, Jakarta Barat, 11630 | CONFIRM | ROUTE | Jalan SMPN 45, 77, Jakarta Barat, 11630 |

**印尼 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| jakarta, Jakarta | FIX | OTHER |  |
| Jl. Hii No.1, RT.7/RW.4, Jakarta Utara, 14240 | FIX | LOCALITY |  |
| 14, RT.14/RW.3, Jakarta Selatan, 12520 | FIX | LOCALITY |  |
| Kompl Duta Mas Bl A-3/45, Jakarta Barat, 11720 | FIX | LOCALITY |  |

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
| ร้านลักชูรี่ เนลล์ บายนุ่น 43/5หมู่3 หน้าตลาดมนวดี ติดกับห้างทองศรสุวรรณ 2 ต.พิมลราช, บางบ | CONFIRM | ROUTE | 3, ซอยสุวรรณ, 11110 |
| กาญจนาภิเษก, นนทบุรี, 11110 | CONFIRM | ROUTE | ถนนกาญจนาภิเษก, 11110 |
| 101 สุขุมวิท, กรุงเทพมหานคร, 10260 | CONFIRM | ROUTE | 101, สุขุมวิท 7, 10260 |
| ถนนจันทน์ 28 แขวงทุ่งวัดดอน สาทร, กรุงเทพมหานคร, 10120 | CONFIRM | ROUTE | ซอยจันทน์ 28, แขวงทุ่งวัดดอน, 10120 |

**泰国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 393 หมู่ที่9, ถนนประชาอุทิศ, กรุงเทพมหานคร, 10140 | ACCEPT | ROUTE | 393, ถนนประชาอุทิศ, 10140 |
| 69 ถนน ประชาอุทิศ, กรุงเทพมหานคร, 10140 | ACCEPT | ROUTE | 69, ถนนประชาอุทิศ, 10140 |
| ปาก Tha Din Daeng 12, กรุงเทพมหานคร, 10600 | ACCEPT | ROUTE | 12, ท่าดินแดง 1, ท่าดินแดง, 10600 |
| 3 ซอย พหลโยธิน 54/1, สายไหม, 10220 | ACCEPT | ROUTE | 3, ซอย พหลโยธิน 54/1, สายไหม, 10220 |

**越南 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 21 Hoàng Diệu, Quận 4, 70000 | CONFIRM | ROUTE | 21, Hoàng Diệu, 70000 |
| 51-49 Hồ Thị Kỷ, Phường 1, Quận 10, Thành phố Hồ Chí Minh, Việt Nam, Quận 5, 700000 | CONFIRM | ROUTE | 51-49, Hồ Thị Kỷ, 700000 |
| 71 Hoàng Hoa Thám, Quận Tân Bình, 72106 | CONFIRM | ROUTE | Hẻm 71 Đường Hoàng Hoa Thám, 72106 |
| 3 Khu Đô Thị Geleximco Lê Trọng Tấn, Quận Hà Đông, 12114 | CONFIRM | ROUTE | 3, Lê Trọng Tấn, 12114 |

**越南 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 642 Đ. Lê Đức Thọ, Quận Gò Vấp | ACCEPT | ROUTE | 642, Đường Lê Đức Thọ, Phường Gò Vấp |
| 963 Đường Phan Văn Trị, Quận Gò Vấp, 71407 | ACCEPT | ROUTE | 963, Đường Phan Văn Trị, Phường Gò Vấp, 71407 |
| 178/23/4 Hẻm 178 Phan Đăng Lưu, Quận Phú Nhuận, 72213 | ACCEPT | ROUTE | 178/23/4, Hẻm 178 Phan Đăng Lưu, Phường Phú Nhuận, 72213 |
| 177 Đ. Nguyễn Chí Thanh, Phường Chợ Lớn, Thành phố Hồ Chí Minh, Ho Chi Minh City, Vietnam, | ACCEPT | ROUTE | 177, Đường Nguyễn Chí Thanh, Phường Chợ Lớn, 70000 |

**越南 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Phường Phước Long, Dĩ An, 700000 | FIX | LOCALITY |  |
| 458/41 Hẻm 458 Đường 3/2, Quận 10, 72510 | FIX | LOCALITY |  |
| P6-09, KDC PHI Long 5, Huyện Bình Chánh, 71812 | FIX | LOCALITY |  |
| 3 Đường 40, Thủ Đức, 50000 | FIX | LOCALITY |  |

**马来西亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| M3 Mall, Bandar Kuala Lumpur | CONFIRM | PREMISE_PROXIMITY | M3 Mall |
| Damansara Damai, Petaling Jaya | CONFIRM | ROUTE | Jalan Damansara, Petaling Jaya |
| no 22 jalan AU1A/4C Taman Keramat Permai, Ampang, 68000 | CONFIRM | ROUTE | 4C, Jalan Keramat, 68000 |
| Lembah Pantai, Petaling Jaya | CONFIRM | ROUTE | Jalan Lembah, Petaling Jaya |

**马来西亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| F-11-3, Pusat Bandar Bukit Jalil, Jalan Jalil Utama 2, 57000, Kuala Lumpur, Malaysia., Kua | ACCEPT | ROUTE | 11-3, Persiaran Jalil Utama, 57000 |
| 2 Jalan SS 4B/2, Petaling Jaya, 47301 | ACCEPT | ROUTE | 2, Jalan SS 4B/2, Petaling Jaya, 47301 |
| 127 A, Jalan Damansara, Petaling Jaya, 60000 | ACCEPT | ROUTE | 127, Jalan Damansara, Petaling Jaya, 60000 |
| 1,Jalan Pandan Indah, Pandan Indah, 55100 | ACCEPT | ROUTE | 1, Jalan Indah, Kampung Pandan, 55100 |

**马来西亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| The Square @ One City, Jalan USJ 25/1C, Subang Jaya, 47650 | FIX | LOCALITY |  |
| malaysia, Bandar Kuala Lumpur, 55100 | FIX | LOCALITY |  |
| Desa Business Centre, Kuala Lumpur, 58100 | FIX | LOCALITY |  |
| kepong sentral condominium, Bandar Kuala Lumpur, 52100 | FIX | LOCALITY |  |

**菲律宾 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Office no 415, 417 4/F Unit 4 C&D Commerce and Industry Plaza Building, Taguig, 1634 | CONFIRM | PREMISE_PROXIMITY | UNIT 4, Commerce and Industry Plaza, 415, 1634 |
| 720 B Bulacan St, Manila, 002 | CONFIRM | ROUTE | 720, Bulacan Street, Manila |
| 53 Anonas, Quezon City, 1102 | CONFIRM | ROUTE | 53, Anonas, Quezon City, 1102 |
| Provident Vill, 170 Cambridge, Marikina, 1804 | CONFIRM | ROUTE | 170, Cambridge, 1804 |

**菲律宾 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Sampaloc Manila, Manila | FIX | LOCALITY |  |
| Two E-com Bldg, Pasay City, 1300 | FIX | LOCALITY |  |
| Manila, Manila, <<not-applicable>> | FIX | LOCALITY |  |
| Tomas Arguelles 53, Quezon City, 1113 | FIX | LOCALITY |  |

**菲律宾 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 486 Lt. Artiaga, San Juan, 1500 | ACCEPT | ROUTE | 486, Artiaga, San Juan, 1500 |
| 303 building tullahan road, tandang sora extention, Santa Quiteria Rd, Caloocan City, 1402 | ACCEPT | ROUTE | 303, Santa Quiteria Road, Caloocan, 1402 |
| 537 J Fabella St, Mandaluyong, 1550 | ACCEPT | ROUTE | 537, J. Fabella Street, Mandaluyong, 1550 |
| 2521 a Isagani St, Bgy 370, Zone 037 STA Cruz, Manila, Manila, 1113 | ACCEPT | ROUTE | 2521, Isagani Street, Santa Cruz, 1113 |

