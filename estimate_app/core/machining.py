"""가공 조건(회전수·이송·가공 시간 등) 계산. 화면과 분리된 순수 함수만 둔다(v0.1.1).

Lathe 쪽은 `04.CSS_조건 산출기.hta`의 doCalc()/applyRecommendation()을 상수 하나까지
그대로 옮긴 것이다(장비 PUMA 2600Y 22kW/3500RPM, 인서트 대구텍 CNMG120408 기준 데이터는
core/settings.py의 DEFAULT_LATHE_* 에 있다). 옮기면서 식이나 분기를 하나도 바꾸지 않았다
-- 바꾸면 이식이 아니라 개조가 된다(plan.md 2026-08-09 v0.1.1 항목 참고).

Mill 쪽은 `01.견적_산출_입력.hta`에 계산식이 아예 없어(파일 안에 "산출 방식과 계산
방식은 다음 단계에서 연결 예정"이라 적혀 있다) v0.1.1에서 새로 설계했다. 표준 밀링
공식(n/Vf/Q/Pc)을 쓰고, 로드 형상은 Lathe의 회전체 부피 식과 같은 모양을 쓴다
(요청 2 "로드 계열은 계산식이 없음, mill 계열 참조"에 대한 해석).
"""

import math

SFM_FACTOR = 3.28084


# ---------- Lathe (04.hta 이식) ----------

def lathe_sfm_from_v(v):
    return round(v * SFM_FACTOR)


def lathe_v_from_sfm(sfm):
    return round(sfm / SFM_FACTOR, 1)


def apply_lathe_recommendation(rec, max_power, base_power, machine_max_rpm):
    """재질을 고르면 자동으로 채워지는 V/F/Ap/G50 (04.hta applyRecommendation 이식).

    rec: {"v", "f", "ap", "max_rpm"} -- 재질표 한 행(core/settings.DEFAULT_LATHE_MATERIALS).
    동력 스케일은 0.2~1.5로 제한한다. ap는 동력에 선형 비례(주 조정), f는 제곱근
    비례(이송은 가공 품질을 지키려 완만하게 조정) -- 04.hta 주석 그대로다.
    """
    power = max_power if max_power and max_power > 0 else base_power
    power_scale = min(1.5, max(0.2, power / base_power))
    sqrt_scale = math.sqrt(power_scale)
    return {
        "v": rec["v"],
        "f": round(rec["f"] * sqrt_scale, 3),
        "ap": round(rec["ap"] * power_scale, 2),
        "g50": min(rec["max_rpm"], machine_max_rpm),
        "power_scale": power_scale,
    }


def calc_lathe(kc, d_max, d_min, v, g50, feed, ap, length, max_power, base_power):
    """04.hta doCalc()의 선삭 계산 부분.

    d_max < d_min이면(오류 입력) 04.hta와 마찬가지로 값을 그대로 계산해서 돌려준다
    (화면에서 두 입력칸을 오류로 표시하는 것과 별개다) -- `dmax_lt_dmin` 플래그로 알린다.
    """
    min_rpm = max_rpm = 0.0
    if v > 0:
        if d_max > 0:
            min_rpm = 1000 * v / (math.pi * d_max)
            if g50 > 0:
                min_rpm = min(min_rpm, g50)
        if d_min > 0:
            max_rpm = 1000 * v / (math.pi * d_min)
            if g50 > 0:
                max_rpm = min(max_rpm, g50)

    feed_min = min_rpm * feed
    mrr = v * ap * feed
    force_kg = (ap * feed * kc) / 9.81
    total_vol = max((math.pi * (d_max * d_max - d_min * d_min) * length) / 4000, 0.0)

    passes, total_sec = 0, 0.0
    radial_margin = (d_max - d_min) / 2
    face_only = length <= 1.6
    if radial_margin > 0:
        if face_only:
            passes = 1
            if feed_min > 0:
                total_sec = (radial_margin / feed_min) * 60
        else:
            if ap > 0:
                passes = math.ceil(radial_margin / ap)
            if feed_min > 0 and length > 0 and passes > 0:
                total_sec = (length / feed_min) * 60 * passes

    power_kw = (ap * feed * v * kc) / 60000
    load_rate = (power_kw / max_power * 100) if max_power > 0 else 0.0
    spindle_load = (power_kw / base_power * 100) if base_power > 0 else 0.0
    total_kwh = power_kw * (total_sec / 3600) if total_sec > 0 and power_kw > 0 else 0.0

    return {
        "min_rpm": min_rpm, "max_rpm": max_rpm, "feed_min": feed_min,
        "mrr": mrr, "force_kg": force_kg, "total_vol": total_vol,
        "passes": passes, "total_sec": total_sec, "face_only": face_only,
        "power_kw": power_kw, "load_rate": load_rate, "spindle_load": spindle_load,
        "total_kwh": total_kwh, "sfm": lathe_sfm_from_v(v),
        "dmax_lt_dmin": d_max < d_min,
    }


