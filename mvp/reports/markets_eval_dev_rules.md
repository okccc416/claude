# 多市场评测报告（自动生成）

- 真实地址：各城市留出的 20% 商户（不在参考库里）的自填地址，标准答案为商户坐标（弱标注）
- 合成地址：按各市场写法渲染的测试部分道路（AI 解析器训练时没见过），标准答案已知
- 解析方式：rules = 规则 + 地名表；crf = 机器学习（条件随机场）；hybrid = 两者都出候选，由参考数据裁决

## 真实商户地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 600 | 73.5% | 3.7% | 1.0% | 14.8% | 4.5% | 2.5% | 85.8% | 2 |
| 德国（DE） | A | rules | 600 | 90.8% | 2.8% | 0.0% | 4.2% | 1.2% | 1.0% | 96.8% | 2 |
| 法国（FR） | A | rules | 600 | 86.3% | 3.0% | 0.3% | 7.8% | 0.5% | 2.0% | 95.8% | 1 |
| 荷兰（NL） | A | rules | 600 | 69.0% | 6.7% | 1.0% | 22.2% | 0.2% | 1.0% | 91.7% | 1 |
| 阿联酋（AE） | B | rules | 600 | 7.5% | 23.5% | 7.3% | 21.0% | 35.2% | 5.5% | 16.8% | 3 |
| 沙特（SA） | B | rules | 600 | 6.8% | 23.8% | 0.2% | 2.5% | 63.2% | 3.5% | 13.5% | 3 |
| 马来西亚（MY） | C | rules | 600 | 51.7% | 18.3% | 3.7% | 6.0% | 13.7% | 6.7% | 55.3% | 2 |
| 印尼（ID） | C | rules | 600 | 37.3% | 15.0% | 2.2% | 2.7% | 31.0% | 11.8% | 37.5% | 2 |
| 泰国（TH） | C | rules | 600 | 38.5% | 19.2% | 7.2% | 12.5% | 15.7% | 7.0% | 26.8% | 4 |
| 越南（VN） | C | rules | 600 | 15.8% | 45.0% | 1.3% | 4.3% | 27.7% | 5.8% | 43.7% | 1 |
| 菲律宾（PH） | C | rules | 600 | 32.8% | 19.8% | 15.8% | 9.2% | 17.8% | 4.5% | 37.3% | 3 |

## 合成地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 澳大利亚（AU） | A | rules | 600 | 81.3% | 8.7% | 0.0% | 4.8% | 4.2% | 1.0% | 95.7% | 1 |
| 德国（DE） | A | rules | 600 | 83.2% | 7.8% | 0.0% | 4.2% | 2.7% | 2.2% | 96.5% | 2 |
| 法国（FR） | A | rules | 600 | 85.3% | 5.5% | 0.0% | 7.7% | 1.5% | 0.0% | 97.8% | 1 |
| 荷兰（NL） | A | rules | 600 | 84.2% | 8.7% | 0.0% | 5.0% | 1.0% | 1.2% | 99.2% | 1 |
| 阿联酋（AE） | B | rules | 600 | 32.7% | 16.8% | 0.0% | 27.7% | 17.5% | 5.3% | 50.5% | 2 |
| 沙特（SA） | B | rules | 600 | 57.2% | 25.8% | 0.0% | 1.3% | 15.0% | 0.7% | 80.8% | 2 |
| 马来西亚（MY） | C | rules | 600 | 58.2% | 30.3% | 0.0% | 1.3% | 7.7% | 2.5% | 88.5% | 2 |
| 印尼（ID） | C | rules | 600 | 40.7% | 41.5% | 0.0% | 0.0% | 12.3% | 5.5% | 81.8% | 1 |
| 泰国（TH） | C | rules | 600 | 73.0% | 20.5% | 0.0% | 2.0% | 3.3% | 1.2% | 92.5% | 3 |
| 越南（VN） | C | rules | 600 | 55.8% | 34.3% | 0.0% | 0.7% | 8.0% | 1.2% | 90.0% | 2 |
| 菲律宾（PH） | C | rules | 600 | 59.5% | 24.3% | 0.0% | 4.7% | 10.3% | 1.2% | 82.8% | 2 |

