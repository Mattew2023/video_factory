# -*- coding: utf-8 -*-

import hashlib
import json
from datetime import datetime
from pathlib import Path


SUCCESS_STATUSES = {
    "success",
    "verified",
    "source_moved_to_pending_delete",
    "source_deleted",
}


def now_text():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_task_id(source_path, source_size_bytes, modified_at=""):
    normalized = str(Path(source_path).expanduser().resolve(strict=False)).lower()
    raw_key = f"{normalized}|{source_size_bytes}|{modified_at}"
    return hashlib.sha1(raw_key.encode("utf-8")).hexdigest()


class CompressionRecords:
    def __init__(self, records_path):
        self.records_path = Path(records_path).expanduser()

    def iter_records(self):
        if not self.records_path.exists():
            return
        with self.records_path.open("r", encoding="utf-8") as records_file:
            for line in records_file:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    yield record

    def latest_by_task_id(self):
        latest = {}
        for record in self.iter_records() or ():
            task_id = record.get("task_id")
            if task_id:
                latest[task_id] = record
        return latest

    def has_success_for_file(self, source_path, source_size_bytes):
        source_path = str(Path(source_path).expanduser().resolve(strict=False)).lower()
        for record in self.iter_records() or ():
            record_path = str(record.get("source_path", "")).lower()
            record_size = record.get("source_size_bytes")
            if (
                record_path == source_path
                and record_size == source_size_bytes
                and record.get("status") in SUCCESS_STATUSES
            ):
                return True
        return False

    def append(self, record):
        record = dict(record)
        current_time = now_text()
        record.setdefault("created_at", current_time)
        record["updated_at"] = current_time
        self.records_path.parent.mkdir(parents=True, exist_ok=True)
        with self.records_path.open("a", encoding="utf-8") as records_file:
            records_file.write(json.dumps(record, ensure_ascii=False))
            records_file.write("\n")
        return record

    def append_status(self, base_record, status, **updates):
        record = dict(base_record)
        record.update(updates)
        record["status"] = status
        return self.append(record)
