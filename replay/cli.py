"""
Replay CLI - Command-line interface for replay operations.

Usage:
    python -m replay.cli run --pack treasury --from 2025-01-01 --to 2025-03-31
    python -m replay.cli ingest --file signals.csv --pack treasury
    python -m replay.cli compare --baseline replay_123 --comparison replay_456
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .csv_ingestor import CSVIngestor, ColumnMapping
from .harness import ReplayHarness, ReplayConfig
from .comparison import compare_evaluations, generate_comparison_report
from .metrics import MetricsCalculator, generate_metrics_report


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def cmd_run(args) -> int:
    """Run replay on historical signals."""
    print(f"Running replay for pack: {args.pack}")
    print(f"Namespace: {args.namespace or 'auto-generated'}")

    if args.from_date:
        print(f"From: {args.from_date}")
    if args.to_date:
        print(f"To: {args.to_date}")

    config = ReplayConfig(
        pack=args.pack,
        namespace=args.namespace,
        from_date=parse_date(args.from_date) if args.from_date else None,
        to_date=parse_date(args.to_date) if args.to_date else None,
    )

    # For now, demonstrate with sample data
    # In production, this would connect to the database
    if args.db:
        print("\nConnecting to database...")
        # TODO: Implement database connection
        print("Database mode not yet implemented. Use --sample for demo.")
        return 1
    else:
        print("\nRunning with sample data (use --db for database mode)...")
        from .csv_ingestor import IngestedSignal

        # Sample signals for demo
        sample_signals = [
            IngestedSignal(
                signal_type="position_limit_breach",
                source="demo",
                payload={
                    "asset": "BTC",
                    "current_position": 150000000,
                    "limit": 100000000,
                    "currency": "USD"
                },
                timestamp=datetime.utcnow(),
            ),
            IngestedSignal(
                signal_type="market_volatility_spike",
                source="demo",
                payload={
                    "asset": "ETH",
                    "volatility": 0.85,
                    "threshold": 0.6,
                    "timeframe": "24h"
                },
                timestamp=datetime.utcnow(),
            ),
        ]

        # Sample policies
        sample_policies = [
            {
                "id": "policy-1",
                "name": "Position Limit Policy",
                "current_version": {
                    "id": "version-1",
                    "rule_definition": {
                        "type": "threshold_breach",
                        "conditions": [{
                            "signal_type": "position_limit_breach",
                            "threshold": {
                                "field": "payload.current_position",
                                "operator": ">",
                                "value": "payload.limit"
                            },
                            "severity_mapping": {"default": "high"}
                        }],
                        "evaluation_logic": "any_condition_met"
                    }
                }
            },
            {
                "id": "policy-2",
                "name": "Volatility Policy",
                "current_version": {
                    "id": "version-2",
                    "rule_definition": {
                        "type": "threshold_breach",
                        "conditions": [{
                            "signal_type": "market_volatility_spike",
                            "threshold": {
                                "field": "payload.volatility",
                                "operator": ">",
                                "value": "payload.threshold"
                            },
                            "severity_mapping": {"default": "medium"}
                        }],
                        "evaluation_logic": "any_condition_met"
                    }
                }
            }
        ]

        harness = ReplayHarness()
        result = harness.run(sample_signals, sample_policies, config)

    print(f"\nReplay complete!")
    print(f"  Signals processed: {result.signals_processed}")
    print(f"  Evaluations: {len(result.evaluations)}")
    print(f"  Exceptions raised: {len(result.exceptions_raised)}")
    print(f"  Pass: {result.pass_count}, Fail: {result.fail_count}, Inconclusive: {result.inconclusive_count}")

    # Calculate and display metrics
    calculator = MetricsCalculator()
    metrics = calculator.calculate(result)

    if args.verbose:
        print("\n" + generate_metrics_report(metrics))

    # Output results if requested
    if args.output:
        output_path = Path(args.output)
        output_data = {
            "replay_id": result.replay_id,
            "namespace": result.namespace,
            "config": config.model_dump(mode="json"),
            "summary": {
                "signals_processed": result.signals_processed,
                "evaluations": len(result.evaluations),
                "exceptions": len(result.exceptions_raised),
                "pass_count": result.pass_count,
                "fail_count": result.fail_count,
            },
            "exceptions": [e.model_dump(mode="json") for e in result.exceptions_raised],
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\nResults written to: {output_path}")

    return 0


def cmd_ingest(args) -> int:
    """Ingest signals from a CSV file."""
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        return 1

    print(f"Ingesting signals from: {filepath}")
    print(f"Pack: {args.pack}")

    # Build column mapping
    mapping_dict = {
        "signal_type": args.signal_type_col or "signal_type",
        "timestamp": args.timestamp_col or "timestamp",
        "source": args.source_col or "source",
    }

    if args.mapping:
        # Parse additional mappings from JSON
        try:
            extra_mapping = json.loads(args.mapping)
            mapping_dict["payload_columns"] = extra_mapping
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in --mapping: {args.mapping}")
            return 1

    column_mapping = ColumnMapping(**mapping_dict)

    ingestor = CSVIngestor(pack=args.pack)

    try:
        batch = ingestor.ingest(filepath, column_mapping, skip_errors=args.skip_errors)
    except Exception as e:
        print(f"Error during ingestion: {e}")
        return 1

    print(f"\nIngestion complete!")
    print(f"  Batch ID: {batch.batch_id}")
    print(f"  File hash: {batch.file_hash[:16]}...")
    print(f"  Signals ingested: {batch.row_count}")

    if args.verbose:
        print("\nSample signals:")
        for signal in batch.signals[:3]:
            print(f"  - {signal.signal_type}: {signal.payload}")

    # Output results if requested
    if args.output:
        output_path = Path(args.output)
        output_data = {
            "batch_id": batch.batch_id,
            "source_file": batch.source_file,
            "file_hash": batch.file_hash,
            "row_count": batch.row_count,
            "signals": [s.model_dump(mode="json") for s in batch.signals],
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\nResults written to: {output_path}")

    return 0


def cmd_compare(args) -> int:
    """Compare two replay results."""
    print(f"Comparing replays:")
    print(f"  Baseline: {args.baseline}")
    print(f"  Comparison: {args.comparison}")

    # Load replay results from files
    baseline_path = Path(args.baseline)
    comparison_path = Path(args.comparison)

    if not baseline_path.exists():
        print(f"Error: Baseline file not found: {baseline_path}")
        return 1

    if not comparison_path.exists():
        print(f"Error: Comparison file not found: {comparison_path}")
        return 1

    # TODO: Implement loading ReplayResult from JSON files
    print("\nComparison from files not yet implemented.")
    print("Run replays with --output flag first, then compare.")

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="replay",
        description="Replay harness for policy evaluation",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run replay on signals")
    run_parser.add_argument("--pack", default="treasury", help="Domain pack (treasury, wealth)")
    run_parser.add_argument("--namespace", help="Replay namespace (auto-generated if not provided)")
    run_parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    run_parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    run_parser.add_argument("--db", action="store_true", help="Use database signals")
    run_parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    run_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest signals from CSV")
    ingest_parser.add_argument("--file", "-f", required=True, help="CSV file path")
    ingest_parser.add_argument("--pack", default="treasury", help="Domain pack")
    ingest_parser.add_argument("--signal-type-col", help="Column name for signal type")
    ingest_parser.add_argument("--timestamp-col", help="Column name for timestamp")
    ingest_parser.add_argument("--source-col", help="Column name for source")
    ingest_parser.add_argument("--mapping", help="JSON mapping of payload columns")
    ingest_parser.add_argument("--skip-errors", action="store_true", help="Skip rows with errors")
    ingest_parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    ingest_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare replay results")
    compare_parser.add_argument("--baseline", "-b", required=True, help="Baseline replay result file")
    compare_parser.add_argument("--comparison", "-c", required=True, help="Comparison replay result file")
    compare_parser.add_argument("--output", "-o", help="Output file for comparison (JSON)")
    compare_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "run":
        return cmd_run(args)
    elif args.command == "ingest":
        return cmd_ingest(args)
    elif args.command == "compare":
        return cmd_compare(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
