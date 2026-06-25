from datetime import datetime, timezone, timedelta
import json
import os


def fetch(output_file="azure_activity_events.json", config_file=None, days=1, hours=0):
    from azure.mgmt.monitor import MonitorManagementClient

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=days, hours=hours)

    if config_file:
        from azure.identity import ClientSecretCredential
        cfg = {}
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, _, value = line.partition("=")
                    cfg[key.strip().upper()] = value.strip()
        credential = ClientSecretCredential(
            tenant_id=cfg["AZURE_TENANT_ID"],
            client_id=cfg["AZURE_CLIENT_ID"],
            client_secret=cfg["AZURE_CLIENT_SECRET"],
        )
        subscription_id = cfg["AZURE_SUBSCRIPTION_ID"]
    else:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]

    client = MonitorManagementClient(credential, subscription_id)

    filter_str = (
        f"eventTimestamp ge '{start_time.isoformat()}' and "
        f"eventTimestamp lt '{end_time.isoformat()}'"
    )

    total = 0
    first_event = True
    all_events = []

    with open(output_file, "w") as f:
        f.write("[\n")

        for event in client.activity_logs.list(filter=filter_str):
            event_dict = event.as_dict()
            if not first_event:
                f.write(",\n")
            f.write("  " + json.dumps(event_dict, default=str))
            first_event = False
            total += 1
            all_events.append(event_dict)
            if total % 50 == 0:
                f.flush()
                print(f"Events written so far: {total}")

        f.write("\n]")

    print(f"Done. Saved {total} events to {output_file}")

    nested = {}
    for event in all_events:
        caller = event.get("caller", "unknown")
        operation_name = event.get("operation_name", {}).get("value", "unknown")
        time_key = str(event.get("event_timestamp", "unknown"))
        nested.setdefault(caller, {}).setdefault(operation_name, {})[time_key] = event

    base, ext = os.path.splitext(output_file)
    nested_file = f"{base}_nested{ext or '.json'}"
    with open(nested_file, "w") as f:
        json.dump(nested, f, indent=2, default=str)
    print(f"Saved nested JSON to {nested_file}")


if __name__ == "__main__":
    fetch()