## 错误样例（规则解析，真实地址）

**澳大利亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 141-151 Taren Point Rd Unit 13, Taren Point, 2229 | ACCEPT | PREMISE | UNIT 13, 141-151, Taren Point Road, Taren Point, 2229 |
| 1 Coggins Pl, Mascot, 2020 | CONFIRM_ADD_SUBPREMISES | PREMISE | 1, Coggins Place, Mascot, 2020 |
| 113 Railway St, Sydney, 2216 | ACCEPT | PREMISE | 113, Railway Street, Sydney, 2216 |
| 55 Crockford St, Port Melbourne, 3207 | ACCEPT | PREMISE | 55, Crockford Street, Port Melbourne, 3207 |

**澳大利亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Ground Level Chatswood Chase Shopping Centre outside entrance David Jones, Sydney, 2067 | FIX | ROUTE | GROUND FLOOR, Entrance, Sydney, 2067 |
| Keith Burrows Theatre, UNSW, Sydney, 2033 | FIX | LOCALITY |  |
| Shop/10 Rockdale Plaza Dr, Sydney, 2216 | FIX | ROUTE | SHOP 10, Rockdale Plaza Drive, Sydney, 2216 |
| 593-599 Old Illawarra Rd, Sydney, 2234 | FIX | ROUTE | 593-599, Old Illawarra Road, Sydney, 2234 |

**澳大利亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Cabramatta Rd, Cabramatta, 2166 | CONFIRM | ROUTE | Cabramatta Road, 2166 |
| 282 Oxford St Suite 202, Bondi Junction, 2022 | CONFIRM | PREMISE | SUITE 202, 282, Oxford Street, Bondi Junction, 2021 |
| Brushbox Drive, Melbourne, 3072 | CONFIRM | ROUTE | Brushbox Street, Melbourne, 3072 |
| 10 Lawson St, Sydney, 2115 | CONFIRM | PREMISE | 10, Lawson Street, Sydney, 2213 |

**德国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Heinrich-Hertz-Straße 3D, Kleinmachnow, 14532 | FIX | ROUTE | Heinrich-Hertz-Straße, 3D, Kleinmachnow, 14532 |
| Am Zwirngraben 6-7, Berlin, 10178 | FIX | ROUTE | Am Zwirngraben, 6-7, Berlin, 10178 |
| Leipziger Pl. 12-14, Berlin, 10117 | FIX | ROUTE | Leipziger Platz, 12-14, Berlin, 10117 |
| Kottbusser Damm 25-26, Berlin, 10967 | FIX | ROUTE | Kottbusser Damm, 25-26, 10967 |

**德国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Hauptbahnhof 1, Berlin, 10557 | CONFIRM | PREMISE | Bartningallee, 1, 10557 |
| Reischstrasse 13, Berlin, 14052 | CONFIRM | PREMISE | Reichsstraße, 13, 14052 |
| Schillerstr. 4, Berlin, 10625 | CONFIRM | PREMISE | Schillerstraße, 4, 14532 |
| Schwanebecker Ch 50, Berlin, 13125 | CONFIRM | PREMISE | Wolfgang-Heinz-Straße, 50, 13125 |

**德国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Turmstr. 21/Haus M, Berlin, 10559 | ACCEPT | PREMISE | Turmstraße, 21, 10559 |
| Unitb Consulting, Brunnenstraße 156, Berlin, 10115 | ACCEPT | PREMISE | Brunnenstraße, 156, Berlin, 10115 |
| Spenerstraße 15, Berlin, 10557 | ACCEPT | PREMISE | Spenerstraße, 15, 10557 |
| Hardenbergstraße 9a, Berlin, 10623 | ACCEPT | PREMISE | Hardenbergstraße, 9 A, 10623 |

