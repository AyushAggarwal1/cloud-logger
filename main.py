#!/usr/bin/env python3
import argparse
import importlib.util
from pathlib import Path

_HERE = Path(__file__).parent


def _load(filename):
    """Load a module from a file path, handling hyphenated filenames."""
    path = _HERE / filename
    spec = importlib.util.spec_from_file_location(filename.replace("-", "_").replace(".py", ""), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MODULES = {
    "aws":   "aws-cloudtrail.py",
    "azure": "azure_activity_log.py",
    "gcp":   "gcp_audit_log.py",
    "oci":   "oci_audit_log.py",
}


def main():
    parser = argparse.ArgumentParser(description="Fetch cloud audit logs and write flat + nested JSON")
    parser.add_argument("--type", required=True, choices=MODULES, help="Cloud provider (aws/azure/gcp/oci)")
    parser.add_argument("--output", required=True, help="Output file name, e.g. events.json")
    parser.add_argument("--config-file", default=None, help="Path to provider credentials config file")
    parser.add_argument("--days", type=int, default=0, help="Number of past days to fetch")
    parser.add_argument("--hours", type=int, default=0, help="Number of past hours to fetch")
    args = parser.parse_args()

    days = args.days if (args.days or args.hours) else 1

    mod = _load(MODULES[args.type])
    mod.fetch(args.output, config_file=args.config_file, days=days, hours=args.hours)


if __name__ == "__main__":
    main()
