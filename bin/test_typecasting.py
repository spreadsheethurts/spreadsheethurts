import argparse
import json
import importlib
import os
import datetime
from pathlib import Path
from time import sleep
from typing import Optional, List, Dict, Any

from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

from wizard.argumentation.dataset import Dataset


def datetime_encoder(obj):
    """Custom JSON encoder to handle datetime objects."""
    if isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S.%f")
    elif isinstance(obj, datetime.time):
        return obj.strftime("%H:%M:%S.%f")
    elif isinstance(obj, datetime.date):
        return obj.strftime("%Y-%m-%d")

    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def datetime_decoder(obj):
    """Custom JSON decoder to handle datetime strings."""
    for key, value in obj.items():
        if isinstance(value, str):
            # Try to parse datetime in the format "yyyy-mm-dd hh:mm:ss.microsecond"
            try:
                obj[key] = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                # Try to parse time in the format "hh:mm:ss.microsecond"
                try:
                    obj[key] = datetime.datetime.strptime(value, "%H:%M:%S.%f").time()
                except ValueError:
                    # Try to parse date in the format "yyyy-mm-dd"
                    try:
                        obj[key] = datetime.datetime.strptime(value, "%Y-%m-%d").date()
                    except ValueError:
                        pass  # Keep original string if not a datetime/time/date format
    return obj


def get_latest_report_file(sn: str) -> Optional[Path]:
    """Get the latest report file for the given software name."""
    output_dir = Path("typecasting_testing_reports")
    if not output_dir.exists():
        return None

    pattern = f"validation_{sn}_*.json"
    files = list(output_dir.glob(pattern))

    if not files:
        return None

    # Sort by timestamp in filename (descending)
    files.sort(key=lambda x: x.name, reverse=True)
    return files[0]


def load_discrepancies_from_report(
    report_file: Path,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Load discrepancies from an existing report file."""
    with open(report_file, "r", encoding="utf-8") as f:
        report_data = json.load(f, object_hook=datetime_decoder)
    return report_data.get("discrepancies", []), report_data.get("meta", {})


def get_type_casting_class(sn: str):
    """Dynamically import the TypeCasting class based on software name."""
    try:
        module_path = f"wizard.app.common.rule.{sn}"
        module = importlib.import_module(module_path)
        class_name = f"{sn.capitalize()}TypeCasting"
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        print(f"❌ Error: Could not find or import the necessary class for '{sn}'.")
        print(f"   Details: {e}")
        print(
            f"   Please ensure 'src/wizard/app/common/rule/{sn}.py' exists and contains a class named '{class_name}'."
        )
        exit(1)


def run_validation(sn: str, size: Optional[int] = None, from_report: bool = False):
    """
    Run validation comparing a type-casting decision tree's output
    with ground truth from the database or from an existing report.
    """
    TypeCastingClass = get_type_casting_class(sn)
    tree = TypeCastingClass.build_tree()

    if from_report:
        # Load from latest report file
        report_file = get_latest_report_file(sn)
        if not report_file:
            print(
                f"❌ No report file found for '{sn}'. Please run validation with database first."
            )
            exit(1)

        print(f"📂 Loading data from report: {report_file}")
        old_discrepancies, _ = load_discrepancies_from_report(report_file)

        # Create items from old discrepancies: (input, expected) pairs
        items = [(d["input"], d["expected"]) for d in old_discrepancies]
        source_info = f"re-validating {len(items)} items from report {report_file.name}"
    else:
        # Load from database
        dataset = Dataset(sn=sn)
        items = list(dataset.get_items(size))
        source_info = f"validating against {len(items)} database records"

    print(f"🔍 Starting validation for '{sn}': {source_info}")
    print(f"   Processing {len(items)} items...")

    # Setup progress bar
    with Progress(
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TimeRemainingColumn(),
    ) as progress:
        task_id = progress.add_task(
            "Processing... (0 discrepancies found)", total=len(items)
        )

        discrepancies = []
        for i, (input, ground_truth) in enumerate(items, start=1):
            # input_str is already a string when from_report, or needs decoding when from database
            if from_report:
                input_str = input
                result = tree.decide(input, scalar=True)
            else:
                input_str = input.decode("utf-8")
                result = tree.decide(input_str, scalar=True)

            if result != ground_truth:
                # Use original ID if from_report, otherwise use current index
                item_id = old_discrepancies[i - 1]["id"] if from_report else i

                discrepancy = {
                    "id": item_id,
                    "input": input_str,
                    "expected": ground_truth,
                    "result": result,
                }
                discrepancies.append(discrepancy)

                # Update progress bar description with discrepancy count
                progress.update(
                    task_id,
                    description=f"Processing... ({len(discrepancies)} discrepancies found)",
                )

            progress.update(task_id, advance=1)

            # Optional: small delay every 100 items to prevent overwhelming
            if i % 100 == 0:
                sleep(0.01)

    return discrepancies, len(items)


def main():
    parser = argparse.ArgumentParser(
        description="Run validation for spreadsheet type-casting rules with a TUI."
    )
    parser.add_argument(
        "--sn",
        "--sn",
        type=str,
        required=True,
        choices=["gsheet", "excel", "calc"],
        help="The name of the spreadsheet software to validate.",
        dest="sn",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=None,
        help="The number of records to retrieve from the database for validation (ignored when --from-report is used).",
    )
    parser.add_argument(
        "--from-report",
        action="store_true",
        help="Load test data from the latest report file instead of database.",
    )
    args = parser.parse_args()

    discrepancies, processed_count = run_validation(
        args.sn, args.size, args.from_report
    )

    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")

    # Determine source info for metadata
    if args.from_report:
        source_report = get_latest_report_file(args.sn)
        source_info = (
            f"revalidation_of_{source_report.name}"
            if source_report
            else "unknown_report"
        )
    else:
        source_info = "database"

    report_data = {
        "meta": {
            "sn": args.sn,
            "size_requested": args.size if not args.from_report else None,
            "size_processed": processed_count,
            "discrepancies_found": len(discrepancies),
            "timestamp": timestamp,
            "source": source_info,
        },
        "discrepancies": discrepancies,
    }

    output_dir = Path("typecasting_testing_reports")
    output_dir.mkdir(exist_ok=True)

    # Different filename for revalidation reports
    if args.from_report:
        report_file = output_dir / f"revalidation_{args.sn}_{timestamp}.json"
    else:
        report_file = output_dir / f"validation_{args.sn}_{timestamp}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(
            report_data, f, indent=4, ensure_ascii=False, default=datetime_encoder
        )

    source_desc = "re-validation" if args.from_report else "validation"
    print(
        f"\n✅ {source_desc.capitalize()} finished. Found {len(discrepancies)} discrepancies."
    )
    print(f"   Report saved to: {report_file}")


if __name__ == "__main__":
    main()
