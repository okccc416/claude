# 多市场评测报告（自动生成）

- 真实地址：各城市留出的 20% 商户（不在参考库里）的自填地址，标准答案为商户坐标（弱标注）
- 合成地址：按各市场写法渲染的测试部分道路（AI 解析器训练时没见过），标准答案已知
- 解析方式：rules = 规则 + 地名表；crf = 机器学习（条件随机场）；hybrid = 两者都出候选，由参考数据裁决
- 判对标准（真实地址）：门牌级 ≤ 250 米、楼宇级 ≤ 400 米、道路级为该道路经过商户 250 米内；"偏差 >1 公里"的静默错误不是商户坐标不准能解释的，是真正的错

## 真实商户地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 科威特（KW） | B | rules | 600 | 2.5% | 27.3% | 22.2% | 22.7% | 24.2% | 1.2% | 0.5% | 25.0% | 10 |
| 科威特（KW） | B | crf | 600 | 2.2% | 20.0% | 15.0% | 50.7% | 11.0% | 1.2% | 0.7% | 16.0% | 5 |
| 科威特（KW） | B | hybrid | 600 | 2.5% | 27.5% | 21.2% | 22.0% | 25.5% | 1.3% | 0.7% | 24.8% | 9 |
| 巴林（BH） | B | rules | 600 | 0.5% | 31.7% | 19.8% | 8.8% | 39.0% | 0.2% | 0.2% | 29.3% | 8 |
| 巴林（BH） | B | crf | 600 | 0.3% | 21.3% | 3.3% | 49.0% | 26.0% | 0.0% | 0.0% | 19.7% | 3 |
| 巴林（BH） | B | hybrid | 600 | 0.5% | 34.2% | 19.0% | 7.8% | 38.3% | 0.2% | 0.2% | 31.5% | 7 |
| 埃及（EG） | B | rules | 600 | 0.7% | 29.8% | 4.3% | 6.8% | 57.2% | 1.2% | 0.7% | 31.7% | 37 |
| 埃及（EG） | B | crf | 600 | 0.7% | 22.3% | 16.7% | 28.3% | 31.5% | 0.5% | 0.3% | 26.0% | 13 |
| 埃及（EG） | B | hybrid | 600 | 0.7% | 31.8% | 4.3% | 6.5% | 55.5% | 1.2% | 0.7% | 34.2% | 37 |
| 哈萨克斯坦（KZ） | C | rules | 600 | 7.7% | 43.5% | 3.3% | 7.8% | 35.7% | 2.0% | 0.8% | 29.3% | 8 |
| 哈萨克斯坦（KZ） | C | crf | 600 | 5.5% | 40.0% | 9.2% | 15.0% | 28.8% | 1.5% | 0.5% | 27.0% | 4 |
| 哈萨克斯坦（KZ） | C | hybrid | 600 | 7.7% | 44.8% | 3.2% | 7.0% | 35.3% | 2.0% | 0.8% | 30.5% | 10 |
| 多米尼加（DO） | C | rules | 600 | 9.7% | 37.3% | 1.8% | 6.2% | 40.7% | 4.3% | 1.8% | 36.0% | 10 |
| 多米尼加（DO） | C | crf | 600 | 8.8% | 35.3% | 9.5% | 17.2% | 25.5% | 3.7% | 1.8% | 35.5% | 6 |
| 多米尼加（DO） | C | hybrid | 600 | 9.8% | 38.5% | 1.5% | 5.3% | 40.5% | 4.3% | 1.8% | 36.8% | 14 |

## 合成地址

| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | 静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 科威特（KW） | B | rules | 600 | 3.2% | 49.2% | 0.0% | 11.3% | 36.3% | 0.0% | 0.0% | 52.0% | 9 |
| 科威特（KW） | B | crf | 600 | 3.5% | 49.7% | 0.0% | 13.0% | 33.8% | 0.0% | 0.0% | 55.0% | 6 |
| 科威特（KW） | B | hybrid | 600 | 4.0% | 51.8% | 0.0% | 9.7% | 34.5% | 0.0% | 0.0% | 55.2% | 14 |
| 巴林（BH） | B | rules | 600 | 2.5% | 49.5% | 0.0% | 4.3% | 43.7% | 0.0% | 0.0% | 51.7% | 4 |
| 巴林（BH） | B | crf | 600 | 3.8% | 55.2% | 0.0% | 0.5% | 40.5% | 0.0% | 0.0% | 58.5% | 3 |
| 巴林（BH） | B | hybrid | 600 | 3.7% | 52.2% | 0.0% | 0.2% | 44.0% | 0.0% | 0.0% | 55.2% | 5 |
| 埃及（EG） | B | rules | 600 | 12.7% | 55.3% | 0.0% | 0.8% | 30.8% | 0.3% | 0.2% | 68.0% | 9 |
| 埃及（EG） | B | crf | 600 | 14.5% | 65.2% | 0.0% | 3.2% | 17.2% | 0.0% | 0.0% | 78.5% | 7 |
| 埃及（EG） | B | hybrid | 600 | 13.8% | 57.7% | 0.0% | 0.7% | 27.7% | 0.2% | 0.0% | 71.0% | 15 |
| 哈萨克斯坦（KZ） | C | rules | 600 | 9.0% | 79.0% | 0.0% | 1.2% | 10.8% | 0.0% | 0.0% | 77.3% | 4 |
| 哈萨克斯坦（KZ） | C | crf | 600 | 9.5% | 78.0% | 0.0% | 0.2% | 12.3% | 0.0% | 0.0% | 80.3% | 3 |
| 哈萨克斯坦（KZ） | C | hybrid | 600 | 10.2% | 79.0% | 0.0% | 0.2% | 10.7% | 0.0% | 0.0% | 78.0% | 6 |
| 多米尼加（DO） | C | rules | 600 | 8.3% | 49.7% | 0.0% | 1.0% | 41.0% | 0.0% | 0.0% | 55.5% | 7 |
| 多米尼加（DO） | C | crf | 600 | 9.5% | 52.0% | 0.0% | 0.2% | 38.3% | 0.0% | 0.0% | 58.7% | 6 |
| 多米尼加（DO） | C | hybrid | 600 | 9.5% | 51.5% | 0.0% | 0.0% | 39.0% | 0.0% | 0.0% | 58.3% | 12 |

## 错误样例（规则解析，真实地址）

**科威特 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| شارع 10, مدينة الكويت | CONFIRM | ROUTE | شارع 10, الفروانية, الكويت |
| شارع فهد السالم 11, مدينة الكويت | CONFIRM | PREMISE_PROXIMITY | 11 شارع فهد السالم, حولي, الكويت |
| Abdulla Al Fadala, مدينة الكويت, 00965 | CONFIRM | ROUTE | Abdullah Al-Fadhala Street, 00965 حولي, الكويت |
| شارع 3 9, حولى | CONFIRM | PREMISE | 9 شارع 3, الفروانية, الكويت |

**科威特 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| المسيله, مبارك الكبير | FIX | OTHER |  |
| جنوب السرة South Surra, حولى | FIX | LOCALITY | حولي, الكويت |
| Mcdonald's, حولى, 3000 | FIX | OTHER | 3000, الكويت |
| Alfaiha, مدينة الكويت | FIX | OTHER |  |

**科威特 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| 113، Boulevard Mall، 8 Qatar Street, حولى, 25409 | ACCEPT | PREMISE_PROXIMITY | 8 Qatar Street, 25409 حولي, الكويت |
| 83M6+R8W Salmiya, Kuwait, Kuwait | ACCEPT | PREMISE_PROXIMITY | 7HXC83M6+R8, Ḩawallī, Kuwait |
| Nouf Tower, 10th Floor, Jaber Al-Mubarak Street, مدينة الكويت | ACCEPT | PREMISE_PROXIMITY | Tower 10th, NOUF TOWER, Jaber Al-Mubarak Street, حولي, الكويت |
| 6463+QMV, فنيطيس | ACCEPT | PREMISE_PROXIMITY | 7HXC6463+QM, احمدی, الكويت |

