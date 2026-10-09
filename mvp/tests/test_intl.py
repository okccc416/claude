"""多市场引擎测试：用一个微型"悉尼"（A 类，有官方地址点）和一个微型"迪拜"（B 类，只有道路 / 片区 / 楼宇）
走完整的构建流程（与真实数据同样的 parquet 字段），再验证解析、结论、粒度与响应格式。"""

from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")
shapely = pytest.importorskip("shapely")

from avmvp.intl.engine import ACCEPT, ADD_SUB, CONFIRM, FIX, Engine  # noqa: E402
from avmvp.intl.parse import RuleParser, strip_noise  # noqa: E402
from avmvp.intl.reference import build, is_test_place  # noqa: E402
from avmvp.intl.text import core_key, key, tokenize  # noqa: E402


def _bbox(lat, lng, d=0.0003):
    return {"xmin": lng - d, "ymin": lat - d, "xmax": lng + d, "ymax": lat + d}


def _names(primary, *others):
    return {"primary": primary, "common": [["en", o] for o in others] or None}


def _place_ids(n):
    """生成 n 个不会被留出为测试集的 POI 编号（留出规则按编号哈希）。"""
    out, i = [], 0
    while len(out) < n:
        if not is_test_place(f"p{i}"):
            out.append(f"p{i}")
        i += 1
    return out


def _write(d: Path, areas, segments, places, addresses=None):
    """areas: [(名称, 子类型, (xmin, ymin, xmax, ymax))]；segments: [(名称, 纬度, 经度)] 或 [(名称, [(纬度, 经度), …])]
    （后者带线形）；places: [(名称, 类别, 纬度, 经度[, 邮编])]；addresses: [(门牌, 道路, 单元, 邮编, 纬度, 经度)]"""
    from shapely.geometry import LineString, box

    d.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist([
        {"id": f"d{i}", "names": _names(*n) if isinstance(n, tuple) else _names(n), "subtype": st,
         "bbox": {"xmin": b[0], "ymin": b[1], "xmax": b[2], "ymax": b[3]}} for i, (n, st, b) in enumerate(areas)]),
        d / "divisions.parquet")
    pq.write_table(pa.Table.from_pylist([
        {"division_id": f"d{i}", "geometry": box(*b).wkb,
         "bbox": {"xmin": b[0], "ymin": b[1], "xmax": b[2], "ymax": b[3]}} for i, (_, _, b) in enumerate(areas)]),
        d / "division_areas.parquet")
    rows = []
    for n, *geo in segments:
        names = _names(*n) if isinstance(n, tuple) else _names(n)
        if len(geo) == 2:
            rows.append({"names": names, "bbox": _bbox(*geo), "geometry": None})
        else:
            line = LineString([(lng, lat) for lat, lng in geo[0]])
            x0, y0, x1, y1 = line.bounds
            rows.append({"names": names, "bbox": {"xmin": x0, "ymin": y0, "xmax": x1, "ymax": y1},
                         "geometry": line.wkb})
    pq.write_table(pa.Table.from_pylist(rows), d / "segments.parquet")
    ids = _place_ids(len(places))
    pq.write_table(pa.Table.from_pylist([
        {"id": pid, "names": _names(n), "basic_category": c,
         "addresses": [{"freeform": "", "locality": "", "postcode": pc[0] if pc else ""}],
         "bbox": _bbox(lat, lng, 0.0001)}
        for pid, (n, c, lat, lng, *pc) in zip(ids, places)]), d / "places.parquet")
    if addresses:
        pq.write_table(pa.Table.from_pylist([
            {"number": n, "street": s, "unit": u, "postcode": pc, "address_levels": [{"value": "Sydney"}],
             "bbox": _bbox(lat, lng, 0.00005)} for n, s, u, pc, lat, lng in addresses]), d / "addresses.parquet")


