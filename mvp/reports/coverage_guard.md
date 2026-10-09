# 试点范围守卫评测

开发集全部在试点范围内：被判成"范围外"的都是误判（应接近 0）。"判范围内"是找到了范围内证据（邮编 / 城镇 / 片区）的比例，其余是没有可用证据、照常匹配的。

合计：真实商户地址 26,400 条误判 35（0.13%），合成地址 13,200 条误判 2（0.02%）

| 市场 | 真实地址 | 误判范围外 | 判范围内 | 合成地址 | 误判范围外 | 判范围内 |
|---|---|---|---|---|---|---|
| AU | 600 | 1 | 100% | 300 | 0 | 95% |
| DE | 600 | 0 | 100% | 300 | 0 | 98% |
| FR | 600 | 0 | 100% | 300 | 0 | 96% |
| NL | 600 | 1 | 100% | 300 | 0 | 96% |
| AE | 600 | 0 | 98% | 300 | 0 | 80% |
| SA | 600 | 2 | 99% | 300 | 2 | 90% |
| MY | 600 | 0 | 100% | 300 | 0 | 74% |
| ID | 600 | 1 | 100% | 300 | 0 | 84% |
| TH | 600 | 0 | 100% | 300 | 0 | 69% |
| VN | 600 | 0 | 100% | 300 | 0 | 72% |
| PH | 600 | 0 | 100% | 300 | 0 | 89% |
| CA | 600 | 2 | 100% | 300 | 0 | 88% |
| MX | 600 | 2 | 100% | 300 | 0 | 95% |
| PR | 600 | 0 | 100% | 300 | 0 | 89% |
| BR | 600 | 1 | 100% | 300 | 0 | 97% |
| AR | 600 | 2 | 97% | 300 | 0 | 85% |
| CL | 600 | 0 | 100% | 300 | 0 | 70% |
| CO | 600 | 2 | 100% | 300 | 0 | 73% |
| GB | 600 | 1 | 100% | 300 | 0 | 88% |
| IE | 600 | 0 | 100% | 300 | 0 | 84% |
| BE | 600 | 0 | 100% | 300 | 0 | 92% |
| LU | 600 | 0 | 100% | 300 | 0 | 97% |
| CH | 600 | 1 | 100% | 300 | 0 | 96% |
| AT | 600 | 2 | 100% | 300 | 0 | 96% |
| IT | 600 | 2 | 100% | 300 | 0 | 70% |
| ES | 600 | 0 | 100% | 300 | 0 | 98% |
| PT | 600 | 1 | 100% | 300 | 0 | 94% |
| DK | 600 | 1 | 100% | 300 | 0 | 93% |
| SE | 600 | 0 | 100% | 300 | 0 | 89% |
| NO | 600 | 0 | 100% | 300 | 0 | 98% |
| FI | 600 | 1 | 100% | 300 | 0 | 96% |
| EE | 600 | 0 | 100% | 300 | 0 | 75% |
| LV | 600 | 2 | 100% | 300 | 0 | 98% |
| LT | 600 | 2 | 100% | 300 | 0 | 96% |
| PL | 600 | 2 | 100% | 300 | 0 | 98% |
| CZ | 600 | 0 | 100% | 300 | 0 | 98% |
| SK | 600 | 1 | 100% | 300 | 0 | 98% |
| HU | 600 | 0 | 100% | 300 | 0 | 90% |
| SI | 600 | 2 | 100% | 300 | 0 | 98% |
| HR | 600 | 0 | 100% | 300 | 0 | 96% |
| BG | 600 | 0 | 99% | 300 | 0 | 70% |
| NZ | 600 | 1 | 100% | 300 | 0 | 65% |
| JP | 600 | 1 | 97% | 300 | 0 | 88% |
| IN | 600 | 1 | 100% | 300 | 0 | 84% |

## 误判样例（开发集）