# ---------- Mill (v0.1.1 신설) ----------

def calc_mill(kc, tool_d, flutes, vc, fz, ap, ae, max_rpm, shape, stock, target,
              max_power, base_power):
    """표준 밀링 식(n/Vf/Q/Pc)으로 제거 체적과 가공 시간을 낸다.

    shape="block"이면 stock/target에 t,w,l(mm)을 담는다(소재·목표 치수가 각각 다른
    길이여도 된다 -- 3면 모두 깎아 낼 수 있어서다).
    shape="rod"이면 stock에 d,l을, target에는 d만 담는다 -- 목표 지름만 줄고 길이는
    그대로라고 본다(Lathe의 로드 계산과 같은 구조. 요청 2의 해석. 목표 길이를 따로 받지
    않는다).
    필요한 치수가 비어 있으면(0 이하) 그 항목의 부피는 0으로 본다 -- 추측해서 채우지 않는다.
    """
    n = 0.0
    if tool_d and tool_d > 0 and vc > 0:
        n = 1000 * vc / (math.pi * tool_d)
        if max_rpm > 0:
            n = min(n, max_rpm)
    feed_min = n * fz * flutes
    mrr = ae * ap * feed_min / 1000  # cm3/min
    power_kw = (mrr * kc) / 60000

    volume = 0.0
    if shape == "block":
        stock_vol = stock.get("t", 0) * stock.get("w", 0) * stock.get("l", 0)
        target_vol = target.get("t", 0) * target.get("w", 0) * target.get("l", 0)
        volume = max((stock_vol - target_vol) / 1000, 0.0)
    elif shape == "rod":
        d0, l0 = stock.get("d", 0), stock.get("l", 0)
        d1 = target.get("d", 0)
        volume = max((math.pi * (d0 * d0 - d1 * d1) * l0) / 4000, 0.0)

    total_sec = (volume / mrr) * 60 if mrr > 0 else 0.0
    load_rate = (power_kw / max_power * 100) if max_power > 0 else 0.0
    spindle_load = (power_kw / base_power * 100) if base_power > 0 else 0.0

    return {
        "rpm": n, "feed_min": feed_min, "mrr": mrr, "power_kw": power_kw,
        "volume": volume, "total_sec": total_sec,
        "load_rate": load_rate, "spindle_load": spindle_load,
    }


# ---------- 공통 표시 ----------

def seconds_to_text(total_sec):
    """04.hta의 시간 표기(`h시간 m분 s초`)와 같은 형식으로 만든다.

    04.hta처럼 시/분은 내림(floor), 초만 반올림한다 -- 반올림 방식이 섞이면 표시가
    plan.md의 검증 대조표와 어긋난다.
    """
    if total_sec <= 0:
        return "0초"
    hours = int(total_sec // 3600)
    minutes = int((total_sec % 3600) // 60)
    seconds = round(total_sec % 60)
    parts = []
    if hours:
        parts.append(f"{hours}시간")
    if minutes or hours:
        parts.append(f"{minutes}분")
    parts.append(f"{seconds}초")
    return " ".join(parts)


def seconds_to_hours(total_sec):
    """카드의 공정 시간칸(h 단위)에 눈으로 옮겨 적을 수 있도록 시간으로 환산한다."""
    return round(total_sec / 3600, 2)