**法国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 10 Rue de Sévigné, Paris, 75004 | FIX | ROUTE | 10, Rue de Sévigné, Paris, 75004 |
| 60 Rue François 1er, Paris, 75008 | FIX | ROUTE | 60, Rue François 1er, Paris, 75008 |
| 1 Cour du Havre, Paris, 75008 | FIX | ROUTE | 1, Cour du Havre, Paris, 75008 |
| Rue Viala, Paris, 75015 | FIX | ROUTE | Rue Viala, Paris, 75015 |

**法国 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Rives de Seine Habitat, 6 Rue Jacques Mazaud, Levallois-Perret, 92300 | ACCEPT | PREMISE | 6, Rue Jacques Mazaud, Levallois-Perret, 92300 |
| 6 place de Belgique, Courbevoie, 92400 | ACCEPT | PREMISE | 6, Place de Belgique, Courbevoie, 92400 |
| 6 Rue Rataud, Paris, 75005 | ACCEPT | PREMISE | 6, Rue Rataud, Paris, 75005 |
| Les Films du Cap, 20 Rue Oberkampf, Paris, 75011 | ACCEPT | PREMISE | 20, Rue Oberkampf, Paris, 75011 |

**法国 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Synthelabo Recherche, 31 Ave Paul Vaillant-Couturier, Bagneux, 92220 | CONFIRM | PREMISE | 31, Avenue Paul Vaillant-Couturier, 94250 |
| 15 Parv. de la Défense, Puteaux, 92800 | CONFIRM | PREMISE | 15, Place De La Défense, Puteaux, 92400 |
| 15 Parv. de la Défense, Puteaux, 92800 | CONFIRM | PREMISE | 15, Place De La Défense, Puteaux, 92400 |

**荷兰 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Bijlmerplein 89B, Amsterdam, 1102 DA | FIX | ROUTE | Bijlmerplein, 89B, Amsterdam, 1102DA |
| Wethouder Driessenstraat, Amsterdam | FIX | ROUTE | Wethouder Driessenstraat, Amsterdam |
| Ottho Heldringstraat 31n, Amsterdam, 1066 XT | FIX | ROUTE | Ottho Heldringstraat, 31N, Amsterdam, 1066XT |
| Joop Woortmanplein, Amsterdam, 1069 PT | FIX | ROUTE | Joop Woortmanplein, Amsterdam, 1069PT |

**荷兰 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Nico Broekhuysenweg 22, Amsterdam, 1067 HT | ACCEPT | PREMISE | Nico Broekhuysenweg, 22, Amsterdam, 1067HT |
| Herengracht 514, Amsterdam, 1017 CC | ACCEPT | PREMISE | Herengracht, 514, Amsterdam, 1017CC |
| V&d Buitenplein 101, Amstelveen, 1181 ZE | ACCEPT | PREMISE | Buitenplein, 101, Amstelveen, 1181ZE |
| Ingelandenweg 1, Amsterdam, 1069 WE | CONFIRM_ADD_SUBPREMISES | PREMISE | Ingelandenweg, 1, Amsterdam, 1069WE |

**荷兰 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Evert V/D Beekstraat 202, Luchthaven Schiphol, 1118 CP | CONFIRM | PREMISE | Evert van de Beekstraat, 202, Schiphol, 1118CP |

**阿联酋 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Sanctuary Tower - Office NO.105, دبي, 341296 | FIX | OTHER |  |
| Al Tawoon, الشارقة, 06 | FIX | LOCALITY |  |
| Grosvenor House, Dubai | FIX | LOCALITY |  |
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
| 10th St, دبي, 5280 DUBAI | ACCEPT | ROUTE | 5280, شارع 10, دبي |
| 28291 95853, شارع الخور, دبي | ACCEPT | ROUTE | شارع الخور |

