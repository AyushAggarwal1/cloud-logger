from datetime import datetime, timezone, timedelta
import boto3
import json
import os


def fetch(output_file="cloudtrail_events.json", config_file=None, days=1, hours=0):
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=days, hours=hours)

    kwargs = {}
    if config_file:
        import configparser
        parser = configparser.ConfigParser()
        with open(config_file) as f:
            parser.read_string("[default]\n" + f.read())
        section = parser["default"]
        kwargs = {
            "aws_access_key_id": section.get("aws_access_key_id", "").strip(),
            "aws_secret_access_key": section.get("aws_secret_access_key", "").strip(),
        }

    cloudtrail = boto3.client("cloudtrail", **kwargs)

    next_token = None
    total = 0
    first_event = True
    all_events = []

    with open(output_file, "w") as f:
        f.write("[\n")

        while True:
            params = {"StartTime": start_time, "EndTime": end_time, "MaxResults": 50}
            if next_token:
                params["NextToken"] = next_token

            response = cloudtrail.lookup_events(**params)
            filtered = [e for e in response["Events"] if e.get("EventName") != "LookupEvents"]

            for event in filtered:
                raw = event.pop("CloudTrailEvent", None)
                if raw:
                    event.update(json.loads(raw))
                if not first_event:
                    f.write(",\n")
                f.write("  " + json.dumps(event, default=str))
                first_event = False
                all_events.append(event)

            f.flush()
            total += len(filtered)
            print(f"Batch written: {len(filtered)} events (total so far: {total})")

            next_token = response.get("NextToken")
            if not next_token:
                break

        f.write("\n]")

    print(f"Done. Saved {total} events to {output_file}")

    nested = {}
    for event in all_events:
        arn = event.get("userIdentity", {}).get("arn", "unknown")
        event_name = event.get("eventName") or event.get("EventName", "unknown")
        time_key = str(event.get("eventTime") or event.get("EventTime", "unknown"))
        nested.setdefault(arn, {}).setdefault(event_name, {})[time_key] = event

    base, ext = os.path.splitext(output_file)
    nested_file = f"{base}_nested{ext or '.json'}"
    with open(nested_file, "w") as f:
        json.dump(nested, f, indent=2, default=str)
    print(f"Saved nested JSON to {nested_file}")


if __name__ == "__main__":
    fetch()