**巴林 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Gate No 131, Road 20, Barbar 522, المرخ | CONFIRM | ROUTE | 20 Barbar Avenue, اَلْمُحَرَّق, البحرين |
| BUILDING 1233, ROAD, 3619 AL DIRAZ 0536, الدراز, 536 | CONFIRM | ROUTE | 0536 Al-Diraz Avenue, اَلْمُحَرَّق, البحرين |
| شارع 3 10, توبلي | CONFIRM | ROUTE | 10 شارع 3, المنامة, البحرين |
| Level 1 , Bahrain City Centre , Seef Area, المنامة, 317 | CONFIRM | PREMISE_PROXIMITY | Level 1, Bahrain City Centrer, 317, اَلْمُحَرَّق, البحرين |

**巴林 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Promedia Advertising Agency, Office 11 Entrance 4038, ROAD 0469, AL QARYAH 0604 CAPITAL GO | FIX | LOCALITY | Office 11, 4038 Office 11 Entrance, اَلْمُحَرَّق, البحرين |
| Gate 1950, Rd No 2542, بوقوة, BLOCK 479 | FIX | OTHER | Block 479, 2542, البحرين |
| Nasser Al-Jabur Avenue, Manama | FIX | LOCALITY | Al Muharraq, Bahrain |
| Rd No 551, توبلي, 701 | FIX | OTHER | 551, البحرين |

**巴林 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Dana Mall, Sheikh Khalifa Bin Salman St, Avenue 28, Alsuwayfiyah Manama، 323, سار, 00973 | ACCEPT | PREMISE_PROXIMITY | Dana Mall, 323 Avenue 28, اَلْمُحَرَّق, البحرين |

**埃及 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| شارع الشيخ صالح الجعفرى خلف مشيخة الازهر - الدراسة, القاهرة | CONFIRM | ROUTE | شارع الشيخ صالح الجعفري, القاهرة, مصر |
| 25 El-Montaza St, القاهرة, 11351 | CONFIRM | PREMISE | 25 Al Montaza Street, القاهرة, الجيزة, 12961, مصر |
| CSA, Maadi, المعادى, <<not-applicable>> | CONFIRM | ROUTE | Al Maadi Street, ئەسکەندەریە, الإسكندرية, مصر |
| 138 محور المحمودية, الاسكندرية | CONFIRM | ROUTE | شارع ماهر محمد عايد, القاهرة, الجيزة, مصر |

**埃及 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| مسجد المهند - النرجس 1 بجوار فندق توليب - شارع التسعين الجنوبي - التجمع الخامس, القاهرة ال | ACCEPT | PREMISE | 1 شارع التسعين الجنوبي, القاهرة, 11835, مصر |
| فيلات الأمن العام, فيلا 18, Moustafa Kamel Axis, القاهرة الجديدة, 11865 | ACCEPT | PREMISE | 18 محور مصطفى كامل, القاهرة, 11865, مصر |
| Fares seafood Almaza-مطعم فارس للمأكولات البحرية مصر الجديدة, 38JW+VXG امام, عمر بن الخطاب | ACCEPT | PREMISE_PROXIMITY | شارع عمر بن الخطاب, القاهرة, 11775, مصر |
| Building no. 10, 150 St., Horriya Square 2, Maadi, المعادى, 12151 | ACCEPT | ROUTE | 150 Square, القاهرة, الجيزة, 12151, مصر |

**埃及 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| egypt, القاهرة | FIX | OTHER | القاهرة, مصر |
| القاهرة, الجيزة | FIX | OTHER | الجيزة, مصر |
| cairo, القاهرة, 21523 | FIX | LOCALITY | القاهرة, 21523, مصر |
| أركيديا مول الدور الأرضي محل A18, القاهرة | FIX | OTHER | القاهرة, مصر |

**哈萨克斯坦 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Мамыр-4 шағын ауданы 86, Алматы, 050036 | CONFIRM | ROUTE | 050036, Алматы, Мамыр көшесі 4, Қазақстан |
| Конаев 14, Астана, 010000 | CONFIRM | ROUTE | 010000, Астана, Қонаев көшесі 14, Қазақстан |
| Мамыр-7 шағын ауданы 17А, Алматы, 050036 | CONFIRM | ROUTE | 050036, Алматы, Мамыр көшесі 7, Қазақстан |
| Юрий Гагарин даңғылы 277, Алматы, 050060 | CONFIRM | ROUTE | 050060, Астана, Юрий Гагарин көшесі 277, Қазақстан |

