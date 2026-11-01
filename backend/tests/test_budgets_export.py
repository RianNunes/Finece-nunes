"""Tests for new features: per-month budget overrides and xlsx export."""
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
    r = s.post(f"{API}/auth/register", json={"email": _email("be"), "password": "Secret@123", "name": "BE User"})
    assert r.status_code == 200, r.text
    return s


# ---------- Budget overrides ----------
class TestBudgetOverride:
    def test_default_budget_applies_to_all_months(self, user):
        # Create default (month=null)
        r = user.put(f"{API}/budgets", json={"category": "lazer", "limit": 400})
        assert r.status_code == 200
        data = r.json()
        assert data["limit"] == 400
        assert data["month"] is None

        for m in ("2026-01", "2026-02", "2026-03"):
            s = user.get(f"{API}/summary?month={m}").json()
            b = next((x for x in s["budgets"] if x["category"] == "lazer"), None)
            assert b is not None, f"missing in {m}"
            assert b["limit"] == 400
            assert b["override"] is False
            assert b["default_limit"] == 400

    def test_override_only_affects_target_month(self, user):
        # Add override for 2026-02 only
        r = user.put(f"{API}/budgets", json={"category": "lazer", "limit": 900, "month": "2026-02"})
        assert r.status_code == 200
        assert r.json()["limit"] == 900
        assert r.json()["month"] == "2026-02"

        s_feb = user.get(f"{API}/summary?month=2026-02").json()
        b_feb = next(x for x in s_feb["budgets"] if x["category"] == "lazer")
        assert b_feb["limit"] == 900
        assert b_feb["override"] is True
        assert b_feb["default_limit"] == 400

        # Other months should still show default
        s_jan = user.get(f"{API}/summary?month=2026-01").json()
        b_jan = next(x for x in s_jan["budgets"] if x["category"] == "lazer")
        assert b_jan["limit"] == 400
        assert b_jan["override"] is False

    def test_delete_override_reverts_to_default(self, user):
        r = user.delete(f"{API}/budgets/lazer", params={"month": "2026-02"})
        assert r.status_code == 200
        s = user.get(f"{API}/summary?month=2026-02").json()
        b = next(x for x in s["budgets"] if x["category"] == "lazer")
        assert b["limit"] == 400
        assert b["override"] is False

    def test_delete_default_removes_everywhere(self, user):
        r = user.delete(f"{API}/budgets/lazer")
        assert r.status_code == 200
        s = user.get(f"{API}/summary?month=2026-01").json()
        assert not any(x["category"] == "lazer" for x in s["budgets"])

    def test_override_without_default(self, user):
        r = user.put(f"{API}/budgets", json={"category": "viagens", "limit": 1500, "month": "2026-03"})
        assert r.status_code == 200
        s = user.get(f"{API}/summary?month=2026-03").json()
        b = next(x for x in s["budgets"] if x["category"] == "viagens")
        assert b["limit"] == 1500
        assert b["override"] is True
        assert b["default_limit"] is None
        # cleanup
        user.delete(f"{API}/budgets/viagens", params={"month": "2026-03"})

    def test_invalid_month_rejected(self, user):
        r = user.put(f"{API}/budgets", json={"category": "lazer", "limit": 100, "month": "bad"})
        assert r.status_code == 422


# ---------- Export xlsx ----------
class TestExport:
    def test_export_contains_transactions_recurring_installments(self, user):
        # Seed data in 2026-05
        assert user.post(f"{API}/transactions", json={"type": "income", "amount": 2500, "category": "salario",
                                                     "description": "TEST salary export", "date": "2026-05-05"}).status_code == 200
        assert user.post(f"{API}/transactions", json={"type": "expense", "amount": 120.50, "category": "mercado",
                                                     "description": "TEST compras export", "date": "2026-05-10"}).status_code == 200
        # Recurring starting 2026-05
        rec = user.post(f"{API}/recurring", json={"name": "TEST assinatura export", "amount": 29.90, "day": 15,
                                                  "category": "assinaturas", "start_month": "2026-05", "active": True}).json()
        # Installments 2x starting 2026-05
        inst = user.post(f"{API}/installments", json={"description": "TEST parcelado export", "total_amount": 200,
                                                     "installments": 2, "category": "compras", "start_date": "2026-05-20"}).json()

        r = user.get(f"{API}/export", params={"month": "2026-05"})
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "spreadsheetml" in ct
        cd = r.headers.get("content-disposition", "")
        assert "finance-nunes-2026-05.xlsx" in cd

        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        # Row 1 title, Row 2 empty, Row 3 headers
        assert rows[0][0] and "2026-05" in rows[0][0]
        assert rows[2] == ("Data", "Tipo", "Categoria", "Descrição", "Observação", "Valor (R$)")

        # Collect data rows
        all_text = "\n".join(" | ".join(str(c) if c is not None else "" for c in row) for row in rows)
        assert "TEST salary export" in all_text
        assert "TEST compras export" in all_text
        assert "TEST assinatura export" in all_text
        assert "Recorrente" in all_text
        assert "TEST parcelado export" in all_text
        assert "Parcela 1/2" in all_text
        # Totals labels present
        assert "Total de receitas" in all_text
        assert "Total de despesas" in all_text
        assert "Saldo" in all_text

        # cleanup
        user.delete(f"{API}/recurring/{rec['id']}")
        user.delete(f"{API}/installments/{inst['group_id']}")

    def test_export_empty_month_still_works(self, user):
        r = user.get(f"{API}/export", params={"month": "2029-11"})
        assert r.status_code == 200
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        # Should have title + header + totals (no data rows)
        all_text = "\n".join(" | ".join(str(c) if c is not None else "" for c in row) for row in ws.iter_rows(values_only=True))
        assert "Total de receitas" in all_text

    def test_export_requires_auth(self):
        r = requests.get(f"{API}/export", params={"month": "2026-05"})
        assert r.status_code == 401

    def test_export_invalid_month(self, user):
        r = user.get(f"{API}/export", params={"month": "bad"})
        assert r.status_code == 422
