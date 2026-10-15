# 多市场评测报告（自动生成）

- 真实地址：各城市留出的 20% 商户（不在参考库里）的自填地址，标准答案为商户坐标（弱标注）
- 合成地址：按各市场写法渲染的测试部分道路（AI 解析器训练时没见过），标准答案已知
- 解析方式：rules = 规则 + 地名表；crf = 机器学习（条件随机场）；hybrid = 两者都出候选，由参考数据裁决
- 判对标准（真实地址）：门牌级 ≤ 250 米、楼宇级 ≤ 400 米、道路级为该道路经过商户 250 米内；"偏差 >1 公里"的静默错误不是商户坐标不准能解释的，是真正的错

## 真实商户地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 科威特（KW） | B | rules | 1000 | 2.6% | 24.4% | 23.1% | 25.6% | 23.5% | 0.8% | 0.6% | 23.2% | 9 |
| 科威特（KW） | B | crf | 1000 | 1.3% | 17.0% | 15.6% | 53.2% | 12.1% | 0.8% | 0.7% | 14.1% | 5 |
| 科威特（KW） | B | hybrid | 1000 | 2.6% | 25.1% | 21.3% | 24.6% | 25.6% | 0.8% | 0.6% | 23.9% | 10 |
| 巴林（BH） | B | rules | 921 | 0.7% | 31.7% | 20.8% | 6.6% | 40.0% | 0.2% | 0.2% | 30.3% | 7 |
| 巴林（BH） | B | crf | 921 | 0.5% | 21.1% | 5.4% | 43.0% | 29.5% | 0.4% | 0.4% | 21.0% | 3 |
| 巴林（BH） | B | hybrid | 921 | 0.7% | 34.4% | 18.1% | 5.6% | 40.9% | 0.2% | 0.2% | 32.7% | 8 |
| 埃及（EG） | B | rules | 1000 | 0.9% | 25.7% | 5.0% | 7.5% | 60.6% | 0.3% | 0.3% | 25.8% | 32 |
| 埃及（EG） | B | crf | 1000 | 0.3% | 17.9% | 19.4% | 33.3% | 29.0% | 0.1% | 0.0% | 22.4% | 14 |
| 埃及（EG） | B | hybrid | 1000 | 0.9% | 26.0% | 4.8% | 6.9% | 61.1% | 0.3% | 0.3% | 26.2% | 35 |
| 哈萨克斯坦（KZ） | C | rules | 1000 | 6.6% | 44.9% | 2.9% | 8.3% | 36.7% | 0.6% | 0.3% | 28.8% | 7 |
| 哈萨克斯坦（KZ） | C | crf | 1000 | 6.0% | 38.6% | 8.6% | 16.2% | 30.3% | 0.3% | 0.1% | 25.9% | 4 |
| 哈萨克斯坦（KZ） | C | hybrid | 1000 | 6.6% | 45.6% | 2.6% | 7.8% | 36.8% | 0.6% | 0.3% | 29.5% | 11 |
| 多米尼加（DO） | C | rules | 1000 | 12.4% | 36.5% | 1.7% | 6.0% | 40.2% | 3.2% | 2.3% | 39.7% | 10 |
| 多米尼加（DO） | C | crf | 1000 | 10.3% | 33.1% | 8.5% | 19.6% | 26.1% | 2.4% | 1.5% | 36.5% | 6 |
| 多米尼加（DO） | C | hybrid | 1000 | 12.5% | 37.6% | 1.5% | 5.6% | 39.6% | 3.2% | 2.3% | 39.7% | 14 |

