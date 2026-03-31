"""
normalizer.py — Converts raw heterogeneous logs into ECS-compliant format.
Reused from services/normalization_service/main.py
"""

def normalize_siem(log: dict) -> dict:
    return {
        "@timestamp": log.get("timestamp"),
        "event": {
            "category": "security",
            "type": log.get("event_type"),
            "severity": log.get("severity"),
            "action": log.get("event_type"),
        },
        "source": {"ip": log.get("src_ip")},
        "destination": {"ip": log.get("dest_ip")},
        "host": {"name": log.get("hostname")},
        "user": {"name": log.get("user")},
        "message": log.get("msg"),
        "ecs": {"version": "8.11.0"},
        "observer": {
            "vendor": log.get("device_vendor"),
            "product": log.get("device_product"),
        },
    }


def normalize_edr(log: dict) -> dict:
    return {
        "@timestamp": log.get("timestamp"),
        "event": {
            "category": "process",
            "type": log.get("event"),
            "severity": log.get("severity"),
        },
        "host": {"name": log.get("endpoint_id"), "os": log.get("os")},
        "user": {"name": log.get("user")},
        "process": {
            "name": log.get("process_name"),
            "pid": log.get("process_id"),
            "parent": {"name": log.get("parent_process")},
        },
        "observer": {"vendor": log.get("device_vendor")},
        "ecs": {"version": "8.11.0"},
    }


def normalize_asset_management(log: dict) -> dict:
    return {
        "@timestamp": log.get("timestamp"),
        "event": {"category": "inventory", "type": "asset_status"},
        "host": {"name": log.get("hostname")},
        "asset": {
            "id": log.get("asset_id"),
            "type": log.get("asset_type"),
            "status": log.get("status"),
            "owner": log.get("owner"),
            "os": log.get("os"),
        },
        "vulnerability": {"cve": log.get("missing_patches", [])},
        "ecs": {"version": "8.11.0"},
    }


def normalize_network_monitoring(log: dict) -> dict:
    return {
        "@timestamp": log.get("timestamp"),
        "event": {
            "category": "network",
            "type": log.get("protocol"),
            "action": "connection_test",
        },
        "source": {"ip": log.get("src_ip")},
        "destination": {"ip": log.get("dest_ip")},
        "network": {
            "protocol": log.get("protocol"),
            "latency": log.get("latency_ms"),
            "packet_loss": log.get("packet_loss"),
        },
        "observer": {"name": log.get("device"), "vendor": log.get("vendor")},
        "ecs": {"version": "8.11.0"},
    }


def normalize_firewall(log: dict) -> dict:
    return {
        "@timestamp": log.get("timestamp"),
        "event": {
            "category": "network",
            "type": "firewall",
            "action": log.get("action", log.get("action_taken")),
            "severity": log.get("severity"),
        },
        "source": {"ip": log.get("src_ip"), "port": log.get("src_port")},
        "destination": {"ip": log.get("dest_ip"), "port": log.get("dest_port")},
        "network": {
            "protocol": log.get("protocol"),
            "direction": log.get("direction"),
        },
        "rule": {"name": log.get("rule_name"), "id": log.get("rule_id")},
        "observer": {"name": log.get("device"), "vendor": log.get("vendor")},
        "ecs": {"version": "8.11.0"},
    }


SOURCE_TYPE_NORMALIZERS = {
    "siem": normalize_siem,
    "edr": normalize_edr,
    "asset_management": normalize_asset_management,
    "network_monitoring": normalize_network_monitoring,
    "firewall": normalize_firewall,
}

# Keywords used for auto-detecting source type from filename
FILENAME_KEYWORD_MAP = {
    "siem": "siem",
    "edr": "edr",
    "patch": "asset_management",
    "asset": "asset_management",
    "network": "network_monitoring",
    "monitor": "network_monitoring",
    "firewall": "firewall",
    "fw": "firewall",
}


def detect_source_type_from_filename(filename: str) -> str:
    """Infer source_type from filename keywords."""
    name = filename.lower()
    for keyword, source_type in FILENAME_KEYWORD_MAP.items():
        if keyword in name:
            return source_type
    return "unknown"


def normalize_log(log: dict) -> dict | None:
    """Routes a raw log to the appropriate normalizer based on source_type."""
    source = log.get("source_type", "unknown")
    normalizer = SOURCE_TYPE_NORMALIZERS.get(source)
    if normalizer:
        return normalizer(log)
    # Fallback: return raw log with basic ECS wrapper
    return {
        "@timestamp": log.get("timestamp"),
        "event": {"category": "unknown"},
        "raw": log,
        "ecs": {"version": "8.11.0"},
    }
