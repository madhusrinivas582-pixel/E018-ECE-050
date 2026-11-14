
import csv
import os
from collections import defaultdict
from datetime import date
from decimal import Decimal

from value_parser import (
    parse_value,
    check_tolerance,
    get_sample_size,
    get_acceptance_number,
    evaluate_lot,
    is_beyond_three_x_tolerance
)


def load_csv(filename):
    with open(filename, "r", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(filename, headers, rows):
    os.makedirs("output", exist_ok=True)

    with open(filename, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


# Data loaded through commands.txt
specifications = None
suppliers = None
lots = None
measurements = None

lot_results = []
parse_errors = []
supplier_scorecard = []
evaluated = False


def evaluate_all_lots():
    global lot_results, parse_errors, evaluated

    specs_by_part = {
        spec["part_no"]: spec for spec in specifications
    }

    measurements_by_lot = defaultdict(list)

    for measurement in measurements:
        measurements_by_lot[measurement["lot_id"]].append(
            measurement
        )

    lot_results = []
    parse_errors = []

    for lot in sorted(lots, key=lambda x: x["lot_id"]):
        lot_id = lot["lot_id"]
        part = specs_by_part[lot["part_no"]]

        nominal = parse_value(part["nominal_value"])
        tolerance = Decimal(part["tolerance_pct"])

        lot_size = int(lot["lot_size"])
        required = get_sample_size(lot_size)
        acceptance_number = get_acceptance_number(required)

        all_samples = sorted(
            measurements_by_lot[lot_id],
            key=lambda x: int(x["sample_no"])
        )

        selected_samples = all_samples[:required]

        in_count = 0
        out_count = 0
        unparseable_count = 0
        beyond_3x_count = 0

        for measurement in selected_samples:
            try:
                measured = parse_value(
                    measurement["measured_value"]
                )

                result = check_tolerance(
                    measured, nominal, tolerance
                )

                if result == "IN":
                    in_count += 1
                else:
                    out_count += 1

                    if is_beyond_three_x_tolerance(
                        measured, nominal, tolerance
                    ):
                        beyond_3x_count += 1

            except ValueError:
                out_count += 1
                unparseable_count += 1

                parse_errors.append({
                    "lot_id": lot_id,
                    "sample_no": measurement["sample_no"],
                    "measured_value": measurement["measured_value"]
                })

        decision, reason = evaluate_lot(
            required,
            len(all_samples),
            in_count,
            out_count,
            beyond_3x_count
        )

        lot_results.append({
            "lot_id": lot_id,
            "part_no": lot["part_no"],
            "supplier_id": lot["supplier_id"],
            "lot_size": lot_size,
            "sample_size": required,
            "samples_used": len(selected_samples),
            "in_count": in_count,
            "out_count": out_count,
            "unparseable_count": unparseable_count,
            "acceptance_no": acceptance_number,
            "decision": decision,
            "reason": reason
        })

    write_csv(
        "output/lot_decisions.csv",
        [
            "lot_id", "part_no", "supplier_id", "lot_size",
            "sample_size", "samples_used", "in_count",
            "out_count", "unparseable_count", "acceptance_no",
            "decision", "reason"
        ],
        lot_results
    )

    write_csv(
        "output/parse_errors.csv",
        ["lot_id", "sample_no", "measured_value"],
        parse_errors
    )

    evaluated = True
    print("Lot evaluation completed.")
    print("Total lots:", len(lot_results))
    print("Parse errors:", len(parse_errors))


def generate_scorecard(start_date, end_date):
    global supplier_scorecard

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    if end < start:
        raise ValueError("Scorecard end date is before start date.")

    results_by_lot = {
        result["lot_id"]: result for result in lot_results
    }

    stats = defaultdict(lambda: {"lots": 0, "accepted": 0})

    for lot in lots:
        received = date.fromisoformat(lot["received_date"])

        if start <= received <= end:
            supplier = lot["supplier_id"]
            stats[supplier]["lots"] += 1

            if results_by_lot[lot["lot_id"]]["decision"] == "ACCEPTED":
                stats[supplier]["accepted"] += 1

    supplier_scorecard = []

    # Include suppliers even if they have no lots in this period.
    for supplier in sorted(
        item["supplier_id"] for item in suppliers
    ):
        lots_count = stats[supplier]["lots"]
        accepted = stats[supplier]["accepted"]

        score = (
            round((accepted / lots_count) * 100, 1)
            if lots_count else 0.0
        )

        flag = "PROBATION" if score < 80 else "OK"

        supplier_scorecard.append({
            "supplier_id": supplier,
            "lots": lots_count,
            "accepted": accepted,
            "score_pct": f"{score:.1f}",
            "flag": flag
        })

    write_csv(
        "output/supplier_scorecard.csv",
        ["supplier_id", "lots", "accepted", "score_pct", "flag"],
        supplier_scorecard
    )

    print("Supplier scorecard generated.")
    print("Period:", start_date, "to", end_date)


def execute_commands():
    global specifications, suppliers, lots, measurements

    command_file = "data/commands.txt"

    with open(command_file, "r") as file:
        commands = file.readlines()

    for line_number, line in enumerate(commands, start=1):
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        parts = line.split("|")
        command = parts[0].strip()

        if command in (
            "LOAD_SPECS",
            "LOAD_SUPPLIERS",
            "LOAD_LOTS",
            "LOAD_MEASUREMENTS"
        ):
            if len(parts) != 2 or not parts[1].strip():
                raise ValueError(
                    f"Invalid command at line {line_number}: {line}"
                )

            filename = os.path.join("data", parts[1].strip())
            data = load_csv(filename)

            if command == "LOAD_SPECS":
                specifications = data
            elif command == "LOAD_SUPPLIERS":
                suppliers = data
            elif command == "LOAD_LOTS":
                lots = data
            elif command == "LOAD_MEASUREMENTS":
                measurements = data

            print(command, "->", len(data), "records loaded.")

        elif command == "EVALUATE":
            if any(x is None for x in (
                specifications, suppliers, lots, measurements
            )):
                raise ValueError(
                    "Load all four data files before EVALUATE."
                )

            evaluate_all_lots()

        elif command == "SCORECARD":
            if len(parts) != 3:
                raise ValueError(
                    f"Invalid SCORECARD command at line {line_number}"
                )

            if not evaluated:
                raise ValueError(
                    "Run EVALUATE before SCORECARD."
                )

            generate_scorecard(
                parts[1].strip(),
                parts[2].strip()
            )

        else:
            raise ValueError(
                f"Unknown command at line {line_number}: {command}"
            )


if __name__ == "__main__":
    execute_commands()
    print("\nPROJECT EVALUATION COMPLETED")
    print("All reports are available in the output folder.")