## 合成地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 科威特（KW） | B | rules | 1000 | 3.9% | 46.8% | 0.0% | 17.3% | 32.0% | 0.0% | 0.0% | 53.8% | 9 |
| 科威特（KW） | B | crf | 1000 | 4.0% | 45.4% | 0.0% | 17.6% | 33.0% | 0.0% | 0.0% | 52.0% | 8 |
| 科威特（KW） | B | hybrid | 1000 | 4.4% | 48.1% | 0.0% | 15.2% | 32.3% | 0.0% | 0.0% | 55.2% | 14 |
| 巴林（BH） | B | rules | 1000 | 2.0% | 50.5% | 0.0% | 6.7% | 40.8% | 0.0% | 0.0% | 54.0% | 4 |
| 巴林（BH） | B | crf | 1000 | 3.7% | 57.5% | 0.0% | 1.4% | 37.4% | 0.0% | 0.0% | 61.3% | 3 |
| 巴林（BH） | B | hybrid | 1000 | 3.1% | 55.0% | 0.0% | 0.7% | 41.2% | 0.0% | 0.0% | 58.6% | 7 |
| 埃及（EG） | B | rules | 1000 | 12.0% | 58.0% | 0.0% | 0.6% | 29.3% | 0.1% | 0.0% | 70.6% | 10 |
| 埃及（EG） | B | crf | 1000 | 13.8% | 69.6% | 0.0% | 2.0% | 14.6% | 0.0% | 0.0% | 83.1% | 7 |
| 埃及（EG） | B | hybrid | 1000 | 14.0% | 57.6% | 0.0% | 0.4% | 27.9% | 0.1% | 0.0% | 72.3% | 16 |
| 哈萨克斯坦（KZ） | C | rules | 1000 | 6.7% | 75.9% | 0.0% | 1.2% | 16.1% | 0.1% | 0.0% | 73.2% | 4 |
| 哈萨克斯坦（KZ） | C | crf | 1000 | 7.5% | 75.7% | 0.0% | 0.4% | 16.3% | 0.1% | 0.0% | 75.3% | 3 |
| 哈萨克斯坦（KZ） | C | hybrid | 1000 | 7.7% | 77.6% | 0.0% | 0.0% | 14.6% | 0.1% | 0.0% | 75.0% | 5 |
| 多米尼加（DO） | C | rules | 1000 | 10.5% | 46.2% | 0.0% | 0.8% | 42.4% | 0.1% | 0.0% | 53.9% | 8 |
| 多米尼加（DO） | C | crf | 1000 | 12.7% | 49.2% | 0.0% | 0.4% | 37.7% | 0.0% | 0.0% | 58.6% | 6 |
| 多米尼加（DO） | C | hybrid | 1000 | 12.4% | 48.0% | 0.0% | 0.0% | 39.6% | 0.0% | 0.0% | 57.3% | 12 |

## 错误样例（规则解析，真实地址）

**科威特 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Alsalam, حولى | FIX | OTHER |  |
| AlThajeej, الفروانية | FIX | OTHER |  |
| الشاميه، قطعة ٩, مدينة الكويت | FIX | LOCALITY | حولي, الكويت |
| Road 602, الفروانية | FIX | OTHER | 602 Road, الكويت |

**科威特 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Hawalli, Al-Naqrah, Block 10, Plot 7202, Street 219, حولى | CONFIRM | ROUTE | Block 10, 7202 Street 219, Ḩawallī, الكويت |
| Hamad Al-Zuwayer Street, الأحمدى | CONFIRM | ROUTE | Hamad Al Zuwayer Street, الأحمدي, الكويت |
| 800001 Faris Abdulrahman Al Waqayan St, Zahra | CONFIRM | ROUTE | Al-Zahra'a Street, Ḩawallī, Kuwait |
| 11 2 St. 1 Ln, حولى, 3000 | CONFIRM | PREMISE | 2 شارع 1, الفروانية, الكويت |

**科威特 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Etihad medical centre,Amman Street,Salmiya, حولى, 32771 | ACCEPT | PREMISE_PROXIMITY | Etihad Medical Centre, Amman Street, 32771 حولي, الكويت |
| 1873 Sheikh Zayed Bin Sultan Al Nahyan Rd, الجهراء, 92000 | ACCEPT | PREMISE | 1873 Sheikh Zayed Bin Sultan Al Nahyan Road, 92000 حولي, الكويت |
| Mangaf, Kuwait, 34XJ+HJ Mangaf, Kuwait, Kuwait | ACCEPT | PREMISE_PROXIMITY | 7HXC34XJ+HJ, Al Aḩmadī, Kuwait |
| 25 Arabian Gulf St, Salmiya, مدينة الكويت, 35908 | ACCEPT | PREMISE_PROXIMITY | 25 Arabischer-Golf-Straße, 35908 حولي, الكويت |

