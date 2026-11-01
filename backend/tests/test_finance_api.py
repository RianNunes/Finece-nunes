"""Finance Nunes backend API tests. Uses REACT_APP_BACKEND_URL public URL."""
import os
import time
import uuid
import re
import pytest
import requests
from pathlib import Path

# Load frontend .env to get REACT_APP_BACKEND_URL
env_path = Path("/app/frontend/.env")
for line in env_path.read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip()

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "rian@financenunes.com"
ADMIN_PASS = "Nunes@2026"


def _new_email(tag="u"):
    return f"TEST_{tag}_{uuid.uuid4().hex[:10]}@test.local"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def user_a():
    s = requests.Session()
    email = _new_email("a")
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Secret@123", "name": "User A"})
    assert r.status_code == 200, r.text
    s.email = email
    return s


@pytest.fixture(scope="module")
def user_b():
    s = requests.Session()
    email = _new_email("b")
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Secret@123", "name": "User B"})
    assert r.status_code == 200, r.text
    s.email = email
    return s


# ---------------- Auth ----------------
class TestAuth:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        assert r.json().get("app") == "Finance Nunes"

    def test_admin_login(self, admin):
        r = admin.get(f"{API}/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        assert "_id" not in data
        assert "id" in data

    def test_invalid_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": "nouser@test.local", "password": "wrongpass"})
        assert r.status_code == 401

    def test_duplicate_register(self, user_a):
        r = requests.post(f"{API}/auth/register", json={"email": user_a.email, "password": "Secret@123"})
        assert r.status_code == 400

    def test_bad_email_format(self):
        r = requests.post(f"{API}/auth/register", json={"email": "notanemail", "password": "Secret@123"})
        assert r.status_code == 422

    def test_short_password(self):
        r = requests.post(f"{API}/auth/register", json={"email": _new_email("p"), "password": "123"})
        assert r.status_code == 422

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_brute_force_lockout(self):
        # Use a throwaway user — do NOT lock the admin.
        s = requests.Session()
        email = _new_email("bf")
        s.post(f"{API}/auth/register", json={"email": email, "password": "Secret@123"})
        # Fail 5 times
        last = None
        for _ in range(5):
            last = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrongwrong"})
            assert last.status_code == 401
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrongwrong"})
        assert r.status_code == 429, f"Expected 429 after 5 fails, got {r.status_code}"

    def test_profile_update(self, user_a):
        new_name = "User A Renamed"
        r = user_a.put(f"{API}/auth/me", json={"name": new_name, "email": user_a.email})
        assert r.status_code == 200
        assert r.json()["name"] == new_name
        r2 = user_a.get(f"{API}/auth/me")
        assert r2.json()["name"] == new_name


# ---------------- Transactions ----------------
class TestTransactions:
    def test_create_income(self, user_a):
        r = user_a.post(f"{API}/transactions", json={
            "type": "income", "amount": 3000.00, "category": "salario",
            "description": "TEST salario", "date": "2026-01-10"})
        assert r.status_code == 200, r.text
        tx = r.json()
        assert tx["amount"] == 3000.00
        user_a.income_id = tx["id"]

    def test_create_expense(self, user_a):
        r = user_a.post(f"{API}/transactions", json={
            "type": "expense", "amount": 150.50, "category": "mercado",
            "description": "TEST mercado", "date": "2026-01-11"})
        assert r.status_code == 200, r.text
        user_a.expense_id = r.json()["id"]

    def test_invalid_category_for_type(self, user_a):
        r = user_a.post(f"{API}/transactions", json={
            "type": "income", "amount": 100, "category": "mercado", "description": "", "date": "2026-01-01"})
        assert r.status_code == 422

    def test_invalid_date(self, user_a):
        r = user_a.post(f"{API}/transactions", json={
            "type": "expense", "amount": 10, "category": "mercado", "description": "", "date": "2026/01/01"})
        assert r.status_code == 422

    def test_negative_amount(self, user_a):
        r = user_a.post(f"{API}/transactions", json={
            "type": "expense", "amount": -5, "category": "mercado", "description": "", "date": "2026-01-01"})
        assert r.status_code == 422

    def test_list_month(self, user_a):
        r = user_a.get(f"{API}/transactions?month=2026-01")
        assert r.status_code == 200
        items = r.json()
        descs = [i.get("description") for i in items]
        assert "TEST salario" in descs
        assert "TEST mercado" in descs

    def test_update_transaction(self, user_a):
        r = user_a.put(f"{API}/transactions/{user_a.expense_id}", json={
            "type": "expense", "amount": 199.99, "category": "mercado",
            "description": "TEST mercado upd", "date": "2026-01-11"})
        assert r.status_code == 200
        assert r.json()["amount"] == 199.99

    def test_invalid_month_format(self, user_a):
        r = user_a.get(f"{API}/transactions?month=bad")
        assert r.status_code == 422

    def test_isolation_user_b_cannot_edit(self, user_a, user_b):
        r = user_b.put(f"{API}/transactions/{user_a.expense_id}", json={
            "type": "expense", "amount": 1, "category": "mercado", "description": "", "date": "2026-01-11"})
        assert r.status_code == 404

    def test_isolation_user_b_cannot_delete(self, user_a, user_b):
        r = user_b.delete(f"{API}/transactions/{user_a.expense_id}")
        assert r.status_code == 404

    def test_isolation_list_separate(self, user_a, user_b):
        r = user_b.get(f"{API}/transactions?month=2026-01")
        assert r.status_code == 200
        for i in r.json():
            assert i.get("description") not in ("TEST salario", "TEST mercado upd")


# ---------------- Installments ----------------
class TestInstallments:
    def test_create_3x(self, user_a):
        r = user_a.post(f"{API}/installments", json={
            "description": "TEST notebook", "total_amount": 300.00,
            "installments": 3, "category": "compras", "start_date": "2026-02-15"})
        assert r.status_code == 200, r.text
        assert r.json()["count"] == 3
        user_a.inst_group = r.json()["group_id"]

    def test_installment_months(self, user_a):
        months = {"2026-02", "2026-03", "2026-04"}
        for m in months:
            r = user_a.get(f"{API}/transactions?month={m}")
            assert r.status_code == 200
            got = [t for t in r.json() if t.get("description") == "TEST notebook"]
            assert len(got) == 1, f"month {m} missing installment"
            assert got[0]["installment_total"] == 3

    def test_list_installments(self, user_a):
        r = user_a.get(f"{API}/installments")
        assert r.status_code == 200
        groups = [g for g in r.json() if g.get("description") == "TEST notebook"]
        assert len(groups) == 1
        assert groups[0]["installments"] == 3
        assert round(groups[0]["total"], 2) == 300.00

    def test_delete_installments(self, user_a):
        r = user_a.delete(f"{API}/installments/{user_a.inst_group}")
        assert r.status_code == 200
        r2 = user_a.get(f"{API}/transactions?month=2026-02")
        assert all(t.get("description") != "TEST notebook" for t in r2.json())


# ---------------- Recurring ----------------
class TestRecurring:
    def test_create(self, user_a):
        r = user_a.post(f"{API}/recurring", json={
            "name": "TEST aluguel", "amount": 800, "day": 5,
            "category": "moradia", "start_month": "2026-01", "active": True})
        assert r.status_code == 200, r.text
        user_a.rec_id = r.json()["id"]

    def test_appears_in_month(self, user_a):
        r = user_a.get(f"{API}/transactions?month=2026-01")
        items = r.json()
        found = [i for i in items if i.get("description") == "TEST aluguel" and i.get("recurring")]
        assert len(found) == 1

    def test_included_in_summary_expense(self, user_a):
        r = user_a.get(f"{API}/summary?month=2026-01")
        assert r.status_code == 200
        s = r.json()
        assert s["recurring_total"] >= 800
        assert s["expense"] >= 800

    def test_update(self, user_a):
        r = user_a.put(f"{API}/recurring/{user_a.rec_id}", json={
            "name": "TEST aluguel upd", "amount": 850, "day": 5,
            "category": "moradia", "active": True})
        assert r.status_code == 200
        assert r.json()["amount"] == 850

    def test_delete(self, user_a):
        r = user_a.delete(f"{API}/recurring/{user_a.rec_id}")
        assert r.status_code == 200


# ---------------- Budgets ----------------
class TestBudgets:
    def test_upsert(self, user_a):
        r = user_a.put(f"{API}/budgets", json={"category": "mercado", "limit": 500})
        assert r.status_code == 200
        assert r.json()["limit"] == 500

    def test_summary_has_budget_with_spent(self, user_a):
        r = user_a.get(f"{API}/summary?month=2026-01")
        s = r.json()
        b = next((x for x in s["budgets"] if x["category"] == "mercado"), None)
        assert b is not None
        assert b["limit"] == 500
        assert b["spent"] >= 0

    def test_update_limit(self, user_a):
        r = user_a.put(f"{API}/budgets", json={"category": "mercado", "limit": 700})
        assert r.status_code == 200
        assert r.json()["limit"] == 700

    def test_invalid_category(self, user_a):
        r = user_a.put(f"{API}/budgets", json={"category": "nonsense", "limit": 100})
        assert r.status_code == 422

    def test_delete(self, user_a):
        r = user_a.delete(f"{API}/budgets/mercado")
        assert r.status_code == 200
        r2 = user_a.delete(f"{API}/budgets/mercado")
        assert r2.status_code == 404


# ---------------- Goals ----------------
class TestGoals:
    def test_create(self, user_a):
        r = user_a.post(f"{API}/goals", json={"name": "TEST viagem", "target": 5000, "saved": 0, "deadline": "2026-12-31"})
        assert r.status_code == 200
        user_a.goal_id = r.json()["id"]

    def test_contribute(self, user_a):
        r = user_a.post(f"{API}/goals/{user_a.goal_id}/contribute", json={"amount": 250})
        assert r.status_code == 200
        assert r.json()["saved"] == 250
        r2 = user_a.post(f"{API}/goals/{user_a.goal_id}/contribute", json={"amount": 100})
        assert r2.json()["saved"] == 350

    def test_update(self, user_a):
        r = user_a.put(f"{API}/goals/{user_a.goal_id}", json={"name": "TEST viagem BR", "target": 6000, "saved": 350})
        assert r.status_code == 200
        assert r.json()["target"] == 6000

    def test_isolation(self, user_a, user_b):
        r = user_b.post(f"{API}/goals/{user_a.goal_id}/contribute", json={"amount": 10})
        assert r.status_code == 404

    def test_delete(self, user_a):
        r = user_a.delete(f"{API}/goals/{user_a.goal_id}")
        assert r.status_code == 200


# ---------------- Summary / 50-30-20 ----------------
class TestSummary:
    def test_summary_fields(self, user_a):
        r = user_a.get(f"{API}/summary?month=2026-01")
        assert r.status_code == 200
        s = r.json()
        for k in ["month", "income", "expense", "balance", "by_category", "groups", "rule", "budgets", "history"]:
            assert k in s
        assert len(s["history"]) == 6
        for grp in ["needs", "wants", "savings"]:
            assert grp in s["rule"]
            assert s["rule"][grp]["pct"] in (50, 30, 20)


# ---------------- Chat ----------------
class TestChat:
    def test_history_empty_or_list(self, user_a):
        r = user_a.get(f"{API}/chat/history")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_chat_stream(self, user_a):
        r = user_a.post(f"{API}/chat", json={"message": "Qual meu saldo em janeiro de 2026?"}, stream=True, timeout=60)
        assert r.status_code == 200
        got_delta = False
        got_done = False
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if '"delta"' in payload:
                got_delta = True
            if '"done"' in payload:
                got_done = True
                break
            if '"error"' in payload:
                pytest.fail(f"Chat error: {payload}")
        assert got_done, "SSE did not finish"
        # delta may or may not be present but historically should be
        assert got_delta, "No text delta received"

    def test_history_persists(self, user_a):
        time.sleep(1)
        r = user_a.get(f"{API}/chat/history")
        assert r.status_code == 200
        msgs = r.json()
        assert any(m["role"] == "user" for m in msgs)
        assert any(m["role"] == "assistant" for m in msgs)

    def test_clear_history(self, user_a):
        r = user_a.delete(f"{API}/chat/history")
        assert r.status_code == 200
        r2 = user_a.get(f"{API}/chat/history")
        assert r2.json() == []
