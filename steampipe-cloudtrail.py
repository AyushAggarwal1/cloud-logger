#!/usr/bin/env python3
"""
Fetch all CloudTrail events from the last 24 hours via steampipe,
paginating by incrementing LIMIT + OFFSET until all results are collected.
"""

import json
import logging
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

STEP = 100
OUTPUT_FILE = "cloudtrail.json"

QUERY_TEMPLATE = """
SELECT *
FROM aws_cloudtrail_lookup_event
WHERE event_name <> 'LookupEvents'
  AND event_time >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
LIMIT {limit} OFFSET {offset}
"""


def run_query(limit: int, offset: int) -> list[dict]:
    query = QUERY_TEMPLATE.format(limit=limit, offset=offset).strip()
    cmd = ["steampipe", "query", query, "--output", "json"]
    logger.debug("Running: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("steampipe failed (offset=%d):\n%s", offset, result.stderr.strip())
        sys.exit(1)

    data = json.loads(result.stdout)
    rows = data.get("rows", data) if isinstance(data, dict) else data
    logger.info("LIMIT %d OFFSET %d -> %d rows", limit, offset, len(rows))
    return rows


def main():
    logger.info("Starting CloudTrail fetch (step=%d, output=%s)", STEP, OUTPUT_FILE)
    all_rows: list[dict] = []
    offset = 0

    while True:
        rows = run_query(limit=STEP, offset=offset)
        all_rows.extend(rows)

        if len(rows) < STEP:
            break

        offset += STEP

    logger.info("Total events fetched: %d", len(all_rows))

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_rows, f, indent=2, default=str)

    logger.info("Written to %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