**沙特 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Prince Muhammad Ibn Saad Ibn Abdulaziz Rd, الرياض, 13512 | CONFIRM | ROUTE | طريق الأمير محمد بن سعد بن عبدالعزيز, 13512 |
| حي بدر, الرياض, 14724 | CONFIRM | ROUTE | الرياض, 14724 |
| Prince Ahmad Bin Abdulaziz Street Riyadh, الرياض, 11461 | CONFIRM | ROUTE | Ahmad, 11461 |
| Ishbiliyah District, الرياض, 13226 | CONFIRM | ROUTE | الرياضة, 13226 |

**沙特 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Al Thoumamah Road 3178, الرياض, 13322 | ACCEPT | ROUTE | 3178, طريق الثمامة, 13322 |
| 6526 التخصصي, الرياض, 12332 | ACCEPT | ROUTE | 6526, التخصصي, 12332 |
| 2418 Al Olaya, Al Wurud, Riyadh, 12253 | ACCEPT | ROUTE | 2418, العليا, الورود, 12253 |
| المملكة العربية السعودية - الرياض - المربع - سوق السمك - ش الفالح بن صغير9151- شركة فتكر ل | ACCEPT | ROUTE | 9151, فالح بن الصغير, الرياض |

**沙特 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Riyadh Park-inside Debenhams, Riyadh | FIX | LOCALITY |  |
| localizer mall office number 10, riyadh, P.O Box 1491 | FIX | LOCALITY |  |
| Terminal 3, Riyadh | FIX | LOCALITY |  |
| Localizer Mall, Riyadh | FIX | LOCALITY |  |

**马来西亚 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| M3 Mall, Bandar Kuala Lumpur | CONFIRM | PREMISE_PROXIMITY | M3 Mall |
| Damansara Damai, Petaling Jaya | CONFIRM | ROUTE | Jalan Damansara, Petaling Jaya |
| no 22 jalan AU1A/4C Taman Keramat Permai, Ampang, 68000 | CONFIRM | ROUTE | 4C, Jalan Keramat, 68000 |
| Lembah Pantai, Petaling Jaya | CONFIRM | ROUTE | Jalan Pantai, Petaling Jaya |

**马来西亚 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| F-11-3, Pusat Bandar Bukit Jalil, Jalan Jalil Utama 2, 57000, Kuala Lumpur, Malaysia., Kua | ACCEPT | ROUTE | 11-3, Persiaran Jalil Utama, 57000 |
| 2 Jalan SS 4B/2, Petaling Jaya, 47301 | ACCEPT | ROUTE | 2, Jalan SS 4B/2, Petaling Jaya, 47301 |
| MELAWATI MALL, LOT L4-14(B) LEVEL 4, 355, Jln Bandar Melawati, Melawati, 53100 | ACCEPT | ROUTE | LEVEL 4, 355, Jalan Melawati, 53100 |
| 127 A, Jalan Damansara, Petaling Jaya, 60000 | ACCEPT | ROUTE | 127, Jalan Damansara, Petaling Jaya, 60000 |

**马来西亚 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| malaysia, Bandar Kuala Lumpur, 55100 | FIX | LOCALITY |  |
| Desa Business Centre, Kuala Lumpur, 58100 | FIX | LOCALITY |  |
| kepong sentral condominium, Bandar Kuala Lumpur, 52100 | FIX | LOCALITY |  |
| Oasis Square, Petaling Jaya, 47301 | FIX | LOCALITY |  |

**印尼 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Jl. Ir. H. Juanda No.3, RT.14/RW.4, Jakarta Pusat, 10120 | ACCEPT | ROUTE | Jalan N:O, 3, Jakarta Pusat, 10120 |
| Jl. Raya Bekasi No.KM 26, RW.5, Jakarta Timur, 13960 | ACCEPT | ROUTE | Jalan Raya Bekasi, 26, Jakarta Timur, 13960 |
| Jl. SMPN 207 No.77, RT.4/RW.8, Jakarta Barat, 11630 | ACCEPT | ROUTE | Jalan N:O, 77, Jakarta Barat, 11630 |
| Jl. Kamal Raya No.32 Blk C7, RT.6/RW.14, Jakarta Barat, 11730 | ACCEPT | ROUTE | Jalan Kamal Raya, 32, Jakarta Barat, 11730 |

