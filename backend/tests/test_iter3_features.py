"""Iteration 3: upcoming recurring, copy budgets, year export."""
import os
import io
import uuid
import pytest
import requests
from pathlib import Path
from openpyxl import load_workbook

env_path = Path("/app/frontend/.env")
for line in env_path.read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip()

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _email(tag="x"):
    return f"TEST_{tag}_{uuid.uuid4().hex[:10]}@test.local"


@pytest.fixture(scope="module")
def user():
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"email": _email("i3"), "password": "Secret@123", "name": "Iter3"})
    assert r.status_code == 200, r.text
    return s


# ---------- /api/recurring/upcoming ----------
class TestUpcomingRecurring:
    def test_upcoming_within_window(self, user):
        # Create recurring on day 1 of month, start_month 2026-01
        r = user.post(f"{API}/recurring", json={"name": "TEST upc rent", "amount": 1200, "day": 1,
                                                "category": "moradia", "start_month": "2026-01", "active": True})
        assert r.status_code == 200
        rid = r.json()["id"]
        # today = 2026-11-29, next day-1 is 2026-12-01 => days_left 2
        r = user.get(f"{API}/recurring/upcoming", params={"today": "2026-11-29", "days": 3})
        assert r.status_code == 200
        items = r.json()
        got = [x for x in items if x["id"] == rid]
        assert len(got) == 1
        assert got[0]["due_date"] == "2026-12-01"
        assert got[0]["days_left"] == 2
        # Day 15 next month: not in 3-day window
        r2 = user.post(f"{API}/recurring", json={"name": "TEST upc far", "amount": 50, "day": 15,
                                                 "category": "assinaturas", "start_month": "2026-01", "active": True})
        rid2 = r2.json()["id"]
        r = user.get(f"{API}/recurring/upcoming", params={"today": "2026-11-29", "days": 3})
        assert not any(x["id"] == rid2 for x in r.json())
        # Cleanup
        user.delete(f"{API}/recurring/{rid}")
        user.delete(f"{API}/recurring/{rid2}")

    def test_due_today_days_left_0(self, user):
        rec = user.post(f"{API}/recurring", json={"name": "TEST today", "amount": 10, "day": 10,
                                                  "category": "assinaturas", "start_month": "2026-01", "active": True}).json()
        r = user.get(f"{API}/recurring/upcoming", params={"today": "2026-05-10", "days": 3}).json()
        got = next(x for x in r if x["id"] == rec["id"])
        assert got["days_left"] == 0
        assert got["due_date"] == "2026-05-10"
        user.delete(f"{API}/recurring/{rec['id']}")

    def test_inactive_excluded(self, user):
        rec = user.post(f"{API}/recurring", json={"name": "TEST inactive", "amount": 10, "day": 10,
                                                  "category": "assinaturas", "start_month": "2026-01", "active": False}).json()
        r = user.get(f"{API}/recurring/upcoming", params={"today": "2026-05-09", "days": 3}).json()
        assert not any(x["id"] == rec["id"] for x in r)
        user.delete(f"{API}/recurring/{rec['id']}")

    def test_start_month_future_excluded(self, user):
        rec = user.post(f"{API}/recurring", json={"name": "TEST future", "amount": 10, "day": 5,
                                                  "category": "assinaturas", "start_month": "2030-01", "active": True}).json()
        r = user.get(f"{API}/recurring/upcoming", params={"today": "2026-05-04", "days": 3}).json()
        assert not any(x["id"] == rec["id"] for x in r)
        user.delete(f"{API}/recurring/{rec['id']}")

    def test_day_clamped_to_month_length(self, user):
        # day 31 should land on last day of February (28 in 2026)
        rec = user.post(f"{API}/recurring", json={"name": "TEST clamp", "amount": 10, "day": 31,
                                                  "category": "assinaturas", "start_month": "2026-01", "active": True}).json()
        r = user.get(f"{API}/recurring/upcoming", params={"today": "2026-02-27", "days": 3}).json()
        got = next((x for x in r if x["id"] == rec["id"]), None)
        assert got is not None
        assert got["due_date"] == "2026-02-28"
        user.delete(f"{API}/recurring/{rec['id']}")

    def test_requires_auth(self):
        r = requests.get(f"{API}/recurring/upcoming", params={"today": "2026-05-01", "days": 3})
        assert r.status_code == 401


