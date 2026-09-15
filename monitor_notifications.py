import argparse
import csv
import os
from datetime import datetime, timezone


def count_csv_rows(path):
    if not os.path.exists(path):
        return 0

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return sum(1 for _ in csv.DictReader(file))


def inspect_current_data(
    path,
    minimum_healthy_rows,
    max_healthy_age_hours,
    required_currency,
):
    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    currencies = sorted({
        str(row.get("Currency", "")).strip().upper()
        for row in rows
        if str(row.get("Currency", "")).strip()
    })

    last_seen_values = [
        str(row.get("Last Seen", "")).strip()
        for row in rows
        if str(row.get("Last Seen", "")).strip()
    ]

    age_hours = None

    if last_seen_values:
        last_seen = datetime.strptime(
            max(last_seen_values),
            "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=timezone.utc)
        age_hours = (
            datetime.now(timezone.utc) - last_seen
        ).total_seconds() / 3600

    healthy = (
        len(rows) >= minimum_healthy_rows
        and currencies == [required_currency]
        and age_hours is not None
        and age_hours <= max_healthy_age_hours
    )

    return {
        "healthy": str(healthy).lower(),
        "current_rows": len(rows),
        "currencies": ",".join(currencies) or "none",
        "data_age_hours": (
            f"{age_hours:.1f}"
            if age_hours is not None
            else "unknown"
        ),
    }


def write_outputs(values):
    output_path = os.environ.get("GITHUB_OUTPUT", "").strip()

    if output_path:
        with open(output_path, "a", encoding="utf-8") as file:
            for key, value in values.items():
                file.write(f"{key}={value}\n")

    for key, value in values.items():
        print(f"{key}={value}")


def snapshot(args):
    write_outputs({
        "price_rows": count_csv_rows(args.price_history),
        "structure_rows": count_csv_rows(args.structure_history),
    })


def compare(args):
    price_rows = count_csv_rows(args.price_history)
    structure_rows = count_csv_rows(args.structure_history)

    if price_rows < args.before_price:
        raise RuntimeError(
            "Price history unexpectedly became shorter: "
            f"{args.before_price} -> {price_rows}"
        )

    if structure_rows < args.before_structure:
        raise RuntimeError(
            "Product-change history unexpectedly became shorter: "
            f"{args.before_structure} -> {structure_rows}"
        )

    price_changes = price_rows - args.before_price
    structure_changes = structure_rows - args.before_structure

    outputs = {
        "changed": str(
            price_changes > 0 or structure_changes > 0
        ).lower(),
        "price_changes": price_changes,
        "structure_changes": structure_changes,
    }

    outputs.update(
        inspect_current_data(
            args.current_data,
            args.minimum_healthy_rows,
            args.max_healthy_age_hours,
            args.required_currency,
        )
    )

    write_outputs(outputs)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Detect meaningful price-monitor changes for GitHub Actions."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--price-history", required=True)
    snapshot_parser.add_argument("--structure-history", required=True)
    snapshot_parser.set_defaults(handler=snapshot)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--price-history", required=True)
    compare_parser.add_argument("--structure-history", required=True)
    compare_parser.add_argument(
        "--before-price",
        required=True,
        type=int,
    )
    compare_parser.add_argument(
        "--before-structure",
        required=True,
        type=int,
    )
    compare_parser.add_argument("--current-data", required=True)
    compare_parser.add_argument(
        "--minimum-healthy-rows",
        required=True,
        type=int,
    )
    compare_parser.add_argument(
        "--max-healthy-age-hours",
        required=True,
        type=float,
    )
    compare_parser.add_argument(
        "--required-currency",
        default="USD",
    )
    compare_parser.set_defaults(handler=compare)

    return parser


def main():
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