- AU：16a Abeckett Rd, Bunyip, 3815 — 范围外证据 postcode:3815, place:BUNYIP；范围内 无
- NL：Meester B.M. Teldersstraat 7, Arnhem, 6842 CT — 范围外证据 postcode:6842CT, place:ARNHEM；范围内 无
- SA：خميس مشيط - حي الضيافة - خلف بي مارك - امام الدفاع المدني, خميس مشيط, 62435 — 范围外证据 place:حي الضيافه；范围内 无
- SA：الدرب الشارع العام جوار الأحوال المدنية, جازان — 范围外证据 place:جازان；范围内 无
- SA：Office 38, No. 174, Rumah — 范围外证据 place:RUMAH；范围内 无
- SA：Office 17, 67, رقم 142, بلدية الروضة, Rumah, Riyadh, Saudi Arabia — 范围外证据 place:RUMAH；范围内 area:بلديه الروضه, city:RIYADH
- ID：Jl. Sultan agung, Bekasi Kota, 51216 — 范围外证据 postcode:51216；范围内 无
- CA：1 Long Branch Trl, Brampton, L6P 3V7 — 范围外证据 postcode:L6P3V7, place:BRAMPTON；范围内 无
- CA：190 Canam Cres, Brampton, L7A 1A9 — 范围外证据 postcode:L7A1A9, place:BRAMPTON；范围内 无
- MX：Calle Doctor Efrén E. Marín 16, Altotonga, 93700 — 范围外证据 postcode:93700, place:ALTOTONGA；范围内 无
- MX：Periférico Independencia 1000, Morelia, 58089 — 范围外证据 postcode:58089, place:MORELIA；范围内 无
- BR：Rua 14 número 2020, Santa Cruz, São Paulo — 范围外证据 place:SANTA CRUZ；范围内 city:SAO PAULO
- AR：Ruta 205 Km. 56, Ciudad de Buenos Aires, 1816 — 范围外证据 postcode:1816；范围内 无
- AR：Carlos Gardel 262, Tigre, B1648 — 范围外证据 place:TIGRE；范围内 无
- CO：Carrera 4 #69a-31, Rosales — 范围外证据 place:ROSALES；范围内 无
- CO：Calle 45 43-83; Barranquilla; Atlلntico, Bogotá, D.C. — 范围外证据 place:BARRANQUILLA；范围内 city:BOGOTA
- GB：Bank Street, Coatbridge, ML5 1EG — 范围外证据 postcode:ML51EG, place:COATBRIDGE；范围内 无
- CH：Bruggerstrasse 68, Baden, 5400 — 范围外证据 place:BADEN；范围内 无
- AT：Schönberg 12, Lohnsburg am Kobernaußerwald, 4923 — 范围外证据 place:LOHNSBURG AM KOBERNAUSSERWALD；范围内 无
- AT：Georg-Kropp-Straße 44, Salzburg, 5020 — 范围外证据 postcode:5020, place:SALZBURG；范围内 无
- IT：PIAZZA GENERALE ARMANDO DIAZ 13, CARNAGO, 21040 — 范围外证据 place:CARNAGO；范围内 无
- IT：Contrada Pozzo, Melissano, 73040 — 范围外证据 postcode:73040, place:MELISSANO；范围内 无
- PT：Avenida Infante Dom Henrique 5, Sintra, 2735-116 — 范围外证据 place:SINTRA；范围内 无
- DK：Lyngborghave 50, Birkerød, 3460 — 范围外证据 postcode:3460, place:BIRKEROD；范围内 无
- FI：University in Oulu, Finland, Oulu, 90570 — 范围外证据 postcode:90570, place:OULU；范围内 无
- LV：Fabrika, Cenu pagasts, Jelgavas novads, Cena — 范围外证据 place:CENU PAGASTS, place:CENA；范围内 无
- LV：Rožu iela 30, Inčukalns, 2141 — 范围外证据 postcode:2141, place:INCUKALNS；范围内 无
- LT：Dvaro gatvė 50, Šiauliai, 76346 — 范围外证据 place:SIAULIAI；范围内 无
- LT：Paupio gatvė 18, Antazavė, 32260 — 范围外证据 place:ANTAZAVE；范围内 无
- PL：ulica Boczna 4, Sośnicowice, 44-153 — 范围外证据 postcode:44153, place:SOSNICOWICE；范围内 无
- PL：ulica Graniczna 9f, Radomyśl Wielki, 39-310 — 范围外证据 postcode:39310, place:RADOMYSL WIELKI；范围内 无
- SK：Námestie Andreja Hlinku 8610/7b, Žilina, 010 01 — 范围外证据 postcode:01001, place:ZILINA；范围内 无
- SI：Pod gradom 1, Slovenj Gradec, 2380 — 范围外证据 postcode:2380, place:SLOVENJ GRADEC；范围内 无
- SI：Kazarje 10, Postojna, 6230 — 范围外证据 postcode:6230, place:POSTOJNA；范围内 无
- NZ：4 Hillside Road, Ostend, 1081 — 范围外证据 postcode:1081, place:OSTEND；范围内 无
- JP：埼玉県さいたま市大宮区上小町４９６−１, さいたま市大宮区, 330-0855 — 范围外证据 postcode:3300855, place:さいたま市 大宮区；范围内 无
- IN：Opp. Veterinary Hospital, Beside Fatema Clinic, Dr Sheikh Bunker Colony, Kamptee, Mumbai, 441001 — 范围外证据 postcode:441001, place:KAMPTEE；范围内 city:MUMBAI
