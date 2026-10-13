"""
NBPDCL REST API v1 client - thin wrapper around the SaaS billing platform.

Endpoints (from http://127.0.0.1:8000/api/v1/openapi.json):
  GET  /auth/me
  GET  /mrus
  GET  /bills
  PATCH /bills/review
  POST /bills/batch-sync
  GET  /automation/queue

Auth: "Authorization: Bearer nbp_live_..."  OR  "X-API-Key: nbp_live_..."
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Reason code dictionaries (from the API docs)
DOUBT_REASONS = {
    "PREMISES_LOCKED": "House locked / closed",
    "SUSPICIOUS_READING": "Abnormal reading spike",
    "SUSPICIOUS_AMOUNT": "High arrears disputed",
    "PREV_MONTH_MISMATCH": "Dial baseline mismatch",
    "OWNER_RECHECK_REQUEST": "Consumer re-verification",
}

CRITICAL_REASONS = {
    "METER_BURNT_DEAD": "Black/burnt display",
    "METER_TAMPERED_BYPASS": "Seal broken / direct line",
    "METER_MISSING_STOLEN": "Meter stolen / not found",
    "PREMISES_DEMOLISHED": "Building demolished",
    "JE_INTERVENTION_REQUIRED": "DISCOM legal/SDO block",
}

REVIEW_STATUSES = {"submitted", "doubt", "critical", "pending"}


class NBPDCLClient:
    def __init__(self, base_url=None, api_key=None, auth_mode=None):
        self.base_url = (base_url or os.environ.get(
            "NBPDCL_API_BASE", "http://127.0.0.1:8000/api/v1"
        )).rstrip("/")
        self.api_key = api_key or os.environ.get("NBPDCL_API_KEY", "")
        self.auth_mode = auth_mode or os.environ.get("NBPDCL_AUTH_MODE", "bearer")

        if not self.api_key or self.api_key == "nbp_live_YOUR_KEY_HERE":
            raise ValueError(
                "NBPDCL_API_KEY not set. Copy chat/.env, fill in your key "
                "(get one at http://127.0.0.1:8000/register)."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _headers(self):
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.auth_mode.lower() == "apikey":
            h["X-API-Key"] = self.api_key
        else:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _get(self, path, params=None):
        r = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params or {},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def _patch(self, path, payload):
        r = requests.patch(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def _post(self, path, payload):
        r = requests.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def auth_me(self):
        """Operator profile + active stats (plan, MRUs, consumers, bills)."""
        return self._get("/auth/me")

    def list_mrus(self):
        """All village/block MRU workspaces for the authenticated tenant."""
        return self._get("/mrus")

    def list_bills(self, mru_id=None, month=None, year=None, status="all",
                   sort_col=None, sort_asc=True, status_sort="default",
                   search=None, per_page=50, page=1):
        """Query filtered & sorted monthly bills (web dashboard parity)."""
        params = {
            "status": status,
            "per_page": per_page,
            "page": page,
            "sort_asc": str(sort_asc).lower(),
            "status_sort": status_sort,
        }
        if mru_id:
            params["mru_id"] = mru_id
        if month:
            params["month"] = month
        if year:
            params["year"] = year
        if sort_col:
            params["sort_col"] = sort_col
        if search:
            params["search"] = search
        return self._get("/bills", params=params)

    def submit_review(self, ca_number, billing_month, billing_year, status,
                      reason_code=None, remark=None, working_reading=None):
        """Atomic field verdict: submit a human inspection decision."""
        if status not in REVIEW_STATUSES:
            raise ValueError(f"status must be one of {REVIEW_STATUSES}")
        payload = {
            "ca_number": ca_number,
            "billing_month": billing_month,
            "billing_year": billing_year,
            "status": status,
        }
        if reason_code is not None:
            payload["reason_code"] = reason_code
        if remark is not None:
            payload["remark"] = remark
        if working_reading is not None:
            payload["working_reading"] = working_reading
        return self._patch("/bills/review", payload)

    def batch_sync(self, billing_month, billing_year, reviews):
        """Offline-to-online bulk sync (up to ~1,000 records in one commit)."""
        return self._post("/bills/batch-sync", {
            "billing_month": billing_month,
            "billing_year": billing_year,
            "reviews": reviews,
        })

    def get_automation_queue(self, mru_id=None, cycle=None, limit=50):
        """High-speed FIFO queue for ADB bots - pre-calculated suggested readings."""
        params = {"limit": limit}
        if mru_id:
            params["mru_id"] = mru_id
        if cycle:
            params["cycle"] = cycle
        return self._get("/automation/queue", params=params)


# ---------------------------------------------------------------------------
# Convenience: build a review payload from a human/AI decision
# ---------------------------------------------------------------------------
def build_review(ca_number, status, billing_month, billing_year,
                 working_reading=None, reason_code=None, remark=None):
    """Helper to assemble a review dict for batch_sync()."""
    if status not in REVIEW_STATUSES:
        raise ValueError(f"status must be one of {REVIEW_STATUSES}")
    r = {
        "ca_number": ca_number,
        "status": status,
    }
    if working_reading is not None:
        r["working_reading"] = working_reading
    if reason_code is not None:
        r["reason_code"] = reason_code
    if remark is not None:
        r["remark"] = remark
    return r