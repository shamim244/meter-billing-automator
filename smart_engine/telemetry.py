"""
telemetry.py – High-Performance SQLite & JSON UI Interaction Telemetry Manager.
Records exact UI click coordinates, normalized screen ratios, latencies, failure reasons,
and decision states for future AI decision model training without impacting pipeline speed.
"""
import os
import sys
import time
import json
import sqlite3
import argparse
from typing import Optional, Dict, Any, List

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "telemetry.sqlite")

class TelemetryManager:
    _instance = None

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._conn = None
        self._ensure_tables()

    @classmethod
    def get_instance(cls, db_path: str = DEFAULT_DB_PATH):
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, timeout=5.0)
            self._conn.row_factory = sqlite3.Row
            try:
                self._conn.execute("PRAGMA journal_mode = WAL;")
                self._conn.execute("PRAGMA synchronous = NORMAL;")
            except Exception:
                pass
        return self._conn

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def _ensure_tables(self):
        try:
            conn = self.get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS consumer_traces (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ca_number TEXT NOT NULL,
                        mru TEXT,
                        cycle TEXT,
                        device_serial TEXT,
                        screen_resolution TEXT,
                        meter_type TEXT,
                        base_kwh INTEGER,
                        final_reading INTEGER,
                        overall_status TEXT,
                        total_duration_ms INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ui_interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trace_id INTEGER NOT NULL,
                        step_num INTEGER NOT NULL,
                        screen_name TEXT,
                        activity TEXT,
                        action_name TEXT,
                        coord_x INTEGER,
                        coord_y INTEGER,
                        ratio_x REAL,
                        ratio_y REAL,
                        how_method TEXT,
                        duration_ms INTEGER,
                        status TEXT,
                        alert_message TEXT,
                        prefill_state TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(trace_id) REFERENCES consumer_traces(id)
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_ca ON consumer_traces(ca_number);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_cycle ON consumer_traces(cycle);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_trace ON ui_interactions(trace_id);")
        except Exception as e:
            # Telemetry must never crash runtime
            print(f"[!] Telemetry DB initialization warning: {e}", file=sys.stderr)

    def start_trace(
        self,
        ca_number: str,
        mru: str = "",
        cycle: str = "",
        device_serial: str = "",
        screen_resolution: str = "1080x2400",
        meter_type: str = "NORMAL",
        base_kwh: int = 0
    ) -> Optional[int]:
        """Starts a new consumer trace record. Returns trace_id or None on failure."""
        try:
            conn = self.get_connection()
            with conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO consumer_traces 
                    (ca_number, mru, cycle, device_serial, screen_resolution, meter_type, base_kwh, overall_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (str(ca_number), str(mru), str(cycle), str(device_serial), str(screen_resolution), str(meter_type), int(base_kwh or 0), "RUNNING")
                )
                return cur.lastrowid
        except Exception:
            return None

    def log_interaction(
        self,
        trace_id: Optional[int],
        step_num: int,
        screen_name: str,
        activity: str,
        action_name: str,
        coord_x: Optional[int] = None,
        coord_y: Optional[int] = None,
        ratio_x: Optional[float] = None,
        ratio_y: Optional[float] = None,
        how_method: str = "cached_tap",
        duration_ms: int = 0,
        status: str = "SUCCESS",
        alert_message: str = "",
        prefill_state: str = ""
    ):
        """Records a single UI interaction step into ui_interactions."""
        if not trace_id:
            return
        try:
            conn = self.get_connection()
            with conn:
                conn.execute(
                    """
                    INSERT INTO ui_interactions
                    (trace_id, step_num, screen_name, activity, action_name, 
                     coord_x, coord_y, ratio_x, ratio_y, how_method, duration_ms, 
                     status, alert_message, prefill_state)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trace_id, step_num, screen_name, activity, action_name,
                        coord_x, coord_y, ratio_x, ratio_y, how_method, int(duration_ms or 0),
                        status, alert_message, prefill_state
                    )
                )
        except Exception:
            pass

    def finish_trace(
        self,
        trace_id: Optional[int],
        final_reading: Optional[int] = None,
        overall_status: str = "submitted",
        total_duration_ms: int = 0
    ):
        """Finalizes a consumer trace record."""
        if not trace_id:
            return
        try:
            conn = self.get_connection()
            with conn:
                conn.execute(
                    """
                    UPDATE consumer_traces
                    SET final_reading = ?, overall_status = ?, total_duration_ms = ?
                    WHERE id = ?
                    """,
                    (final_reading, overall_status, int(total_duration_ms or 0), trace_id)
                )
        except Exception:
            pass

    def export_dataset(self, cycle: Optional[str] = None, mru: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns the complete dataset formatted for decision model training."""
        traces = []
        try:
            conn = self.get_connection()
            query = "SELECT * FROM consumer_traces WHERE 1=1"
            params = []
            if cycle:
                query += " AND cycle = ?"
                params.append(cycle)
            if mru:
                query += " AND mru = ?"
                params.append(str(mru))
            query += " ORDER BY id ASC"

            cur = conn.cursor()
            rows = cur.execute(query, params).fetchall()

            for row in rows:
                t_dict = dict(row)
                trace_id = t_dict["id"]

                # Fetch interactions
                i_rows = conn.execute(
                    "SELECT * FROM ui_interactions WHERE trace_id = ? ORDER BY step_num ASC, id ASC",
                    (trace_id,)
                ).fetchall()
                t_dict["interactions"] = [dict(ir) for ir in i_rows]
                traces.append(t_dict)
        except Exception as e:
            print(f"[!] Export error: {e}", file=sys.stderr)
        return traces

    def export_jsonl(self, output_path: str, cycle: Optional[str] = None, mru: Optional[str] = None) -> int:
        """Exports dataset to a JSON Lines file."""
        dataset = self.export_dataset(cycle=cycle, mru=mru)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item) + "\n")
        return len(dataset)

    def export_json(self, output_path: str, cycle: Optional[str] = None, mru: Optional[str] = None, indent: int = 2) -> int:
        """Exports dataset to a formatted JSON file."""
        dataset = self.export_dataset(cycle=cycle, mru=mru)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=indent)
        return len(dataset)

    def get_summary(self) -> Dict[str, Any]:
        """Provides a summary of logged traces and interactions."""
        try:
            conn = self.get_connection()
            total_traces = conn.execute("SELECT COUNT(*) FROM consumer_traces").fetchone()[0]
            status_counts = dict(conn.execute("SELECT overall_status, COUNT(*) FROM consumer_traces GROUP BY overall_status").fetchall())
            total_actions = conn.execute("SELECT COUNT(*) FROM ui_interactions").fetchone()[0]
            avg_duration = conn.execute("SELECT AVG(total_duration_ms) FROM consumer_traces WHERE overall_status='submitted'").fetchone()[0]
            return {
                "total_traces": total_traces,
                "status_counts": status_counts,
                "total_interactions": total_actions,
                "avg_submitted_duration_ms": round(avg_duration or 0, 1),
                "db_path": self.db_path
            }
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Engine Telemetry & Decision Model Exporter")
    parser.add_argument("--export-json", help="Path to export JSON file")
    parser.add_argument("--export-jsonl", help="Path to export JSONL file")
    parser.add_argument("--cycle", help="Filter by billing cycle (e.g. NOV-2026)")
    parser.add_argument("--mru", help="Filter by MRU")
    parser.add_argument("--summary", action="store_true", help="Print summary of telemetry database")
    args = parser.parse_args()

    tm = TelemetryManager.get_instance()

    if args.summary:
        summary = tm.get_summary()
        print("\n" + "="*50)
        print(" [TELEMETRY SUMMARY]")
        print("="*50)
        print(f" Database: {summary.get('db_path')}")
        print(f" Total Consumer Traces: {summary.get('total_traces')}")
        print(f" Status Breakdown: {summary.get('status_counts')}")
        print(f" Total UI Interactions: {summary.get('total_interactions')}")
        print(f" Avg Duration (Submitted): {summary.get('avg_submitted_duration_ms')} ms")
        print("="*50 + "\n")

    if args.export_json:
        n = tm.export_json(args.export_json, cycle=args.cycle, mru=args.mru)
        print(f"[✓] Exported {n} consumer traces to JSON: {args.export_json}")

    if args.export_jsonl:
        n = tm.export_jsonl(args.export_jsonl, cycle=args.cycle, mru=args.mru)
        print(f"[✓] Exported {n} consumer traces to JSONL: {args.export_jsonl}")