# ---------- /api/budgets/copy ----------
class TestCopyBudgets:
    def test_copy_defaults_and_overrides(self, user):
        # Setup: default for mercado=500, override for mercado=800 in 2027-01, and viagens override only=200
        user.put(f"{API}/budgets", json={"category": "mercado", "limit": 500})
        user.put(f"{API}/budgets", json={"category": "mercado", "limit": 800, "month": "2027-01"})
        user.put(f"{API}/budgets", json={"category": "viagens", "limit": 200, "month": "2027-01"})

        r = user.post(f"{API}/budgets/copy", json={"from_month": "2027-01", "to_month": "2027-02"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["to_month"] == "2027-02"
        assert data["count"] == 2

        s = user.get(f"{API}/summary?month=2027-02").json()
        mercado = next(x for x in s["budgets"] if x["category"] == "mercado")
        assert mercado["limit"] == 800
        assert mercado["override"] is True  # 800 != default 500, so override
        viagens = next(x for x in s["budgets"] if x["category"] == "viagens")
        assert viagens["limit"] == 200
        assert viagens["override"] is True
        # Cleanup overrides
        user.delete(f"{API}/budgets/mercado", params={"month": "2027-01"})
        user.delete(f"{API}/budgets/mercado", params={"month": "2027-02"})
        user.delete(f"{API}/budgets/viagens", params={"month": "2027-01"})
        user.delete(f"{API}/budgets/viagens", params={"month": "2027-02"})

    def test_copy_equal_to_default_no_override(self, user):
        # default mercado = 500 still
        # source month: use effective (no override) = default 500 for mercado
        r = user.post(f"{API}/budgets/copy", json={"from_month": "2028-01", "to_month": "2028-02"})
        assert r.status_code == 200
        s = user.get(f"{API}/summary?month=2028-02").json()
        mercado = next(x for x in s["budgets"] if x["category"] == "mercado")
        # Since value equals default, no override should be written
        assert mercado["override"] is False
        assert mercado["limit"] == 500

    def test_copy_same_month_422(self, user):
        r = user.post(f"{API}/budgets/copy", json={"from_month": "2027-01", "to_month": "2027-01"})
        assert r.status_code == 422

    def test_copy_no_source_400(self, user):
        # Register a fresh user with zero budgets
        s = requests.Session()
        s.post(f"{API}/auth/register", json={"email": _email("empty"), "password": "Secret@123", "name": "Empty"})
        r = s.post(f"{API}/budgets/copy", json={"from_month": "2027-01", "to_month": "2027-02"})
        assert r.status_code == 400

    def test_copy_requires_auth(self):
        r = requests.post(f"{API}/budgets/copy", json={"from_month": "2027-01", "to_month": "2027-02"})
        assert r.status_code == 401

    def test_cleanup_defaults(self, user):
        # Clean up default budget created above
        user.delete(f"{API}/budgets/mercado")


# ---------- /api/export/year ----------
class TestExportYear:
    def test_year_xlsx_has_sheets_and_resumo(self, user):
        # Seed in two different months of 2029
        user.post(f"{API}/transactions", json={"type": "income", "amount": 1000, "category": "salario",
                                               "description": "TEST yr jan", "date": "2029-01-05"})
        user.post(f"{API}/transactions", json={"type": "expense", "amount": 200, "category": "mercado",
                                               "description": "TEST yr feb", "date": "2029-02-10"})
        r = user.get(f"{API}/export/year", params={"year": 2029})
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        assert "finance-nunes-2029.xlsx" in r.headers.get("content-disposition", "")
        wb = load_workbook(io.BytesIO(r.content))
        # Resumo + 12 month tabs
        expected = ["Resumo", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        assert wb.sheetnames == expected
        resumo_text = "\n".join(" | ".join(str(c) if c is not None else "" for c in row)
                                for row in wb["Resumo"].iter_rows(values_only=True))
        assert "Total do ano" in resumo_text
        assert "Despesas por categoria" in resumo_text
        # Monthly rows should be in Resumo
        assert "Janeiro" in resumo_text
        # January sheet contains TEST yr jan
        jan_text = "\n".join(" | ".join(str(c) if c is not None else "" for c in row)
                              for row in wb["Janeiro"].iter_rows(values_only=True))
        assert "TEST yr jan" in jan_text
        fev_text = "\n".join(" | ".join(str(c) if c is not None else "" for c in row)
                              for row in wb["Fevereiro"].iter_rows(values_only=True))
        assert "TEST yr feb" in fev_text

    def test_year_invalid(self, user):
        r = user.get(f"{API}/export/year", params={"year": 1500})
        assert r.status_code == 422

    def test_year_requires_auth(self):
        r = requests.get(f"{API}/export/year", params={"year": 2029})
        assert r.status_code == 401
