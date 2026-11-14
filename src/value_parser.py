
import re
from decimal import Decimal


def parse_value(value):
    suffixes = {
        "k": Decimal("1e3"),
        "M": Decimal("1e6"),
        "m": Decimal("1e-3"),
        "u": Decimal("1e-6"),
        "n": Decimal("1e-9"),
        "p": Decimal("1e-12")
    }

    value = value.strip()

    pattern = r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)([kMmunp]?)$"

    if not re.fullmatch(pattern, value):
        raise ValueError("Invalid engineering value: " + value)

    suffix = value[-1]

    if suffix in suffixes:
        return Decimal(value[:-1]) * suffixes[suffix]

    return Decimal(value)


def check_tolerance(measured, nominal, tolerance):
    tolerance = Decimal(str(tolerance))

    lower_limit = nominal * (
        Decimal("1") - tolerance / Decimal("100")
    )

    upper_limit = nominal * (
        Decimal("1") + tolerance / Decimal("100")
    )

    return "IN" if lower_limit <= measured <= upper_limit else "OUT"


def get_sample_size(lot_size):
    if lot_size <= 500:
        return 20
    elif lot_size <= 3200:
        return 50
    return 80


def get_acceptance_number(sample_size):
    if sample_size == 20:
        return 1
    elif sample_size == 50:
        return 3
    elif sample_size == 80:
        return 5

    raise ValueError("Invalid sample size")


def get_lot_decision(out_count, acceptance_number):
    if out_count <= acceptance_number:
        return "ACCEPTED"
    elif out_count <= acceptance_number + 2:
        return "SCREEN_100"
    return "REJECTED"


def check_sample_availability(required, available):
    return "HELD" if available < required else "READY"


def check_wrong_value_suspected(beyond_3x_count, out_count):
    if out_count == 0:
        return False

    return beyond_3x_count > out_count / 2


def evaluate_lot(required_samples, available_samples,
                 in_count, out_count, beyond_3x_count):

    if available_samples < required_samples:
        return "HELD", "INSUFFICIENT_SAMPLE"

    if check_wrong_value_suspected(beyond_3x_count, out_count):
        return "REJECTED", "WRONG_VALUE_SUSPECTED"

    acceptance_number = get_acceptance_number(required_samples)
    decision = get_lot_decision(out_count, acceptance_number)

    if decision == "ACCEPTED":
        return decision, "OK"

    return decision, "COUNT"


def is_beyond_three_x_tolerance(measured, nominal, tolerance_pct):
    tolerance_pct = Decimal(str(tolerance_pct))

    allowed_deviation = (
        nominal * tolerance_pct / Decimal("100")
    )

    return abs(measured - nominal) > (
        Decimal("3") * allowed_deviation
    )
