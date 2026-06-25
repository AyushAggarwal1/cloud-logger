# cloud-logger

Fetch and analyze audit logs across AWS, Azure, GCP, and OCI from a single CLI interface. Each provider fetches events for a configurable time window and writes two output files:

- **Flat JSON** — a JSON array of all events (`<output>.json`)
- **Nested JSON** — events grouped by `principal → action → timestamp` (`<output>_nested.json`)

## Usage

```bash
python main.py --type <provider> --output <file> [--config-file <path>] [--days N] [--hours N]
```

| Flag | Required | Description |
|---|---|---|
| `--type` | Yes | Cloud provider: `aws`, `azure`, `gcp`, or `oci` |
| `--output` | Yes | Output file path (e.g. `events.json`) |
| `--config-file` | No | Path to credentials config file (uses ambient credentials if omitted) |
| `--days` | No | Number of past days to fetch (default: 1 if neither flag set) |
| `--hours` | No | Number of past hours to fetch |

### Examples

```bash
# Fetch last 24 hours of AWS CloudTrail events using ambient credentials
python main.py --type aws --output aws_events.json

# Fetch last 6 hours of Azure Activity Logs using a config file
python main.py --type azure --output azure_events.json --config-file ./sample-configs/azure-config --hours 6

# Fetch last 3 days of GCP audit logs with a service account key
python main.py --type gcp --output gcp_events.json --config-file ./sample-configs/gcp-config.json --days 3

# Fetch OCI audit logs using default ~/.oci/config
python main.py --type oci --output oci_events.json
```

## Provider Setup

### AWS

Requires `boto3`. Uses `cloudtrail:LookupEvents`.

**Ambient credentials:** IAM role, `~/.aws/credentials`, or environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).

**Config file format** (`sample-configs/aws-config`):
```
aws_access_key_id     = ABC
aws_secret_access_key = XYZ
```

### Azure

Requires `azure-mgmt-monitor` and `azure-identity`. Reads from the Activity Log API.

**Ambient credentials:** `DefaultAzureCredential` (managed identity, `az login`, env vars). Set `AZURE_SUBSCRIPTION_ID` in the environment.

**Config file format** (`sample-configs/azure-config`):
```
AZURE_TENANT_ID=<tenant-id>
AZURE_SUBSCRIPTION_ID=<subscription-id>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>
```

### GCP

Requires `google-cloud-logging`. Reads Cloud Logging entries (including audit logs via `protoPayload`).

**Ambient credentials:** Application Default Credentials (`gcloud auth application-default login`). Set `GCP_PROJECT_ID` in the environment.

**Config file format:** GCP service account JSON key (`sample-configs/gcp-config.json`). The `project_id` field is read from the file automatically.

### OCI

Requires `oci`. Reads from the Audit service for the root tenancy compartment.

**Ambient credentials:** `~/.oci/config` (default OCI SDK config location).

**Config file format** (`sample-configs/oci-config`):
```ini
[DEFAULT]
    tenancy=ocid1.tenancy.oc1..aa
    user=ocid1.user.oc1..aa
    fingerprint=07:51
    region=sa-saopaulo-1
    key_file=/path/to/key.pem
```

## Output Format

### Flat JSON

A JSON array of raw event objects as returned by each provider's SDK.

```json
[
  { "eventName": "DescribeInstances", "eventTime": "2026-06-25T10:00:00Z", ... },
  ...
]
```

### Nested JSON

Events reorganized for quick lookup by identity and action:

```json
{
  "<principal>": {
    "<action>": {
      "<timestamp>": { ...full event... }
    }
  }
}
```

| Provider | Principal key | Action key |
|---|---|---|
| AWS | `userIdentity.arn` | `eventName` |
| Azure | `caller` | `operation_name.value` |
| GCP | `protoPayload.authenticationInfo.principalEmail` | `protoPayload.methodName` |
| OCI | `data.identity.principal_id` | `data.event_name` |

## Standalone Scripts

In addition to `main.py`, per-provider standalone scripts are included for quick one-off use without flags:

| Script | Provider | Output file |
|---|---|---|
| `aws-cloudtrail.py` | AWS CloudTrail | `cloudtrail_events.json` |
| `azure_activity_log.py` | Azure Activity Log | `azure_activity_events.json` |
| `gcp_audit_log.py` | GCP Cloud Logging | `gcp_audit_events.json` |
| `oci_audit_log.py` | OCI Audit | `oci_audit_events.json` |

Each standalone script fetches the last 24 hours using ambient credentials and writes both flat and nested JSON files.

## Steampipe Alternative

`steampipe-cloudtrail.py` fetches AWS CloudTrail events via [Steampipe](https://steampipe.io/) using SQL pagination instead of the boto3 SDK. Requires `steampipe` installed with the AWS plugin.

```bash
python steampipe-cloudtrail.py
# Output: cloudtrail.json
```

## Installation

```bash
# Install all provider SDKs
pip install boto3 azure-mgmt-monitor azure-identity google-cloud-logging oci
```

Install only the packages for the providers you use.
