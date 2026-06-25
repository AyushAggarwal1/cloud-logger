from datetime import datetime, timezone, timedelta
import json
import os


def fetch(output_file="oci_audit_events.json", config_file=None, days=1, hours=0):
    import oci

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=days, hours=hours)

    config = oci.config.from_file(file_location=config_file) if config_file else oci.config.from_file()
    compartment_id = config["tenancy"]
    audit_client = oci.audit.AuditClient(config)

    total = 0
    first_event = True
    next_page = None
    all_events = []

    with open(output_file, "w") as f:
        f.write("[\n")

        while True:
            kwargs = {
                "compartment_id": compartment_id,
                "start_time": start_time,
                "end_time": end_time,
            }
            if next_page:
                kwargs["page"] = next_page

            response = audit_client.list_events(**kwargs)

            for event in response.data:
                event_dict = oci.util.to_dict(event)
                if not first_event:
                    f.write(",\n")
                f.write("  " + json.dumps(event_dict, default=str))
                first_event = False
                total += 1
                all_events.append(event_dict)

            f.flush()
            print(f"Batch written: {len(response.data)} events (total so far: {total})")

            next_page = response.next_page
            if not next_page:
                break

        f.write("\n]")

    print(f"Done. Saved {total} events to {output_file}")

    nested = {}
    for event in all_events:
        identity = event.get("data", {}).get("identity", {})
        principal = identity.get("principal_id") or identity.get("principal_name", "unknown")
        event_name = event.get("data", {}).get("event_name") or event.get("event_type", "unknown")
        time_key = str(event.get("event_time", "unknown"))
        nested.setdefault(principal, {}).setdefault(event_name, {})[time_key] = event

    base, ext = os.path.splitext(output_file)
    nested_file = f"{base}_nested{ext or '.json'}"
    with open(nested_file, "w") as f:
        json.dump(nested, f, indent=2, default=str)
    print(f"Saved nested JSON to {nested_file}")


if __name__ == "__main__":
    fetch()