**印尼 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Jalan M H Thamrin 28, Jakarta Pusat, 10350 | CONFIRM | ROUTE | MH Thamrin, 28, 10350 |
| Pusdiklat Kemenag RI Ciputat, Tangerang Selatan | CONFIRM | ROUTE | Jalan Tangerang |
| Jalan M H Thamrin 28, RT09/RW05, Gondangdia Kel., Menteng, Jakarta, 10350, Indonesia, Jaka | CONFIRM | ROUTE | MH Thamrin, 28, 10350 |
| Jl. Kenanga No.10 7, RT.7/RW.2, Jakarta Selatan, 12560 | CONFIRM | ROUTE | Jalan Kenanga, 10, Jakarta Selatan, 12560 |

**印尼 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| jakarta, Jakarta | FIX | LOCALITY |  |
| 14, RT.14/RW.3, Jakarta Selatan, 12520 | FIX | LOCALITY |  |
| Kompl Duta Mas Bl A-3/45, Jakarta Barat, 11720 | FIX | LOCALITY |  |
| Indonesia, Jakarta, 12740 | FIX | LOCALITY |  |

**泰国 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 69 Phra Ngoen Market, 8 Soi Wat Pra Nguen, บางใหญ่, 11140 | FIX | LOCALITY |  |
| 59 กลาง 1 Suphaphong Alley, กรุงเทพมหานคร, 10250 | FIX | LOCALITY |  |
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
| 21 Hoàng Diệu, Quận 4, 70000 | CONFIRM | ROUTE | 21, Hoàng Diệu |
| 51-49 Hồ Thị Kỷ, Phường 1, Quận 10, Thành phố Hồ Chí Minh, Việt Nam, Quận 5, 700000 | CONFIRM | ROUTE | 51-49, Hồ Thị Kỷ, 700000 |
| 71 Hoàng Hoa Thám, Quận Tân Bình, 72106 | CONFIRM | ROUTE | Hẻm 71 Đường Hoàng Hoa Thám |
| 3 Khu Đô Thị Geleximco Lê Trọng Tấn, Quận Hà Đông, 12114 | CONFIRM | ROUTE | 3, Lê Trọng Tấn |

**越南 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 642 Đ. Lê Đức Thọ, Quận Gò Vấp | ACCEPT | ROUTE | 642, Đường Lê Đức Thọ, Phường Gò Vấp |
| 963 Đường Phan Văn Trị, Quận Gò Vấp, 71407 | ACCEPT | ROUTE | 963, Đường Phan Văn Trị, Phường Gò Vấp |
| 178/23/4 Hẻm 178 Phan Đăng Lưu, Quận Phú Nhuận, 72213 | ACCEPT | ROUTE | 178/23/4, Hẻm 178 Phan Đăng Lưu, Phường Phú Nhuận |
| 177 Đ. Nguyễn Chí Thanh, Phường Chợ Lớn, Thành phố Hồ Chí Minh, Ho Chi Minh City, Vietnam, | ACCEPT | ROUTE | 177, Đường Nguyễn Chí Thanh, Phường Chợ Lớn |

**越南 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Phường Phước Long, Dĩ An, 700000 | FIX | LOCALITY |  |
| 458/41 Hẻm 458 Đường 3/2, Quận 10, 72510 | FIX | LOCALITY |  |
| P6-09, KDC PHI Long 5, Huyện Bình Chánh, 71812 | FIX | LOCALITY |  |
| 3 Đường 40, Thủ Đức, 50000 | FIX | LOCALITY |  |

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