**巴林 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Shop 179G, الساية | CONFIRM | ROUTE | Shop 179g, شارع الساية, اَلْمُحَرَّق, البحرين |
| 4609 طريق 316, المنامة | CONFIRM | ROUTE | 4609 طريق 316, اَلْمُحَرَّق, البحرين |
| 986 Rd No 2417, المنامة | CONFIRM | ROUTE | 2417 شارع المنامة, المنامة, البحرين |
| طريق 2811 657, المنامة | CONFIRM | ROUTE | 657 طريق 2811, اَلْمُحَرَّق, البحرين |

**巴林 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Seef Mall Muharraq, Muharraq | FIX | LOCALITY | Muharraq, Bahrain |
| Bahrain, مدينة حمد | FIX | LOCALITY | المنامة, البحرين |
| Unit G80 - Level G, City Centre Mall, Manama | FIX | LOCALITY | Unit G80, Al Muharraq, Bahrain |
| Diyar Al-Muharraq, قلالي, 263 | FIX | LOCALITY | 263, Al Muharraq, البحرين |

**巴林 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 5GQQ+QG Tubli, Bahrain, توبلي | ACCEPT | PREMISE_PROXIMITY | 7HRG5GQQ+QG, اَلْمُحَرَّق, البحرين |
| 5J68+P9G, Sitra, Bahrain, سفالة | ACCEPT | PREMISE_PROXIMITY | 7HRG5J68+P9, اَلْمُحَرَّق, البحرين |

**埃及 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| كارفور المعادي ، محافظة القاهرة ، مصر, المعادى, 11728 | CONFIRM | ROUTE | شارع كارفور, القاهرة, 11728, مصر |
| 3 شارع م. محمود صدقي, الاسكندرية | CONFIRM | PREMISE | 3 شارع محمود صدقي, القاهرة, الجيزة, 12551, مصر |
| Abbas El-Shareef, القاهرة, 4540010 | CONFIRM | ROUTE | Abbas Street, القاهرة, الجيزة, مصر |
| Omar Ibn El-Khattab, القاهرة, 3753450 | CONFIRM | ROUTE | Omar Ibn Al-Khattab Street, القاهرة, مصر |

**埃及 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Co-Op Gas Station, Nasr City, 11774 | FIX | LOCALITY | Cairo, Cairo Governorate, 11774, Egypt |
| Pyramids park, الجيزة, 12943 | FIX | LOCALITY | القاهرة, الجيزة, 12943, مصر |
| Cairo | FIX | LOCALITY | Cairo, Cairo Governorate, Egypt |
| الاسكندرية, الاسكندرية | FIX | OTHER | الإسكندرية, مصر |

**埃及 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 2 شارع اليابان متفرع من شارع خاتم المرسلين قاعة سيد درويش - العمرانيه, الجيزة, 12552 | ACCEPT | PREMISE | 2 شارع اليابان, القاهرة, الجيزة, 12552, مصر |
| 360 شارع الهرم - الجيزة - الدور الأول أمام سنيما رادوبيس, العمرانية الغربية، قسم العمرانية | ACCEPT | ROUTE | 360 شارع العمرانيه, القاهرة, الجيزة, 12551, مصر |
| X5V9+3H5, Farouk Mohammed, Al Kom Al Akhdar, El Talbia, Giza Governorate 3531140, الخصوص,  | ACCEPT | PREMISE_PROXIMITY | Farouq Mahmoud Street, القاهرة, الجيزة, مصر |

**哈萨克斯坦 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Түркебаев көшесі 86, Алматы, 050009 | CONFIRM | ROUTE | 050009, Almaty, Түркебаев көшесі 86, Қазақстан |
| Алматы микрорайон Аксай-4 118А, Алматы, 050063 | CONFIRM | ROUTE | 050063, Астана, Ақсай көшесі 4, Қазақстан |
| микрорайон Кайрат 4, Алматы | CONFIRM | ROUTE | Алматы, Қайрат көшесі 4, Қазақстан |
| Мәңгілік Ел даңғылы 30, Астана, 010000 | CONFIRM | PREMISE_PROXIMITY | 010000, Астана, Мәңгілік Ел даңғылы 30, Қазақстан |