@pytest.fixture(scope="module")
def au(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    surry, newtown = (151.200, -33.895, 151.220, -33.880), (151.170, -33.905, 151.190, -33.890)
    segs = [("Crown Street", -33.884 - 0.001 * i, 151.212) for i in range(6)]
    segs += [("Bourke Street", -33.884 - 0.001 * i, 151.216) for i in range(4)]
    segs += [("King Street", -33.893 - 0.001 * i, 151.180) for i in range(5)]
    addrs = [("100", "Crown Street", "", "2010", -33.8850, 151.2121),
             ("102", "Crown Street", "1", "2010", -33.8852, 151.2121),
             ("102", "Crown Street", "2", "2010", -33.8852, 151.2121),
             ("104", "Crown Street", "", "2010", -33.8854, 151.2121),
             ("50", "Bourke Street", "", "2010", -33.8860, 151.2161),
             ("200", "King Street", "", "2042", -33.8950, 151.1801)]
    places = [("Crown Street Public School", "elementary_school", -33.8870, 151.2125)]
    _write(root / "AU", [("Surry Hills", "neighborhood", surry), ("Newtown", "neighborhood", newtown)],
           segs, places, addrs)
    return Engine("AU", "rules", build("AU", "A", log=lambda *_: None, root=root))


@pytest.fixture(scope="module")
def ae(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    barsha, deira = (55.19, 25.10, 55.21, 25.12), (55.30, 25.26, 55.32, 25.28)
    segs = [("Sheikh Zayed Road", 25.105 + 0.001 * i, 55.200) for i in range(8)]
    segs += [("6th Street", 25.112 + 0.001 * i, 55.205) for i in range(3)]  # 两个社区都有 6th Street
    segs += [("6th Street", 25.268 + 0.001 * i, 55.310) for i in range(3)]
    places = [("Mall of the Emirates", "shopping_mall", 25.1100, 55.2008),
              ("Barsha Heights Tower", "corporate_or_business_office", 25.1130, 55.2052)]
    _write(root / "AE", [("Al Barsha", "neighborhood", barsha), ("Deira", "neighborhood", deira)], segs, places)
    return Engine("AE", "rules", build("AE", "B", log=lambda *_: None, root=root))


@pytest.fixture(scope="module")
def sa(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    olaya = (46.66, 24.68, 46.70, 24.72)
    segs = [(("طريق الملك فهد", "King Fahd Road"), [(24.685, 46.680), (24.700, 46.680)]),  # 两段各约 1.7 公里
            (("طريق الملك فهد", "King Fahd Road"), [(24.700, 46.680), (24.715, 46.680)]),
            ("شارع ابن تيمية", [(24.700, 46.685), (24.700, 46.690)])]  # 只有阿拉伯文名称
    places = [("Olaya Pharmacy", "pharmacy", 24.69, 46.67)]
    places += [(f"Shop {i}", "retail", 24.700 + 0.001 * i, 46.6805, "12211") for i in range(4)]  # 邮编 12211 的位置
    _write(root / "SA", [("العليا", "neighborhood", olaya)], segs, places)
    return Engine("SA", "rules", build("SA", "B", log=lambda *_: None, root=root))


# ---------------------------------------------------------------------------------------------- 文本
def test_text_normalization():
    assert key("Musterstraße 12", "DE") == key("MUSTERSTRASSE 12", "DE")
    assert key("Đ. Tô Hiến Thành", "VN") == key("Duong To Hien Thanh", "VN")  # 越南文去声调 + 缩写展开
    assert tokenize("339/5 Tô Hiến Thành")[0] == "339/5"
    assert key("١٢ شارع", "AE").startswith("12")  # 阿拉伯-印度数字
    assert core_key("Jalan Ampang", "MY", "street") == core_key("Jln Ampang", "MY", "street") == "AMPANG"
    assert key("شارع الوصل", "AE") == key("شارع الوصل", "AE")  # 阿拉伯文字母统一后稳定


def test_noise_and_codes_are_separated():
    text, noise, codes = strip_noise("Villa 12, 6th St, Al Barsha, Makani 12345 67890, call +971 50 123 4567")
    assert codes.get("makani") == "12345 67890"
    assert noise.get("phones")
    assert "12345" not in text and "4567" not in text


# ---------------------------------------------------------------------------------------------- A 类
def test_au_parse(au):
    p = RuleParser(au.ref).parse("Unit 2/102 Crown St, Surry Hills NSW 2010")
    assert p.number == "102" and p.unit and "2" in p.unit and p.postcode == "2010"
    assert au.ref.streets[p.streets[0].ids[0]].name == "Crown Street"


def test_au_exact_premise_accepts(au):
    r = au.validate("100 Crown Street, Surry Hills NSW 2010")
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE")
    assert abs(r.lat + 33.8850) < 0.001


def test_au_spelling_error_needs_confirmation(au):
    r = au.validate("100 Crown Stret, Surry Hills 2010")
    assert r.granularity == "PREMISE" and r.action == CONFIRM
    assert "STREET_SPELL_CORRECTED" in r.reasons


def test_au_multi_unit_building_asks_for_unit(au):
    assert au.validate("102 Crown St, Surry Hills NSW 2010").action == ADD_SUB
    assert au.validate("2/102 Crown St, Surry Hills NSW 2010").action == ACCEPT


def test_au_missing_number_is_fix_unknown_number_is_route_confirm(au):
    # 与 Google 一致：门牌不在表里 -> 道路级位置 + CONFIRM（门牌未确认）；没写门牌 -> FIX
    r = au.validate("999 Crown Street, Surry Hills NSW 2010")
    assert r.action == CONFIRM and r.granularity == "ROUTE" and "PREMISE_NOT_FOUND" in r.reasons
    assert au.validate("Crown Street, Surry Hills NSW 2010").action == FIX


def test_au_number_range_and_glued_tokens(au):
    r = au.validate("100-104 Crown St, Surry Hills NSW 2010")  # 官方表只记单个门牌时按区间首尾查
    assert r.granularity == "PREMISE" and r.action in (ACCEPT, ADD_SUB)
    assert tokenize("Shop4068, 500Oxford Street, 12th Ave") == ["SHOP", "4068", "500", "OXFORD", "STREET", "12TH", "AVE"]


def test_au_wrong_postcode_is_replaced(au):
    r = au.validate("100 Crown Street, Surry Hills NSW 2042")
    assert r.action == CONFIRM and r.components["postal_code"]["text"] == "2010"
    assert "POSTCODE_REPLACED" in r.reasons


# ---------------------------------------------------------------------------------------------- B 类
def test_ae_building_on_street_accepts(ae):
    r = ae.validate("Mall of the Emirates, Sheikh Zayed Road, Al Barsha, Dubai")
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE_PROXIMITY")
    assert r.components["premise_name"]["text"] == "Mall of the Emirates"


def test_ae_street_with_area_is_located_but_confirmed(ae):
    r = ae.validate("Villa 12, 6th Street, Al Barsha, Dubai")
    assert r.granularity == "ROUTE" and 25.1 < r.lat < 25.13  # 定位到 Al Barsha 的那条 6th Street
    # 同名道路有两条、没有邮编印证：道路级结论要用户确认（开发集上这类直接通过的错误率在 10% 以上）
    assert r.action == CONFIRM and "ROUTE_NOT_CORROBORATED" in r.reasons


def test_ae_duplicate_street_without_area_needs_confirmation(ae):
    r = ae.validate("Villa 12, 6th Street, Dubai")
    assert r.action == CONFIRM and "AMBIGUOUS_MULTIPLE_CANDIDATES" in r.reasons


def test_ae_area_only_is_fix(ae):
    r = ae.validate("Al Barsha, Dubai")
    assert (r.action, r.granularity) == (FIX, "LOCALITY")


def test_response_shape(ae):
    out = ae.to_response(ae.validate("Mall of the Emirates, Sheikh Zayed Road, Al Barsha, Dubai, Makani 12345 67890"))
    v = out["result"]["verdict"]
    assert v["possibleNextAction"] == ACCEPT and v["validationGranularity"] == "PREMISE_PROXIMITY"
    assert all({"code", "message"} <= set(x) for x in v["reasons"])
    assert out["result"]["codes"]["makani"] == "12345 67890"
    assert out["result"]["metadata"]["regionCode"] == "AE"
    json.dumps(out, ensure_ascii=False)


# ---------------------------------------------------------------------------------------------- 中东：线形 / 转写 / Plus Code
def test_long_road_segments_merge_and_follow_geometry(sa):
    from avmvp.intl.engine import dist_to_street

    ids = sa.ref.street_keys[key("King Fahd Road", "SA")]
    assert len(ids) == 1  # 两段首尾相接，合并为一条路（路段中心相距 1.7 公里）
    assert dist_to_street(sa.ref, next(iter(ids)), 24.6925, 46.6801) < 30  # 路段中间也有沿线点


def test_latin_transliteration_matches_arabic_name(sa):
    r = sa.validate("Ibn Taymiyyah St., Olaya, Riyadh")
    assert r.best and r.best.street is not None
    assert sa.ref.streets[r.best.street].name == "شارع ابن تيمية"
    assert "STREET_TRANSLITERATED" in r.reasons


def test_plus_code_locates_address(sa):
    from avmvp.intl.pluscode import encode

    full = encode(24.7001, 46.6802)  # King Fahd Road 旁边
    r = sa.validate(f"{full[4:]}, King Fahd Road, Riyadh")  # 短码，按城市补齐
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE_PROXIMITY")
    assert abs(r.lat - 24.7001) < 0.0002 and abs(r.lng - 46.6802) < 0.0002
    assert "LOCATED_BY_PLUS_CODE" in r.reasons
    far = sa.validate(f"{full[4:]}, Ibn Taymiyyah Street, Riyadh")  # 与所写道路相距约 500 米
    assert far.action == CONFIRM and "PLUS_CODE_STREET_MISMATCH" in far.reasons


def test_route_accept_needs_postcode_corroboration(sa):
    r = sa.validate("12 King Fahd Road, Riyadh 12211")
    assert (r.action, r.granularity) == (ACCEPT, "ROUTE")  # 道路名唯一、邮编就在道路旁
    r = sa.validate("12 King Fahd Road, Riyadh")
    assert r.action == CONFIRM and "ROUTE_NOT_CORROBORATED" in r.reasons


def test_pasted_coordinates_locate_address(sa):
    r = sa.validate("24.700100, 46.680200, King Fahd Road, Riyadh")
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE_PROXIMITY")
    assert "LOCATED_BY_COORDINATES" in r.reasons and abs(r.lat - 24.7001) < 1e-6


def test_placeholder_postcode_is_ignored(sa):
    r = sa.validate("12 King Fahd Road, Al Olaya, Riyadh 00000")
    assert r.parsed.postcode is None and "POSTCODE_STREET_MISMATCH" not in r.reasons


def test_plus_code_decoder_matches_spec():
    from avmvp.intl.pluscode import decode, recover

    lat, lng, _ = decode("9C3W9QCJ+2VX")  # 规范里的测试数据
    assert abs(lat - 51.3701125) < 1e-6 and abs(lng + 1.217765625) < 1e-6
    lat, lng, _ = recover("CJ+2VX", 51.3708675, -1.217765625)
    assert abs(lat - 51.3701125) < 1e-6 and abs(lng + 1.217765625) < 1e-6


# ---------------------------------------------------------------------------------------------- 机器学习解析器
def test_crf_training_and_hybrid(au):
    pytest.importorskip("pycrfsuite")
    from avmvp.intl.crf import train
    from avmvp.intl.render import Renderer

    rd = Renderer(au.ref, "train", 1)
    rd.street_ids = [s.id for s in au.ref.streets]  # 微型参考库只有 3 条路，不分训练 / 测试
    samples = [s for s in (rd.sample(noise=0.2) for _ in range(400)) if s and s.tokens]
    train(au.ref, samples, au.ref.dir / "crf.model", iterations=30)
    eng = Engine("AU", "hybrid", au.ref)
    r = eng.validate("100 Crown Street, Surry Hills NSW 2010")
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE")
    assert Engine("AU", "crf", au.ref).crf.parse("100 Crown Street Surry Hills 2010").streets


# ---------------------------------------------------------------------------------------------- 本地小模型
class StubLLM:
    """替身模型：返回固定字段，用来测试防编造和级联逻辑（真模型的效果见 docs/13）。"""
    name = "stub"

    def __init__(self, fields):
        self.fields = fields

    def extract(self, text, market):
        return dict(self.fields)


def test_llm_guard_drops_invented_fields():
    from avmvp.intl.llm import guard

    fields = {"house_number": "99", "unit": "Office 5", "building": "Burj Khalifa", "street": "Sheikh Zayed Road",
              "area": "", "postcode": ""}
    kept, verbatim = guard(fields, "Office 5, Sheikh Zayed Rd, Dubai", "AE")
    assert "house_number" not in kept  # 99 不在原文里：编造的门牌丢弃
    assert "building" not in kept  # 原文没有 Burj Khalifa
    assert kept["street"] == "Sheikh Zayed Road" and kept["unit"] == "Office 5"
    assert verbatim is False  # Rd -> Road 是改写


def test_llm_cascade_only_when_rules_fail_and_is_capped(ae):
    stub = StubLLM({"house_number": "", "unit": "", "building": "Mall of the Emirates",
                    "street": "Sheikh Zayed Road", "area": "Al Barsha", "postcode": ""})
    eng = Engine("AE", "rules", ae.ref, llm=stub)
    r = eng.validate("MallofEmirates/SheikhZayedRd/AlBarsha")  # 粘连写法，规则解析不出来
    assert r.parser == "rules+llm" and r.granularity == "PREMISE_PROXIMITY"
    assert r.action == CONFIRM and "LLM_REWRITTEN" in r.reasons  # 模型改写过的字段最多给 CONFIRM
    calls = eng.llm.calls
    ok = eng.validate("Mall of the Emirates, Sheikh Zayed Road, Al Barsha, Dubai")
    assert ok.action == ACCEPT and eng.llm.calls == calls  # 规则已经直接通过：不调用模型


# ---------------------------------------------------------------------------------------------- 置信度
def test_confidence_is_calibrated_and_shrinks(au):
    from avmvp.intl.confidence import IntlConfidence, signatures

    r_ok = au.validate("100 Crown Street, Surry Hills NSW 2010")
    r_fix = au.validate("999 Crown Street, Surry Hills NSW 2010")
    s_ok, s_fix = signatures(r_ok, "AU", "A"), signatures(r_fix, "AU", "A")
    assert s_ok[0].startswith("AU|ACCEPT|PREMISE|") and s_ok[-1] == "ACCEPT|PREMISE"
    model = IntlConfidence().fit([(s_ok, True)] * 90 + [(s_ok, False)] * 10 + [(s_fix, False)] * 3)
    assert abs(model.confidence(r_ok, "AU", "A") - 0.9) < 0.02  # 样本多：接近实际比例 90/100
    rare = model.from_signatures(["XX|ACCEPT|PREMISE|z", "A|ACCEPT|PREMISE|z", "A|ACCEPT|PREMISE", "ACCEPT|PREMISE"])
    assert 0.85 < rare < 0.95  # 没见过的细类：退回到粗一级的估计
    eng = Engine("AU", "rules", au.ref, confidence=model)
    out = eng.to_response(eng.validate("100 Crown Street, Surry Hills NSW 2010"))
    assert 0 < out["result"]["verdict"]["confidence"] <= 1 and "100" in out["result"]["verdict"]["confidenceNote"]
    strict = eng.validate("100 Crown Street, Surry Hills NSW 2010", min_confidence=0.95)  # 置信度约 0.9 < 门槛
    assert strict.action == CONFIRM and "LOW_CONFIDENCE" in strict.reasons
    assert abs(strict.confidence - 0.9) < 0.02  # 降级后仍报告原结论的置信度
    assert eng.validate("100 Crown Street, Surry Hills NSW 2010", min_confidence=0.8).action == ACCEPT


# ---------------------------------------------------------------------------------------------- 批量清洗
def test_batch_csv_script(au, tmp_path):
    import csv
    import os
    import subprocess
    import sys

    src = tmp_path / "in.csv"
    src.write_text("id,address\n1,\"100 Crown St, Surry Hills NSW 2010\"\n2,\"999 Crown St, Surry Hills 2010\"\n3,\n",
                   encoding="utf-8")
    out = tmp_path / "out.csv"
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "AV_MARKETS_DIR": str(au.ref.dir.parent)}
    subprocess.run([sys.executable, str(root / "scripts" / "batch_validate.py"), str(src), str(out), "--region", "AU",
                    "--parser", "rules"], check=True, env=env, capture_output=True)
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    assert [r["id"] for r in rows] == ["1", "2", "3"]  # 原有列保留
    assert rows[0]["av_action"] == ACCEPT and rows[0]["av_granularity"] == "PREMISE" and rows[0]["av_lat"]
    assert rows[1]["av_action"] == CONFIRM and "PREMISE_NOT_FOUND" in rows[1]["av_reasons"]
    assert rows[2]["av_error"]  # 空地址：记录原因，不中断


# ---------------------------------------------------------------------------------------------- 服务
def test_router_and_http(au, monkeypatch):
    from avmvp import router as router_mod
    from avmvp.server import make_handler

    monkeypatch.setattr(router_mod, "DATA", au.ref.dir.parent)
    r = router_mod.MarketRouter(None, ["SG", "AU", "DE"], "rules")
    assert [m["code"] for m in r.describe()] == ["AU", "DE"]  # 没有新加坡参考库时不开放 SG
    r._engines["AU"] = au
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(r))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        body = json.dumps({"address": {"regionCode": "au", "addressLines": ["100 Crown St"],
                                       "locality": "Surry Hills", "postalCode": "2010"}}).encode()
        out = json.loads(urlopen(Request(f"{base}/v1/address:validate", body,
                                         {"Content-Type": "application/json"})).read())
        assert out["result"]["verdict"]["possibleNextAction"] == ACCEPT
        assert out["result"]["metadata"]["regionCode"] == "AU"
        markets = json.loads(urlopen(f"{base}/v1/markets").read())["markets"]
        assert {"code": "DE", "available": False} .items() <= next(m for m in markets if m["code"] == "DE").items()
        batch = json.dumps({"requests": [
            {"address": {"regionCode": "AU", "addressLines": ["100 Crown St, Surry Hills NSW 2010"]}},
            {"address": {"regionCode": "JP", "addressLines": ["1-1 Chiyoda"]}}]}).encode()
        out = json.loads(urlopen(Request(f"{base}/v1/address:batchValidate", batch,
                                         {"Content-Type": "application/json"})).read())
        assert len(out["responses"]) == 2  # 单条出错不影响其他条
        assert out["responses"][0]["result"]["verdict"]["possibleNextAction"] == ACCEPT
        assert "JP" in out["responses"][1]["error"]
        bad = json.dumps({"address": {"regionCode": "JP", "addressLines": ["1-1 Chiyoda"]}}).encode()
        with pytest.raises(Exception) as e:
            urlopen(Request(f"{base}/v1/address:validate", bad, {"Content-Type": "application/json"}))
        assert getattr(e.value, "code", None) == 400
    finally:
        srv.shutdown()


# ---------------------------------------------------------------------------------------------- Google 覆盖的其他国家
def test_new_language_normalization():
    from avmvp.intl.text import fmt_postcode, norm_postcode
    # 日文：漢数字丁目、番地 / 号、全角数字与各种横线都统一成 "町名 N CHOME 番地-号"
    assert key("東京都千代田区丸の内二丁目7番9号", "JP") == key("東京都千代田区丸の内2-7-9", "JP") \
        == "東京都 千代田区 丸の内 2 CHOME 7-9"
    assert key("2 Chome-7-1 Yurakucho, Chiyoda City", "JP").startswith("YURAKUCHO 2 CHOME 7-1")
    assert key("銀座１丁目４−６", "JP") == "銀座 1 CHOME 4-6"
    # 保加利亚：西里尔文按官方规则转写，与拉丁写法对得上；ул. / St 都是 ULITSA
    assert core_key("ул. Пиротска", "BG") == core_key("Pirotska St", "BG") == "PIROTSKA"
    # 意大利文带点缩写、哥伦比亚 Cra. / Cl.、波兰 ł、丹麦 ø
    assert key("V.le Monza", "IT") == "VIALE MONZA" and key("C.so Buenos Aires", "IT") == "CORSO BUENOS AIRES"
    assert key("Cra. 14 # 66 - 33", "CO") == "CARRERA 14 # 66-33"
    assert key("ul. Marszałkowska", "PL") == key("ULICA MARSZALKOWSKA", "PL")
    assert key("Nørre Voldgade", "DK") == "NORRE VOLDGADE"
    # 邮编：存储时去掉空格 / 连字符 / 国家前缀，显示时按当地写法
    assert norm_postcode("LT-01120", "LT") == "01120" and norm_postcode("〒104-0028", "JP") == "1040028"
    assert norm_postcode("C1043AAZ", "AR") == "1043" and norm_postcode("M5V 2K4", "CA") == "M5V2K4"
    assert fmt_postcode("M5V2K4", "CA") == "M5V 2K4" and fmt_postcode("01310100", "BR") == "01310-100"
    assert fmt_postcode("11000", "CZ") == "110 00" and fmt_postcode("1040028", "JP") == "104-0028"


@pytest.fixture(scope="module")
def cz(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    nove = (14.41, 50.07, 14.44, 50.09)
    segs = [("Vodičkova", 50.080 + 0.0005 * i, 14.424) for i in range(4)]
    addrs = [("1935", "Vodičkova", "38", "11000", 50.0805, 14.4241),  # 登记号 1935 / 街道号 38
             ("699", "Vodičkova", "36", "11000", 50.0810, 14.4241)]
    _write(root / "CZ", [("Nové Město", "neighborhood", nove)], segs, [("Kavárna", "cafe", 50.075, 14.415)], addrs)
    return Engine("CZ", "rules", build("CZ", "A", log=lambda *_: None, root=root))


def test_czech_house_numbers(cz):
    """捷克门牌 = 登记号 / 街道号：只写街道号（日常写法）、写全两种都能逐门牌验真；单元字段不当作单元号。"""
    for text in ("Vodičkova 38, 110 00 Praha", "Vodičkova 1935/38, 110 00 Praha 1"):
        res = cz.validate(text)
        assert res.action == ACCEPT and res.granularity == "PREMISE", (text, res.reasons)
        assert res.best.point["number"] == "1935/38"
    assert "UNIT_MISSING_MULTI_UNIT_BUILDING" not in cz.validate("Vodičkova 38, Praha").reasons
    resp = cz.to_response(cz.validate("Vodičkova 38, 11000 Praha"))
    assert "110 00" in resp["result"]["address"]["formattedAddress"]


@pytest.fixture(scope="module")
def co(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    chapinero = (-74.07, 4.63, -74.05, 4.67)
    segs = [("Carrera 14", 4.640 + 0.001 * i, -74.062) for i in range(6)]
    segs += [("Calle 66", 4.647, -74.065 + 0.001 * i) for i in range(6)]
    addrs = [("66 33", "KR 14", "", "", 4.6475, -74.0620), ("66 45", "KR 14", "", "", 4.6478, -74.0620)]
    _write(root / "CO", [("Chapinero", "neighborhood", chapinero)], segs, [("Café", "cafe", 4.635, -74.068)], addrs)
    return Engine("CO", "rules", build("CO", "A", log=lambda *_: None, root=root))


def test_colombian_addresses(co):
    """哥伦比亚：Cra. 14 # 66-33 里的 # 标门牌（不是单元号）；地址表的 KR 14 / 66 33 与路网的 Carrera 14 是同一条路。"""
    for text in ("Cra. 14 # 66-33, Bogotá", "Carrera 14 #66 - 33, Chapinero, Bogotá D.C.", "KR 14 66-33"):
        res = co.validate(text)
        assert res.action == ACCEPT and res.granularity == "PREMISE", (text, res.reasons)
    far = co.validate("Cra. 14 # 70-10, Bogotá")  # 这个街区没有任何门牌：道路级 + 请用户确认
    assert far.action == CONFIRM and far.granularity == "ROUTE" and "PREMISE_NOT_FOUND" in far.reasons
    near = co.validate("Cra. 14 # 66-99, Bogotá")  # 同一街区（66-*）里有门牌：按相邻门牌给位置，请用户确认
    assert near.action == CONFIRM and near.granularity == "PREMISE_PROXIMITY" and "PREMISE_INTERPOLATED" in near.reasons
    assert "Carrera 14 # 66-33" in co.to_response(co.validate("Cra 14 # 66-33"))["result"]["address"][
        "formattedAddress"]


@pytest.fixture(scope="module")
def jp(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    m2 = (139.760, 35.675, 139.768, 35.682)
    areas = [(("丸の内二丁目", "Marunouchi 2"), "neighborhood", m2), (("千代田区", "Chiyoda"), "locality",
                                                                    (139.74, 35.66, 139.78, 35.70))]
    addrs = [("7-9", "丸の内二丁目", "", "", 35.6800, 139.7640), ("3-9", "丸の内二丁目", "", "", 35.6790, 139.7630)]
    _write(root / "JP", areas, [("外堀通り", 35.678 + 0.001 * i, 139.766) for i in range(3)],
           [("喫茶店", "cafe", 35.676, 139.761)], addrs)
    return Engine("JP", "rules", build("JP", "A", log=lambda *_: None, root=root))


def test_japanese_addresses(jp):
    """日本：町丁目 + 街区号验真；日文全写、简写、罗马字（片区英文名生成的别名）都能对上。"""
    for text in ("〒100-0005 東京都千代田区丸の内二丁目7番3号", "丸の内2-7-3, 千代田区", "東京都千代田区丸の内２丁目７−３",
                 "2 Chome-7-3 Marunouchi, Chiyoda City, Tokyo"):
        res = jp.validate(text)
        assert res.granularity == "PREMISE" and res.action == ACCEPT, (text, res.reasons, res.parsed.streets)
        assert abs(res.lat - 35.68) < 1e-3
    bad = jp.validate("丸の内2-99-1, 千代田区")  # 街区不存在：町丁目级 + 请用户确认
    assert bad.action == CONFIRM and "PREMISE_NOT_FOUND" in bad.reasons


def test_four_digit_postcode_vs_house_number():
    """欧洲 4 位邮编与门牌同形：单独成段（1070 Wien）才当邮编，道路后面的 4 位数是门牌。"""
    from avmvp.intl.reference import MarketReference
    ref = MarketReference("AT")
    rp = RuleParser(ref)
    assert rp.parse("Mariahilfer Straße 1200, Wien").postcode is None
    assert rp.parse("Mariahilfer Straße 120, 1070 Wien").postcode == "1070"
    assert rp.parse("1070 Wien, Mariahilfer Straße 120").postcode == "1070"


def test_parity_normalizations():
    """对标 Google 时补的写法统一（都来自开发集错例）。"""
    from avmvp.intl.parse import possessive_stem
    # 爱尔兰：Baggot Street Lower = Lower Baggot Street，Frederick St S = South Frederick Street；Upper Street 不动
    assert key("Baggot Street Lower", "IE") == key("Lower Baggot St", "IE") == "LOWER BAGGOT STREET"
    assert key("27 Frederick St S", "IE") == "27 SOUTH FREDERICK STREET" and key("Upper Street", "IE") == "UPPER STREET"
    # 斯拉夫语物主形容词与"名 + 姓属格"两种路名（含游移 e：Basaričekova / Basaričeka / Basarička）
    assert possessive_stem("GAJEVA") == possessive_stem("GAJA")
    assert possessive_stem("BASARICEKOVA") == possessive_stem("BASARICEKA") == possessive_stem("BASARICKA")
    assert possessive_stem("STUROVA") == possessive_stem("STURA")
    # 葡萄牙地址表缩写；西 / 葡语数字词
    assert key("AV DQ DE LOULE", "PT") == key("Avenida Duque de Loulé", "PT")
    assert key("R D INÊS DE CASTRO", "PT") == key("Rua Dona Inês de Castro", "PT")
    assert key("Av. Diez de Julio", "CL") == key("Avenida 10 de Julio", "CL")
    assert key("Rua Quinze de Novembro", "BR") == key("Rua 15 de Novembro", "BR")
    # 保加利亚 ж.к.（住宅小区）；印度 Marg = Road
    assert key("ж.к. Младост 1", "BG") == key("жк Младост 1", "BG") == "ZHK MLADOST 1"
    assert core_key("Sane Guruji Marg", "IN") == core_key("Sane Guruji Road", "IN")
    # 日文：2-chōme-17 Asakusa、九段北4（只写丁目）、上目黒, 3丁目、"Tokyo, 1 Chome-24-15 Shibuya"
    assert key("2-chōme-17 Asakusa", "JP") == "ASAKUSA 2 CHOME 17"
    assert key("千代田区九段北4", "JP") == "千代田区 九段北 4 CHOME"
    assert key("上目黒, 3丁目32-5", "JP") == "上目黒 3 CHOME 32-5"
    assert key("Tokyo, 1 Chome-24-15 Shibuya", "JP") == "TOKYO SHIBUYA 1 CHOME 24-15"


def test_osm_house_numbers_and_road_refs():
    from avmvp.intl.reference import _osm_number, _road_ref_names, street_names
    assert _osm_number("NZ", "14/59", "") == ("59", "14")  # 澳洲 / 新西兰：单元 / 门牌
    assert _osm_number("EE", "103/16", "") == ("103/16", "")
    assert _osm_number("DE", "12;14", "") == ("12", "")
    assert _road_ref_names("PR", "PR-25;PR-1") == ["CARRETERA 25", "CARRETERA 1"]
    assert _road_ref_names("IE", "N11") == ["N11"] and _road_ref_names("IE", "12") == []
    assert street_names({"primary": "RK Patkar Marg (Waterfield Road)"}) == [
        "RK Patkar Marg (Waterfield Road)", "Waterfield Road", "RK Patkar Marg"]
    assert street_names({"primary": "Calle 5 (Peatonal)"}) == ["Calle 5 (Peatonal)", "Calle 5"]


@pytest.fixture(scope="module")
def cl(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    cisterna, quilicura = (-70.67, -33.54, -70.65, -33.52), (-70.73, -33.37, -70.71, -33.35)
    florida = (-70.62, -33.52, -70.60, -33.50)
    segs = [("Gran Avenida José Miguel Carrera", -33.538 + 0.002 * i, -70.662) for i in range(8)]
    segs += [("Avenida Vicuña Mackenna", -33.470 + 0.002 * i, -70.625) for i in range(4)]
    segs += [("Avenida Vicuña Mackenna Poniente", -33.516 + 0.002 * i, -70.6105) for i in range(4)]  # 双向分开的两侧
    segs += [("Avenida Las Torres", -33.364 + 0.002 * i, -70.719) for i in range(3)]
    segs += [("Avenida Las Torres", -33.465 + 0.002 * i, -70.731) for i in range(3)]
    addrs = [("8193", "GRAN AVENIDA JOSE MIGUEL CARRERA", "", "", -33.5295, -70.6625),
             ("8201", "GRAN AVENIDA JOSE MIGUEL CARRERA", "", "", -33.5300, -70.6625),
             ("1200", "AVENIDA VICUNA MACKENNA", "", "", -33.4690, -70.6250),
             ("6100", "AVENIDA VICUNA MACKENNA PONIENTE", "", "", -33.5114, -70.6103),
             ("091", "AVENIDA LAS TORRES", "", "", -33.3642, -70.7192),
             ("85", "AVENIDA LAS TORRES", "", "", -33.4650, -70.7308)]
    _write(root / "CL", [("La Cisterna", "locality", cisterna), ("Quilicura", "locality", quilicura),
                         ("La Florida", "locality", florida)], segs,
           [("Café", "cafe", -33.53, -70.66)], addrs)
    return Engine("CL", "rules", build("CL", "A", log=lambda *_: None, root=root))


def test_completed_names_and_chilean_numbers(cl):
    """智利：所写道路上没有这个门牌、全称多一个词的同名路上有（Vicuña Mackenna 6100 = Vicuña Mackenna Poniente 6100），
    按片区印证后给门牌位置并请用户确认；千位点（8.193）；圣地亚哥门牌前的 0 可以省略（Las Torres 91 = 091）。"""
    res = cl.validate("Av. Vicuña Mackenna 6100, La Florida")
    assert res.granularity == "PREMISE" and res.action == CONFIRM and "STREET_NAME_COMPLETED" in res.reasons
    assert abs(res.lat + 33.5114) < 1e-3
    assert "STREET_NAME_COMPLETED" not in cl.validate("Av. Vicuña Mackenna 6100, Quilicura").reasons  # 没有印证不用
    res = cl.validate("Gran Avenida José Miguel Carrera N° 8.193, La Cisterna")
    assert res.granularity == "PREMISE" and res.best.point["number"] == "8193"
    res = cl.validate("Av. Las Torres 91, Quilicura")
    assert res.granularity == "PREMISE" and res.best.point["number"] == "091"
    assert key("Tobalaba N° 14.007", "CL") == "TOBALABA N 14007" and key("Av. Paulista, 1.636", "BR").endswith(" 1636")
    assert "1636" not in key("12.1.636", "BR") and key("Kreuzg. 1.636", "AT").endswith("1 636")  # 只在这几个市场、只合并 x.xxx


def test_noise_stripping_multilingual():
    """噪声剥离：HTML / 转义换行、"地址："标签、电话、订单号、营业时间、收件人、公司名、配送备注、度分秒坐标都单独返回，
    不进入地址解析；营业时间里的 9:00 不能当门牌。"""
    from avmvp.intl.noise import strip_noise as sn
    assert sn("<p>Rua Diana<br>777<br>São Paulo</p>")[0] == "Rua Diana, 777, São Paulo"
    assert sn("Rua Diana\\n777\\nSão Paulo")[0] == "Rua Diana, 777, São Paulo"
    assert sn("Dirección: C. Velilla, 7, Madrid")[0] == "C. Velilla, 7, Madrid"
    text, noise, codes = sn("Unit 4, Naas Rd, Dublin, D12 A3VR, Mon-Fri 9:00-18:00")
    assert text == "Unit 4, Naas Rd, Dublin, D12 A3VR" and noise["openingHours"] == ["Mon-Fri 9:00-18:00"]
    text, noise, _ = sn("Alla c.a. Sig. Mario Rossi, Via Montenapoleone 1, Milano")
    assert text == "Via Montenapoleone 1, Milano" and noise["recipients"] == ["Sig. Mario Rossi"]
    text, noise, _ = sn("Distribuciones García S.A. de C.V., Tuxpan 39, Cuauhtémoc, 06760")
    assert text == "Tuxpan 39, Cuauhtémoc, 06760" and noise["organizations"]
    text, noise, _ = sn("Müller GmbH, Friedrichstraße 43, 10117 Berlin, bitte beim Nachbarn abgeben, Tel. +49 30 1234567")
    assert text == "Friedrichstraße 43, 10117 Berlin" and noise["notes"] and noise["phones"] and noise["organizations"]
    text, noise, _ = sn("Order #A1234567, 36 Abbott Rd, Sydney, Tel: (11) 98765-4321")
    assert text == "36 Abbott Rd, Sydney" and noise["orderRefs"] and noise["phones"]
    assert sn("56°57'10.9N 24°05'11.3E, Balasta dambis, Rīga")[2]["latlng"] == "56.953028,24.086472"
    # 方位描述：第几栋整段剥出，参照物单独记下（只拿去找楼宇 / 商户）；参照物本身是地址时照常解析，但记为 relativeTo
    text, noise, _ = sn("segunda casa después del árbol grande, portón azul")
    assert text == "portón azul" and noise["descriptions"] and noise["landmarks"] == ["ARBOL GRANDE"]
    text, noise, _ = sn("Avenida Paulista, perto do metrô Consolação")
    assert text == "Avenida Paulista" and noise["landmarks"] == ["METRO CONSOLACAO"]
    assert sn("Avenida Paulista perto do metrô")[0] == "AVENIDA PAULISTA"  # 同一段里：方位词前面的留下
    text, noise, _ = sn("drittes Haus hinter Horstweg 53C")
    assert text == "HORSTWEG 53C" and noise["relativeTo"] == ["HORSTWEG 53C"]


def test_noisy_and_descriptive_inputs(au):
    """带收件人 / 备注 / 电话 / 营业时间的地址照常逐门牌验真；只有方位描述的：参照物是已知楼宇时定位到楼宇附近并请用户确认，
    参照物本身是地址时不直接通过，什么都对不上时判 FIX（DESCRIPTIVE_LOCATION）。"""
    res = au.validate("Attn: John Smith, 100 Crown Street, Surry Hills, 2010, please leave at reception, "
                      "Tel: 0412 345 678, Mon-Fri 9:00-17:00")
    assert res.action == ACCEPT and res.best.point["number"] == "100"
    assert {"recipients", "notes", "phones", "openingHours"} <= set(res.parsed.noise)
    res = au.validate("third house behind Crown Street Public School")
    assert res.action == CONFIRM and "LANDMARK_RELATIVE" in res.reasons and res.granularity == "PREMISE_PROXIMITY"
    res = au.validate("third house behind 100 Crown Street, Surry Hills")
    assert res.action == CONFIRM and "LANDMARK_RELATIVE" in res.reasons
    res = au.validate("second house after the big tree, blue gate")
    assert res.action == FIX and "DESCRIPTIVE_LOCATION" in res.reasons


def _geo(number, route, postcode, lat, lng, loc_type="ROOFTOP", locality="Surry Hills"):
    comps = [{"long_name": number, "types": ["street_number"]}] if number else []
    comps += [{"long_name": route, "types": ["route"]}, {"long_name": locality, "types": ["locality"]}]
    comps += [{"long_name": postcode, "types": ["postal_code"]}] if postcode else []
    return {"results": [{"address_components": comps,
                         "geometry": {"location": {"lat": lat, "lng": lng}, "location_type": loc_type}}]}


def test_geo_result_verification(au):
    """geo 服务的门址代回输入核对：逐字段一致才直接通过；门牌 / 道路对不上时以本引擎为准；
    输入没写门牌时 geo 补出来的门牌不能当真；geo 只到道路级时不采用。"""
    from avmvp.intl.geo_check import parse_geo, validate_with_geo
    g = parse_geo(_geo("100", "Crown Street", "2010", -33.8850, 151.2121))[0]
    assert (g.number, g.route, g.postal_code, g.localities) == ("100", "Crown Street", "2010", ["Surry Hills"])
    # 一致：直接通过，本引擎独立定位到同一处
    res = validate_with_geo(au, "100 Crown St, Surry Hills NSW 2010", _geo("100", "Crown Street", "2010", -33.8850, 151.2121))
    assert res.action == ACCEPT and "GEO_VERIFIED" in res.reasons and "GEO_CONFIRMED_BY_ENGINE" in res.reasons
    # geo 吸附到了别的门牌（输入 104，geo 给 100）：门牌冲突，用本引擎的结论
    res = validate_with_geo(au, "104 Crown St, Surry Hills NSW 2010", _geo("100", "Crown Street", "2010", -33.8850, 151.2121))
    assert "GEO_NUMBER_CONFLICT" in res.reasons and "GEO_REJECTED" in res.reasons and res.best.point["number"] == "104"
    # geo 解析成了另一条路：道路冲突，用本引擎的结论
    res = validate_with_geo(au, "50 Bourke St, Surry Hills NSW 2010", _geo("50", "Crown Street", "2010", -33.8860, 151.2121))
    assert "GEO_ROUTE_CONFLICT" in res.reasons and res.action == ACCEPT and res.best.point["number"] == "50"
    # 输入没写门牌：geo 补出来的门牌不能当真
    res = validate_with_geo(au, "Crown St, Surry Hills NSW 2010", _geo("100", "Crown Street", "2010", -33.8850, 151.2121))
    assert res.action == FIX
    # geo 只到道路级：不采用
    res = validate_with_geo(au, "100 Crown St, Surry Hills", _geo("", "Crown Street", "", -33.886, 151.212, "GEOMETRIC_CENTER"))
    assert "GEO_STREET_LEVEL_ONLY" in res.reasons and res.best.point["number"] == "100"
    # 库里没有的门牌但 geo 有（geo 的门址库更全）：逐字段一致，直接通过
    res = validate_with_geo(au, "110 Crown St, Surry Hills NSW 2010", _geo("110", "Crown Street", "2010", -33.8858, 151.2121))
    assert res.action == ACCEPT and "GEO_VERIFIED" in res.reasons and res.lat == -33.8858
    # 拼写不同：请用户确认
    res = validate_with_geo(au, "110 Crwn St, Surry Hills NSW 2010", _geo("110", "Crown Street", "2010", -33.8858, 151.2121))
    assert res.action == CONFIRM
    # 没有结果：本引擎
    assert "GEO_NO_RESULT" in validate_with_geo(au, "100 Crown St, Surry Hills", {"results": []}).reasons


@pytest.fixture(scope="module")
def au_cov(tmp_path_factory):
    """微型"悉尼"+ 全国地名 / 邮编表（试点范围外有卧龙岗、布里斯班），测试范围守卫。"""
    import gzip
    root = tmp_path_factory.mktemp("markets")
    surry = (151.200, -33.895, 151.220, -33.880)
    segs = [("Crown Street", -33.884 - 0.001 * i, 151.212) for i in range(6)]
    addrs = [("100", "Crown Street", "", "2010", -33.8850, 151.2121)]
    _write(root / "AU", [("Surry Hills", "neighborhood", surry)], segs,
           [("Crown Street Public School", "elementary_school", -33.8870, 151.2125)], addrs)
    places = [[["Sydney"], -33.8688, 151.2093, "P", 5000000, "02"],
              [["Surry Hills"], -33.885, 151.211, "X", 15000, "02"],
              [["Wollongong"], -34.424, 150.893, "P", 300000, "02"],
              [["Brisbane"], -27.47, 153.02, "P", 2000000, "04"],
              [["State of Queensland", "Queensland"], -22.5, 144.5, "A1", 5000000, "04"],
              [["State of New South Wales", "New South Wales"], -32.0, 147.0, "A1", 8000000, "02"]]
    pcs = [["2500", "Wollongong", -34.42, 150.89], ["2010", "Surry Hills", -33.885, 151.211],
           ["4000", "Brisbane", -27.47, 153.02]]
    with gzip.open(root / "AU" / "gazetteer.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"places": places, "postcodes": pcs}, f)
    return Engine("AU", "rules", build("AU", "A", log=lambda *_: None, root=root))


def test_outside_coverage_guard(au_cov):
    """写的城镇 / 邮编 / 州都在试点范围外：不再匹配试点城市里的同名路，只给城镇级位置并请用户确认；
    geo 门址与输入逐字段一致（门牌、道路、所写城镇 / 邮编附近）时可以采用，geo 选了试点城市的同名路则不采用。"""
    from avmvp.intl.geo_check import validate_with_geo
    res = au_cov.validate("100 Crown St, Surry Hills NSW 2010")
    assert res.action == ACCEPT and res.coverage.status == "INSIDE"
    assert au_cov.validate("100 Crown St, Sydney").coverage.status == "INSIDE"
    # 卧龙岗的 Crown Street：试点参考库里没有，不能匹配到悉尼的同名路
    res = au_cov.validate("100 Crown St, Wollongong NSW 2500")
    assert res.coverage.status == "OUTSIDE" and "OUTSIDE_COVERAGE" in res.reasons
    assert res.action == CONFIRM and res.granularity == "LOCALITY" and res.best is None
    assert abs(res.lat - -34.42) < 0.05 and res.components["locality"]["text"] == "Wollongong"
    res = au_cov.validate("100 Crown Street, Brisbane, Queensland")
    assert res.coverage.status == "OUTSIDE" and res.coverage.place == "Brisbane"
    assert au_cov.validate("Crown Street, Wollongong").action == FIX  # 没写门牌：请用户补全
    # 范围外 + geo：逐字段一致 -> 采用 geo；geo 给的是悉尼的同名路 -> 所写城镇里没有这处，不采用
    ok = _geo("100", "Crown Street", "2500", -34.425, 150.89, locality="Wollongong")
    res = validate_with_geo(au_cov, "100 Crown St, Wollongong NSW 2500", ok)
    assert res.action == ACCEPT and {"OUTSIDE_COVERAGE", "GEO_VERIFIED"} <= set(res.reasons)
    bad = _geo("100", "Crown Street", "2010", -33.8850, 151.2121)
    res = validate_with_geo(au_cov, "100 Crown St, Wollongong NSW 2500", bad)
    assert "GEO_REJECTED" in res.reasons and res.granularity == "LOCALITY" and res.lat < -34.3


def test_amap_geo_format_and_route_text_match():
    """高德海外地理编码格式：street / number 拆错时按 formatted_address 重拆、单元截掉、乱码还原；
    路名只和原文的道路段比（城镇名冒充路名判冲突），跨语言类型词、缩写、只写姓算对上。"""
    import re
    from avmvp.intl.geo_check import parse_geo
    from avmvp.intl.geo_text import route_match

    def amap(fa, street, number):
        return {"status": "1", "geocodes": [{"formatted_address": fa, "street": street, "number": number,
                                             "location": "16.2465,50.4425", "city": "x", "district": []}]}
    g = parse_geo(json.dumps(amap("ULICA 1 MAJA 3", "1 MAJA 3", "ULICA")))[0]
    assert (g.number, g.route, g.lat) == ("3", "ULICA 1 MAJA", 50.4425)
    g = parse_geo(amap("AVENIDA JOAO FRANCESCHI 2101, BLOCO 2, APTO 303", "AVENIDA JOAO FRANCESCHI 2101, BLOCO 2", "AVENIDA"))[0]
    assert (g.number, g.route) == ("2101", "AVENIDA JOAO FRANCESCHI")
    g = parse_geo(amap("Avenida MÃ©xico 27", "Avenida MÃ©xico", "27"))[0]
    assert g.route == "Avenida México"
    pl = re.compile(r"\b\d{2}-\d{3}\b")
    assert route_match("HAMILTON ROAD", "12 auchingramont rd, hamilton, ml3 6jt, Hamilton") == "CONFLICT"
    assert route_match("Акжар улица", "Акжар, улица Даулеткерея 32, Алматы") == "CONFLICT"
    assert route_match("CALLE 46D", "Calle 16 #22-53 apto 401, MANIZALES") == "CONFLICT"
    assert route_match("Carrer del Torrent de Can Miano", "5, Torrent de Can Miano, Barcelona") == "CONFIRMED"
    assert route_match("Straße der Nationen", "Str. d. Nationen 5, Hannover") == "CONFIRMED"
    assert route_match("ULICA ZOFII KOSSAK-SZCZUCKIEJ", "ul. Kossak-Szczuckiej 14, 59-241 Legnickie Pole", pl) == "CONFIRMED"
    assert route_match("R. Limeira", "Rua Limeira 179 fundo casa, Mogi Guaçu, São Paulo") == "CONFIRMED"
    assert route_match("Calle Isabel Clara Eugenia", "Calle De Isabel Clara Eujenia 14, Madrid") == "CORRECTED"


def test_geo_check_without_reference_data():
    """没有参考库的国家：门牌、道路对上且坐标在所写城镇里 -> 直接通过；门牌冲突 -> FIX；
    坐标不在所写城镇 -> FIX；编号路名（شارع 18）同城很多条 -> 最多请用户确认。"""
    from avmvp.intl import geo_free
    idx = geo_free.TownIndex("ZZ")
    idx.names = {"LIMA": [(-12.05, -77.04, 20000.0)], "AREQUIPA": [(-16.40, -71.54, 15000.0)]}
    geo_free._TOWNS["ZZ"] = idx

    def amap(fa, lat, lng):
        street, num = fa.rsplit(" ", 1)
        return {"geocodes": [{"formatted_address": fa, "street": street, "number": num, "location": f"{lng},{lat}"}]}
    res = geo_free.validate_free("ZZ", "Jr. Los Eucaliptos 371, Lima, Perú", amap("Jirón Los Eucaliptos 371", -12.06, -77.03))
    assert res.action == "ACCEPT" and "GEO_VERIFIED" in res.reasons
    res = geo_free.validate_free("ZZ", "Jr. Los Eucaliptos 371, Lima, Perú", amap("Jirón Los Eucaliptos 37", -12.06, -77.03))
    assert res.action == "FIX" and "GEO_NUMBER_CONFLICT" in res.reasons
    res = geo_free.validate_free("ZZ", "Jr. Los Eucaliptos 371, Lima, Perú", amap("Jirón Los Eucaliptos 371", -16.40, -71.54))
    assert res.action == "FIX" and "AREA_STREET_MISMATCH" in res.reasons
    res = geo_free.validate_free("ZZ", "منزل 20 شارع 18, Lima", amap("شارع 18 20", -12.06, -77.03))
    assert res.action == "CONFIRM" and "GEO_AMBIGUOUS" in res.reasons
    out = geo_free.to_response(geo_free.validate_free("ZZ", "Jr. Los Eucaliptos 371, Lima", amap("Jirón Los Eucaliptos 371", -12.06, -77.03)))
    assert out["result"]["verdict"]["possibleNextAction"] == "ACCEPT" and out["result"]["metadata"]["marketClass"] == "none"
