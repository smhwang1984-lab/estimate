"""견적 금액 계산. 화면과 엑셀이 같은 규칙을 쓰도록 이 모듈만 본다."""

from .config import MACHINE_KEYS


def calc_row(item, rates):
    """(시간합계, 단가합계, 최종금액)을 돌려준다. 최종금액은 1,000원 단위 내림."""
    sum_time = sum(float(item.get(key, 0) or 0) for key in MACHINE_KEYS)
    cost_sum = sum(float(item.get(key, 0) or 0) * rates[key] for key in MACHINE_KEYS)
    unit_price = cost_sum * item.get("qty", 1)
    final_price = int(unit_price // 1000 * 1000)
    return sum_time, unit_price, final_price


def calc_total_amount(items, rates):
    return sum(calc_row(item, rates)[2] for item in items)