**哈萨克斯坦 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Әл-Назыр көшесі 91, Алматы, 050000 | FIX | LOCALITY | 050000, Almaty, Әл-Назыр көшесі 91, Қазақстан |
| микрорайон Целинный 5/1, Астана, 010005 | FIX | LOCALITY | 010005, Астана, микрорайон Целинный 5/1, Қазақстан |
| астана, Целиноград ауданы, 010000 | FIX | LOCALITY | 010000, Astana, Қазақстан |
| Запотоцкий көшесі 2, Алматы, 050035 | FIX | LOCALITY | 050035, Almaty, Запотоцкий көшесі 2, Қазақстан |

**哈萨克斯坦 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Көкімжан Қазыбаев көшесі 272А, Алматы, 050014 | ACCEPT | ROUTE | 050014, Алматы, Қазыбаев көшесі 272A, Қазақстан |
| ​ул. Улагат 2, ​ул. Садвакасова 146, Алматы, 050063 | ACCEPT | ROUTE | 050063, Алматы, улица Улагат 2, Қазақстан |
| микрорайон 9-й 1, Алматы, 050036 | ACCEPT | ROUTE | 050036, Алматы, Микрорайон 9 1, Қазақстан |
| Qazybek Bi St 19, Шымкент, 160011 | ACCEPT | ROUTE | 160011, Шымкент, Qazybek bi street 19, Қазақстан |

**多米尼加 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Residencial Gacela, Santo Domingo | CONFIRM | ROUTE | Residencial Madelta, Santo Domingo Este, República Dominicana |
| Plaza granada oriental 2do nivel, Santo Domingo | CONFIRM | ROUTE | Calle Paseo de Granada, Santo Domingo de Guzmán, República Dominicana |
| Prol. Av. 27 de Febrero 500, Santo Domingo Oeste, 10904 | CONFIRM | PREMISE_PROXIMITY | Avenida 27 de Febrero 500, 10904 Santo Domingo de Guzmán, República Do |
| Maria Trinidad Sanchez, San Cristóbal, 91000 | CONFIRM | ROUTE | Calle María Trindad Sánchez, 91000 Los Alcarrizos, República Dominican |

**多米尼加 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| avenida sanvicente, Santo Domingo, 03012 | FIX | OTHER | 03012, República Dominicana |
| Ensanche espaillat, C/Jimani #42 D.N Rep. Dom., Santo Domingo, 11500 | FIX | LOCALITY | C/Jimani D.N Rep. Dom 42, 11500 Santo Domingo de Guzmán, República Dom |
| Avenida augusto lora #7 proximo a la Fuente Fun, Santiago, 51000 | FIX | LOCALITY | Avenida augusto lora proximo a la Fuente Fun 7, 51000 Santo Domingo de |
| Linha C 70 Br 364, Los Alcarrizos | FIX | LOCALITY | Linha C Br 364 70, Los Alcarrizos, República Dominicana |

**多米尼加 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Coronel Fernández Domínguez #11. Sector Landia, Los Alcarrizos, 10803 | ACCEPT | ROUTE | Calle Domínguez 11, 10803 Santo Domingo de Guzmán, República Dominican |
| Avenida Gustavo Mejía Ricart 12, Santo Domingo, 10121 | ACCEPT | PREMISE_PROXIMITY | Avenida Gustavo Mejía Ricart 12, 10121 Santo Domingo de Guzmán, Repúbl |
| 18°27'00.8"N 69°57'20.3"W\nSanto Domingo\nhttps://goo.gl/maps/vkibNkbMspx9YZydA, Santo Dom | ACCEPT | PREMISE_PROXIMITY | 77CGF22V+3P, 10901 Santo Domingo de Guzmán, República Dominicana |
| Av. San Vicente de Paúl 36, Santo Domingo Este, 11901 | ACCEPT | PREMISE_PROXIMITY | Avenida San Vicente de Paúl 36, 11901 Santo Domingo Este, República Do |

