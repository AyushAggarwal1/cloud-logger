from datetime import datetime, timezone, timedelta
import json
import os
import time


def fetch(output_file="gcp_audit_events.json", config_file=None, days=1, hours=0):
    from google.cloud import logging as gcloud_logging
    from google.api_core.exceptions import ResourceExhausted

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=days, hours=hours)

    if config_file:
        from google.oauth2 import service_account
        with open(config_file) as f:
            sa_info = json.load(f)
        project_id = sa_info["project_id"]
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=["https://www.googleapis.com/auth/logging.read"],
        )
        client = gcloud_logging.Client(project=project_id, credentials=credentials)
    else:
        project_id = os.environ["GCP_PROJECT_ID"]
        client = gcloud_logging.Client(project=project_id)

    filter_str = (
        f'timestamp>="{start_time.isoformat()}" '
        f'timestamp<"{end_time.isoformat()}"'
    )

    total = 0
    first_event = True
    all_events = []

    with open(output_file, "w") as f:
        f.write("[\n")

        iterator = client.list_entries(filter_=filter_str, page_size=500)
        while True:
            try:
                entry = next(iterator)
            except StopIteration:
                break
            except ResourceExhausted:
                print("Rate limit hit, sleeping 60s...")
                time.sleep(60)
                continue

            event_dict = entry.to_api_repr()
            if not first_event:
                f.write(",\n")
            f.write("  " + json.dumps(event_dict, default=str))
            first_event = False
            total += 1
            all_events.append(event_dict)

            if total % 500 == 0:
                f.flush()
                print(f"Events written so far: {total}")
                time.sleep(1)

        f.write("\n]")

    print(f"Done. Saved {total} events to {output_file}")

    nested = {}
    for event in all_events:
        proto = event.get("protoPayload", {})
        time_key = str(event.get("timestamp", "unknown"))

        if proto:
            # Audit log: resource_type -> principal -> methodName -> timestamp
            resource_type = event.get("resource", {}).get("type", "unknown")
            principal = proto.get("authenticationInfo", {}).get("principalEmail", "unknown")
            method_name = proto.get("methodName", "unknown")
            (nested
                .setdefault(resource_type, {})
                .setdefault(principal, {})
                .setdefault(method_name, {})
                [time_key]
            ) = event
        else:
            # Non-audit log (syslog, stdout, etc.) — resource-type -> resource -> logName -> timestamp
            resource = event.get("resource", {})
            log_resource_type = resource.get("type", "unknown")
            real_resource = next(iter(resource.get("labels", {}).values()), "unknown")
            log_name = event.get("logName", "unknown").split("/logs/")[-1]
            (nested
                .setdefault(log_resource_type, {})
                .setdefault(real_resource, {})
                .setdefault(log_name, {})
                [time_key]
            ) = event

    base, ext = os.path.splitext(output_file)
    nested_file = f"{base}_nested{ext or '.json'}"
    with open(nested_file, "w") as f:
        json.dump(nested, f, indent=2, default=str)
    print(f"Saved nested JSON to {nested_file}")


if __name__ == "__main__":
    fetch()
