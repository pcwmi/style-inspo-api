#!/usr/bin/env python3
"""
Read-only S3 helper for verification.

Usage:
    python scripts/s3_read.py read <user_id> <path>
    python scripts/s3_read.py list <user_id> <prefix>

Examples:
    python scripts/s3_read.py read peichin activity/2026-01-22.json
    python scripts/s3_read.py list peichin activity/
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services.storage_manager import StorageManager


def read_json(user_id: str, path: str):
    """Read and print JSON file from S3."""
    storage = StorageManager(storage_type="s3", user_id=user_id)
    try:
        data = storage.load_json(path)
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        sys.exit(1)


def list_objects(user_id: str, prefix: str):
    """List objects in S3 with given prefix."""
    storage = StorageManager(storage_type="s3", user_id=user_id)
    try:
        # Build the full prefix
        full_prefix = f"{user_id}/{prefix}"

        # Use boto3 directly for listing
        response = storage.s3_client.list_objects_v2(
            Bucket=storage.bucket_name,
            Prefix=full_prefix
        )

        if "Contents" not in response:
            print(f"No objects found with prefix: {full_prefix}")
            return

        for obj in response["Contents"]:
            key = obj["Key"]
            size = obj["Size"]
            modified = obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
            # Remove user_id prefix for cleaner output
            display_key = key.replace(f"{user_id}/", "", 1)
            print(f"{modified}  {size:>8}  {display_key}")

    except Exception as e:
        print(f"Error listing {prefix}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    user_id = sys.argv[2]

    if cmd == "read":
        if len(sys.argv) < 4:
            print("Usage: python scripts/s3_read.py read <user_id> <path>")
            sys.exit(1)
        path = sys.argv[3]
        read_json(user_id, path)

    elif cmd == "list":
        prefix = sys.argv[3] if len(sys.argv) > 3 else ""
        list_objects(user_id, prefix)

    else:
        print(f"Unknown command: {cmd}")
        print("Use 'read' or 'list'")
        sys.exit(1)


if __name__ == "__main__":
    main()