**哈萨克斯坦 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| apple town Вход через 2 паркинг, Алматы, 050043 | FIX | LOCALITY | 050043, Almaty, apple town Вход через паркинг 2, Қазақстан |
| Жәңібек Керей хандары көшесі 24, Астана, 010000 | FIX | LOCALITY | 010000, Астана, Жәңібек Керей хандары көшесі 24, Қазақстан |
| 4-ші шағын аудан 5, Алматы, 050062 | FIX | LOCALITY | 050062, Астана, 4-ші шағын аудан 5, Қазақстан |
| Furmanov Ave 65, Алматы, 050057 | FIX | LOCALITY | 050057, Almaty, Furmanov Ave 65, Қазақстан |

**哈萨克斯坦 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| улица Ырысты 46, Алматы, 050061 | ACCEPT | PREMISE_PROXIMITY | 050061, Алматы, Ырысты көшесі 46, Қазақстан |
| Абдыразакова, 1/1, Шымкент, 160019 | ACCEPT | PREMISE_PROXIMITY | 160019, Шымкент, улица Абдыразакова 1/1, Қазақстан |
| ТЦ Abu-Dhabi Plaza, Syganak St 60/5, Астана, 010000 | ACCEPT | PREMISE_PROXIMITY | 010000, Астана, ТЦ Abu Dhabi Plaza, Syganak street 60/5, Қазақстан |
| Qazybek Bi St 13, Шымкент, 160017 | ACCEPT | ROUTE | 160017, Шымкент, Qazybek bi street 13, Қазақстан |

**多米尼加 · 错误建议**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Cancha La Francia Nueva, Villa Duarte, Santo Domingo, 11602 | CONFIRM | ROUTE | Villa, 11602 Los Alcarrizos, República Dominicana |
| 𝗣𝗹𝗮𝘇𝗮 𝗔𝗻𝗱𝗮𝗹𝘂𝗰í𝗮 𝗜𝗜 Piantini.u2063 Local 35B nivel 2, Santo Domingo, 10127 | CONFIRM | PREMISE_PROXIMITY | Local 35b, Calle Andalucía 2, 10127 Santo Domingo de Guzmán, República |
| Plaza Jessica, Carretera Mella Boulevard Pedro 200, Santo Domingo Este, 11519 | CONFIRM | ROUTE | Carretera Mella 200, 11519 Santo Domingo Este, República Dominicana |
| C. Duarte 81, Bajos de Haina, 91000 | CONFIRM | ROUTE | Calle Duarte 81, 91000 Santo Domingo Oeste, República Dominicana |

**多米尼加 · 判 FIX**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Santo Domingo, Santo Domingo | FIX | OTHER |  |
| C/Juan Erazo Esq.36A #18 Villas Agricolas Santo Domingo D. N., Santo Domingo, 10100 | FIX | LOCALITY | C/Juan Erazo Esq.36A Villas Agricolas Santo Domingo D. N 18, 10100 San |
| Alma Rosa 2da, Santo Domingo, 00981 | FIX | LOCALITY | 00981 Santo Domingo Este, República Dominicana |
| Ruta m Plaza ISABEL EMILIA ,Modulo 103,frente a utesa,51031, Santiago | FIX | LOCALITY | Modulo 103, 51031 Santo Domingo Este, República Dominicana |

**多米尼加 · 静默错误**

| 输入 | 结论 | 粒度 | 标准化结果 |
|---|---|---|---|
| Av. Buenaventura Freites No.32, Santo Domingo, 10602 | ACCEPT | PREMISE_PROXIMITY | Avenida Buenaventura Freites 32, 10602 Santo Domingo de Guzmán, Repúbl |
| Avenida Isabel Aguiar #92, Zona Industrial de Herrera, (Frente a Cemex), Santo Domingo, 11 | ACCEPT | PREMISE_PROXIMITY | Avenida Isabel Aguiar 92, 11113 Santo Domingo Oeste, República Dominic |
| C. El Vergel 72, Santo Domingo, 10107 | ACCEPT | PREMISE_PROXIMITY | Calle El Vergel 72, 10107 Santo Domingo de Guzmán, República Dominican |
| Naco, Avenida Tiradentes 5, Santo Domingo, 10119 | ACCEPT | PREMISE_PROXIMITY | Avenida Tiradentes 5, 10119 Santo Domingo de Guzmán, República Dominic |

