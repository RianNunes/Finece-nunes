from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

import io
import os
import re
import json
import uuid
import logging
import calendar
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Literal, Annotated

import bcrypt
import jwt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, BeforeValidator, AfterValidator, ConfigDict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
from files_api import create_files_router
from storage_service import storage

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
JWT_ALGORITHM = "HS256"

app = FastAPI()
api = APIRouter(prefix="/api")
logger = logging.getLogger("finance")
logging.basicConfig(level=logging.INFO)

EXPENSE_GROUPS = {
    "moradia": "needs", "mercado": "needs", "transporte": "needs", "saude": "needs",
    "contas": "needs", "educacao": "needs", "lazer": "wants", "restaurantes": "wants",
    "compras": "wants", "assinaturas": "wants", "viagens": "wants", "cuidados": "wants",
    "dividas": "savings", "investimentos": "savings", "outros": "other",
}
INCOME_CATS = {"salario", "freelance", "rendimentos", "outras_receitas"}
LABELS = {
    "moradia": "Moradia", "mercado": "Mercado", "transporte": "Transporte", "saude": "Saúde",
    "contas": "Contas da casa", "educacao": "Educação", "lazer": "Lazer", "restaurantes": "Restaurantes",
    "compras": "Compras", "assinaturas": "Assinaturas", "viagens": "Viagens", "cuidados": "Cuidados pessoais",
    "dividas": "Dívidas", "investimentos": "Investimentos", "outros": "Outros", "salario": "Salário",
    "freelance": "Freelance", "rendimentos": "Rendimentos", "outras_receitas": "Outras receitas",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
MONTH_NAMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


# ---------- base models ----------
def _to_str(v):
    return str(v) if isinstance(v, ObjectId) else v


PyObjectId = Annotated[str, BeforeValidator(_to_str)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    @classmethod
    def from_mongo(cls, doc):
        return cls.model_validate(doc)

    def to_mongo(self):
        return self.model_dump(exclude={"id"})


class User(BaseDocument):
    email: str
    name: str = ""
    role: str = "user"


class Transaction(BaseDocument):
    user_id: str
    type: Literal["income", "expense"]
    amount: float
    category: str
    description: str = ""
    date: str
    group_id: Optional[str] = None
    installment_no: Optional[int] = None
    installment_total: Optional[int] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Recurring(BaseDocument):
    user_id: str
    name: str
    amount: float
    day: int
    category: str
    start_month: str
    active: bool = True


class Budget(BaseDocument):
    user_id: str
    category: str
    limit: float
    month: Optional[str] = None


class Goal(BaseDocument):
    user_id: str
    name: str
    target: float
    saved: float = 0
    deadline: Optional[str] = None


class ChatMessage(BaseDocument):
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------- inputs ----------
def _check_date(v):
    if v and not DATE_RE.match(v):
        raise ValueError("Data inválida")
    return v


def _check_expense_cat(v):
    if v not in EXPENSE_GROUPS:
        raise ValueError("Categoria inválida")
    return v


DateStr = Annotated[str, AfterValidator(_check_date)]
ExpenseCat = Annotated[str, AfterValidator(_check_expense_cat)]


class TxIn(BaseModel):
    type: Literal["income", "expense"]
    amount: float = Field(gt=0)
    category: str
    description: str = Field(default="", max_length=200)
    date: DateStr


class InstallmentIn(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    total_amount: float = Field(gt=0)
    installments: int = Field(ge=2, le=72)
    category: ExpenseCat
    start_date: DateStr


class RecurringIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0)
    day: int = Field(ge=1, le=31)
    category: ExpenseCat
    start_month: Optional[str] = None
    active: bool = True


class BudgetIn(BaseModel):
    category: ExpenseCat
    limit: float = Field(gt=0)
    month: Optional[str] = None


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target: float = Field(gt=0)
    saved: float = Field(default=0, ge=0)
    deadline: Optional[DateStr] = None


class AmountIn(BaseModel):
    amount: float


class AuthIn(BaseModel):
    email: str
    password: str = Field(min_length=6)
    name: Optional[str] = None


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


# ---------- auth ----------
def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p, h):
    return bcrypt.checkpw(p.encode(), h.encode())


def create_token(user_id, kind, minutes):
    payload = {"sub": user_id, "type": kind, "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes)}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, user_id: str):
    response.set_cookie("access_token", create_token(user_id, "access", 15), httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie("refresh_token", create_token(user_id, "refresh", 60 * 24 * 7), httponly=True, secure=True, samesite="none", max_age=604800, path="/")


async def current_user(request: Request) -> User:
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Não autenticado")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Sessão expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token inválido")
    if payload.get("type") != "access":
        raise HTTPException(401, "Token inválido")
    doc = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not doc:
        raise HTTPException(401, "Usuário não encontrado")
    return User.from_mongo(doc)


def valid_email(e: str) -> str:
    e = e.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e):
        raise HTTPException(422, "E-mail inválido")
    return e


@api.post("/auth/register")
async def register(body: AuthIn, response: Response):
    email = valid_email(body.email)
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Este e-mail já está cadastrado")
    doc = {"email": email, "password_hash": hash_password(body.password), "name": (body.name or "").strip(),
           "role": "user", "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    set_auth_cookies(response, str(res.inserted_id))
    return User.from_mongo(doc).model_dump()


@api.post("/auth/login")
async def login(body: AuthIn, request: Request, response: Response):
    email = valid_email(body.email)
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "x")
    ident = f"{ip}:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    now = datetime.now(timezone.utc)
    if att and att.get("locked_until"):
        if datetime.fromisoformat(att["locked_until"]) > now:
            raise HTTPException(429, "Muitas tentativas. Tente novamente em 15 minutos.")
        await db.login_attempts.delete_many({"identifier": ident})
        att = None
    doc = await db.users.find_one({"email": email})
    if not doc or not verify_password(body.password, doc["password_hash"]):
        count = (att.get("count", 0) if att else 0) + 1
        update = {"count": count}
        if count >= 5:
            update["locked_until"] = (now + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": ident}, {"$set": update}, upsert=True)
        raise HTTPException(401, "E-mail ou senha incorretos")
    await db.login_attempts.delete_many({"identifier": ident})
    set_auth_cookies(response, str(doc["_id"]))
    return User.from_mongo(doc).model_dump()


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Sem sessão")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Sessão expirada")
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Token inválido")
    set_auth_cookies(response, payload["sub"])
    return {"ok": True}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: User = Depends(current_user)):
    return user.model_dump()


@api.put("/auth/me")
async def update_me(body: ProfileIn, user: User = Depends(current_user)):
    email = valid_email(body.email)
    other = await db.users.find_one({"email": email})
    if other and str(other["_id"]) != user.id:
        raise HTTPException(400, "Este e-mail já está em uso")
    await db.users.update_one({"_id": ObjectId(user.id)}, {"$set": {"name": body.name.strip(), "email": email}})
    return User.from_mongo(await db.users.find_one({"_id": ObjectId(user.id)})).model_dump()


# ---------- helpers ----------
def oid(s: str) -> ObjectId:
    if not ObjectId.is_valid(s):
        raise HTTPException(404, "Não encontrado")
    return ObjectId(s)


def add_months(date_str: str, n: int) -> str:
    y, m, d = map(int, date_str.split("-"))
    m0 = m - 1 + n
    y += m0 // 12
    m = m0 % 12 + 1
    d = min(d, calendar.monthrange(y, m)[1])
    return f"{y:04d}-{m:02d}-{d:02d}"


def shift_month(month: str, n: int) -> str:
    return add_months(f"{month}-01", n)[:7]


def this_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def check_month(month: Optional[str]) -> str:
    month = month or this_month()
    if not MONTH_RE.match(month):
        raise HTTPException(422, "Mês inválido")
    return month


def recurring_as_tx(r: Recurring, month: str) -> dict:
    y, m = map(int, month.split("-"))
    day = min(r.day, calendar.monthrange(y, m)[1])
    return {"id": f"rec-{r.id}-{month}", "recurring_id": r.id, "recurring": True, "type": "expense",
            "amount": r.amount, "category": r.category, "description": r.name, "date": f"{month}-{day:02d}"}


async def month_items(uid: str, month: str) -> list:
    txs = await db.transactions.find({"user_id": uid, "date": {"$regex": f"^{month}"}}).sort("date", -1).to_list(5000)
    items = [Transaction.from_mongo(t).model_dump() for t in txs]
    recs = await db.recurring.find({"user_id": uid, "active": True, "start_month": {"$lte": month}}).to_list(500)
    items += [recurring_as_tx(Recurring.from_mongo(r), month) for r in recs]
    return sorted(items, key=lambda x: x["date"], reverse=True)


def totals(items: list) -> dict:
    income = sum(i["amount"] for i in items if i["type"] == "income")
    expense = sum(i["amount"] for i in items if i["type"] == "expense")
    by_cat = {}
    for i in items:
        if i["type"] == "expense":
            by_cat[i["category"]] = by_cat.get(i["category"], 0) + i["amount"]
    return {"income": round(income, 2), "expense": round(expense, 2), "balance": round(income - expense, 2), "by_category": by_cat}


# ---------- transactions ----------
def validate_tx(body: TxIn):
    ok = body.category in (EXPENSE_GROUPS if body.type == "expense" else INCOME_CATS)
    if not ok:
        raise HTTPException(422, "Categoria inválida para este tipo")


@api.get("/transactions")
async def list_transactions(month: Optional[str] = None, user: User = Depends(current_user)):
    return await month_items(user.id, check_month(month))


@api.post("/transactions")
async def create_transaction(body: TxIn, user: User = Depends(current_user)):
    validate_tx(body)
    tx = Transaction(user_id=user.id, **body.model_dump())
    res = await db.transactions.insert_one(tx.to_mongo())
    tx.id = str(res.inserted_id)
    return tx.model_dump()


@api.put("/transactions/{tx_id}")
async def update_transaction(tx_id: str, body: TxIn, user: User = Depends(current_user)):
    validate_tx(body)
    res = await db.transactions.update_one({"_id": oid(tx_id), "user_id": user.id}, {"$set": body.model_dump()})
    if not res.matched_count:
        raise HTTPException(404, "Movimentação não encontrada")
    return Transaction.from_mongo(await db.transactions.find_one({"_id": oid(tx_id)})).model_dump()


@api.delete("/transactions/{tx_id}")
async def delete_transaction(tx_id: str, user: User = Depends(current_user)):
    res = await db.transactions.delete_one({"_id": oid(tx_id), "user_id": user.id})
    if not res.deleted_count:
        raise HTTPException(404, "Movimentação não encontrada")
    return {"ok": True}


# ---------- installments ----------
@api.post("/installments")
async def create_installments(body: InstallmentIn, user: User = Depends(current_user)):
    group = str(uuid.uuid4())
    base = round(body.total_amount / body.installments, 2)
    last = round(body.total_amount - base * (body.installments - 1), 2)
    docs = [Transaction(user_id=user.id, type="expense", amount=last if i == body.installments - 1 else base,
                        category=body.category, description=body.description, date=add_months(body.start_date, i),
                        group_id=group, installment_no=i + 1, installment_total=body.installments).to_mongo()
            for i in range(body.installments)]
    await db.transactions.insert_many(docs)
    return {"group_id": group, "count": len(docs)}


@api.get("/installments")
async def list_installments(user: User = Depends(current_user)):
    pipeline = [
        {"$match": {"user_id": user.id, "group_id": {"$ne": None}}},
        {"$sort": {"date": 1}},
        {"$group": {"_id": "$group_id", "description": {"$first": "$description"}, "category": {"$first": "$category"},
                    "total": {"$sum": "$amount"}, "installments": {"$first": "$installment_total"},
                    "start_date": {"$first": "$date"}, "end_date": {"$last": "$date"}, "dates": {"$push": "$date"},
                    "installment_amount": {"$first": "$amount"}}},
        {"$sort": {"start_date": -1}},
    ]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = []
    async for g in db.transactions.aggregate(pipeline):
        paid = sum(1 for d in g.pop("dates") if d <= today)
        g["group_id"] = g.pop("_id")
        g["paid"] = paid
        g["total"] = round(g["total"], 2)
        out.append(g)
    return out


@api.delete("/installments/{group_id}")
async def delete_installments(group_id: str, user: User = Depends(current_user)):
    res = await db.transactions.delete_many({"user_id": user.id, "group_id": group_id})
    if not res.deleted_count:
        raise HTTPException(404, "Compra parcelada não encontrada")
    return {"ok": True}


# ---------- recurring ----------
@api.get("/recurring/upcoming")
async def upcoming_recurring(today: Optional[str] = None, days: int = 3, user: User = Depends(current_user)):
    base = date.fromisoformat(today) if today and DATE_RE.match(today) else datetime.now(timezone.utc).date()
    days = max(0, min(days, 31))
    out = []
    for doc in await db.recurring.find({"user_id": user.id, "active": True}).to_list(500):
        r = Recurring.from_mongo(doc)
        for off in range(days + 1):
            d = base + timedelta(days=off)
            if r.start_month > d.strftime("%Y-%m"):
                continue
            if d.day == min(r.day, calendar.monthrange(d.year, d.month)[1]):
                out.append({**r.model_dump(), "due_date": d.isoformat(), "days_left": off})
                break
    return sorted(out, key=lambda x: (x["days_left"], -x["amount"]))


@api.get("/recurring")
async def list_recurring(user: User = Depends(current_user)):
    docs = await db.recurring.find({"user_id": user.id}).sort("day", 1).to_list(500)
    return [Recurring.from_mongo(d).model_dump() for d in docs]


@api.post("/recurring")
async def create_recurring(body: RecurringIn, user: User = Depends(current_user)):
    data = body.model_dump()
    data["start_month"] = check_month(data.get("start_month"))
    r = Recurring(user_id=user.id, **data)
    res = await db.recurring.insert_one(r.to_mongo())
    r.id = str(res.inserted_id)
    return r.model_dump()


@api.put("/recurring/{rid}")
async def update_recurring(rid: str, body: RecurringIn, user: User = Depends(current_user)):
    data = body.model_dump()
    if data.get("start_month"):
        check_month(data["start_month"])
    else:
        data.pop("start_month")
    res = await db.recurring.update_one({"_id": oid(rid), "user_id": user.id}, {"$set": data})
    if not res.matched_count:
        raise HTTPException(404, "Recorrente não encontrada")
    return Recurring.from_mongo(await db.recurring.find_one({"_id": oid(rid)})).model_dump()


@api.delete("/recurring/{rid}")
async def delete_recurring(rid: str, user: User = Depends(current_user)):
    res = await db.recurring.delete_one({"_id": oid(rid), "user_id": user.id})
    if not res.deleted_count:
        raise HTTPException(404, "Recorrente não encontrada")
    return {"ok": True}


# ---------- budgets ----------
@api.get("/budgets")
async def list_budgets(user: User = Depends(current_user)):
    return [Budget.from_mongo(d).model_dump() for d in await db.budgets.find({"user_id": user.id}).to_list(100)]


@api.put("/budgets")
async def upsert_budget(body: BudgetIn, user: User = Depends(current_user)):
    q = {"user_id": user.id, "category": body.category, "month": check_month(body.month) if body.month else None}
    await db.budgets.update_one(q, {"$set": {"limit": body.limit, "month": q["month"]}}, upsert=True)
    return Budget.from_mongo(await db.budgets.find_one(q)).model_dump()


async def effective_budgets(uid: str, month: str):
    defaults, overrides = {}, {}
    for d in await db.budgets.find({"user_id": uid, "month": {"$in": [None, month]}}).to_list(200):
        b = Budget.from_mongo(d)
        (overrides if b.month else defaults)[b.category] = b
    return defaults, overrides


class CopyBudgetsIn(BaseModel):
    from_month: str
    to_month: str


@api.post("/budgets/copy")
async def copy_budgets(body: CopyBudgetsIn, user: User = Depends(current_user)):
    src, dst = check_month(body.from_month), check_month(body.to_month)
    if src == dst:
        raise HTTPException(422, "Escolha meses diferentes")
    defaults, overrides = await effective_budgets(user.id, src)
    source = {**{c: b.limit for c, b in defaults.items()}, **{c: b.limit for c, b in overrides.items()}}
    if not source:
        raise HTTPException(400, "Não há orçamentos para copiar neste mês")
    for cat, limit in source.items():
        q = {"user_id": user.id, "category": cat, "month": dst}
        if cat in defaults and defaults[cat].limit == limit:
            await db.budgets.delete_one(q)
        else:
            await db.budgets.update_one(q, {"$set": {"limit": limit}}, upsert=True)
    return {"ok": True, "count": len(source), "to_month": dst}


@api.delete("/budgets/{category}")
async def delete_budget(category: str, month: Optional[str] = None, user: User = Depends(current_user)):
    res = await db.budgets.delete_one({"user_id": user.id, "category": category, "month": check_month(month) if month else None})
    if not res.deleted_count:
        raise HTTPException(404, "Orçamento não encontrado")
    return {"ok": True}


# ---------- goals ----------
@api.get("/goals")
async def list_goals(user: User = Depends(current_user)):
    return [Goal.from_mongo(d).model_dump() for d in await db.goals.find({"user_id": user.id}).to_list(100)]


@api.post("/goals")
async def create_goal(body: GoalIn, user: User = Depends(current_user)):
    g = Goal(user_id=user.id, **body.model_dump())
    res = await db.goals.insert_one(g.to_mongo())
    g.id = str(res.inserted_id)
    return g.model_dump()


@api.put("/goals/{gid}")
async def update_goal(gid: str, body: GoalIn, user: User = Depends(current_user)):
    res = await db.goals.update_one({"_id": oid(gid), "user_id": user.id}, {"$set": body.model_dump()})
    if not res.matched_count:
        raise HTTPException(404, "Meta não encontrada")
    return Goal.from_mongo(await db.goals.find_one({"_id": oid(gid)})).model_dump()


@api.post("/goals/{gid}/contribute")
async def contribute_goal(gid: str, body: AmountIn, user: User = Depends(current_user)):
    doc = await db.goals.find_one({"_id": oid(gid), "user_id": user.id})
    if not doc:
        raise HTTPException(404, "Meta não encontrada")
    saved = max(0, round(doc.get("saved", 0) + body.amount, 2))
    await db.goals.update_one({"_id": doc["_id"]}, {"$set": {"saved": saved}})
    doc["saved"] = saved
    return Goal.from_mongo(doc).model_dump()


@api.delete("/goals/{gid}")
async def delete_goal(gid: str, user: User = Depends(current_user)):
    res = await db.goals.delete_one({"_id": oid(gid), "user_id": user.id})
    if not res.deleted_count:
        raise HTTPException(404, "Meta não encontrada")
    return {"ok": True}


# ---------- summary ----------
async def build_summary(uid: str, month: str) -> dict:
    items = await month_items(uid, month)
    t = totals(items)
    groups = {"needs": 0, "wants": 0, "savings": 0, "other": 0}
    for cat, amt in t["by_category"].items():
        groups[EXPENSE_GROUPS.get(cat, "other")] += amt
    targets = {"needs": 0.5, "wants": 0.3, "savings": 0.2}
    rule = {k: {"spent": round(groups[k], 2), "target": round(t["income"] * p, 2), "pct": int(p * 100)} for k, p in targets.items()}
    defaults, overrides = await effective_budgets(uid, month)
    budgets = []
    for cat in sorted(set(defaults) | set(overrides), key=lambda c: list(EXPENSE_GROUPS).index(c)):
        b, base = overrides.get(cat) or defaults[cat], defaults.get(cat)
        budgets.append({**b.model_dump(), "spent": round(t["by_category"].get(cat, 0), 2), "override": bool(b.month),
                        "default_limit": base.limit if base else None})
    history = []
    for i in range(5, -1, -1):
        m = shift_month(month, -i)
        mt = totals(await month_items(uid, m)) if m != month else t
        history.append({"month": m, "income": mt["income"], "expense": mt["expense"]})
    return {"month": month, **t, "by_category": [{"category": k, "amount": round(v, 2)} for k, v in sorted(t["by_category"].items(), key=lambda x: -x[1])],
            "groups": {k: round(v, 2) for k, v in groups.items()}, "rule": rule, "budgets": budgets, "history": history,
            "recurring_total": round(sum(i["amount"] for i in items if i.get("recurring")), 2), "count": len(items)}


@api.get("/summary")
async def summary(month: Optional[str] = None, user: User = Depends(current_user)):
    return await build_summary(user.id, check_month(month))


# ---------- export ----------
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MONEY = '"R$" #,##0.00;[Red]-"R$" #,##0.00'
HEAD_FONT, HEAD_FILL = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1E3A8A")


def month_title(month: str) -> str:
    y, m = month.split("-")
    return f"{MONTH_NAMES[int(m) - 1]} de {y}"


def header_row(ws, cols):
    ws.append(cols)
    for c in ws[ws.max_row]:
        c.font, c.fill = HEAD_FONT, HEAD_FILL


def total_rows(ws, t, label_col=5):
    ws.append([])
    for label, v in (("Total de receitas", t["income"]), ("Total de despesas", -t["expense"]), ("Saldo", t["balance"])):
        ws.append([""] * (label_col - 1) + [label, v])
        ws.cell(ws.max_row, label_col).font = Font(bold=True)
        ws.cell(ws.max_row, label_col + 1).number_format = MONEY
        ws.cell(ws.max_row, label_col + 1).font = Font(bold=True)


def fill_month_sheet(ws, month: str, items: list):
    ws.append([f"Finance Nunes – movimentações de {month_title(month)}"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    header_row(ws, ["Data", "Tipo", "Categoria", "Descrição", "Observação", "Valor (R$)"])
    for it in sorted(items, key=lambda x: x["date"]):
        obs = "Recorrente" if it.get("recurring") else (f"Parcela {it['installment_no']}/{it['installment_total']}" if it.get("installment_no") else "")
        y, m, d = it["date"].split("-")
        val = it["amount"] if it["type"] == "income" else -it["amount"]
        ws.append([f"{d}/{m}/{y}", "Receita" if it["type"] == "income" else "Despesa", LABELS.get(it["category"], it["category"]), it.get("description", ""), obs, val])
        ws.cell(ws.max_row, 6).number_format = MONEY
    if not items:
        ws.append(["Sem movimentações neste mês"])
    total_rows(ws, totals(items))
    for col, w in zip("ABCDEF", (12, 10, 18, 36, 16, 16)):
        ws.column_dimensions[col].width = w


def xlsx_response(wb, filename):
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api.get("/export")
async def export_month(month: Optional[str] = None, user: User = Depends(current_user)):
    month = check_month(month)
    wb = Workbook()
    wb.active.title = month_title(month)[:31]
    fill_month_sheet(wb.active, month, await month_items(user.id, month))
    return xlsx_response(wb, f"finance-nunes-{month}.xlsx")


@api.get("/export/year")
async def export_year(year: Optional[int] = None, user: User = Depends(current_user)):
    year = year or datetime.now(timezone.utc).year
    if not 2000 <= year <= 2100:
        raise HTTPException(422, "Ano inválido")
    wb = Workbook()
    resume = wb.active
    resume.title = "Resumo"
    resume.append([f"Finance Nunes – resumo de {year}"])
    resume["A1"].font = Font(bold=True, size=14)
    resume.append([])
    header_row(resume, ["Mês", "Receitas (R$)", "Despesas (R$)", "Saldo (R$)"])
    by_cat_year, year_items = {}, []
    for i, name in enumerate(MONTH_NAMES):
        month = f"{year}-{i + 1:02d}"
        items = await month_items(user.id, month)
        year_items += items
        t = totals(items)
        resume.append([name, t["income"], -t["expense"], t["balance"]])
        for c in range(2, 5):
            resume.cell(resume.max_row, c).number_format = MONEY
        for k, v in t["by_category"].items():
            by_cat_year[k] = by_cat_year.get(k, 0) + v
        fill_month_sheet(wb.create_sheet(name), month, items)
    t = totals(year_items)
    resume.append(["Total do ano", t["income"], -t["expense"], t["balance"]])
    for c in range(1, 5):
        resume.cell(resume.max_row, c).font = Font(bold=True)
        if c > 1:
            resume.cell(resume.max_row, c).number_format = MONEY
    resume.append([])
    header_row(resume, ["Despesas por categoria", "Total (R$)", "% das despesas"])
    for k, v in sorted(by_cat_year.items(), key=lambda x: -x[1]):
        resume.append([LABELS.get(k, k), -v, v / t["expense"] if t["expense"] else 0])
        resume.cell(resume.max_row, 2).number_format = MONEY
        resume.cell(resume.max_row, 3).number_format = "0.0%"
    for col, w in zip("ABCD", (24, 16, 16, 16)):
        resume.column_dimensions[col].width = w
    return xlsx_response(wb, f"finance-nunes-{year}.xlsx")


# ---------- assistant ----------
def brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def finance_context(user: User) -> str:
    lines = []
    month = this_month()
    for i in range(11, -1, -1):
        m = shift_month(month, -i)
        items = await month_items(user.id, m)
        if not items:
            continue
        t = totals(items)
        cats = ", ".join(f"{LABELS.get(k, k)} {brl(v)}" for k, v in sorted(t["by_category"].items(), key=lambda x: -x[1]))
        lines.append(f"- {m}: receitas {brl(t['income'])}, despesas {brl(t['expense'])}, saldo {brl(t['balance'])}. Despesas por categoria: {cats or 'nenhuma'}")
        for it in items[:40]:
            tag = " (recorrente)" if it.get("recurring") else (f" (parcela {it['installment_no']}/{it['installment_total']})" if it.get("installment_no") else "")
            lines.append(f"    · {it['date']} {'+' if it['type']=='income' else '-'}{brl(it['amount'])} {LABELS.get(it['category'], it['category'])} {it.get('description','')}{tag}")
    budgets = await db.budgets.find({"user_id": user.id}).to_list(200)
    goals = await db.goals.find({"user_id": user.id}).to_list(100)
    recs = await db.recurring.find({"user_id": user.id}).to_list(100)
    lines.append("Orçamentos mensais: " + (", ".join(f"{LABELS.get(b['category'])} {brl(b['limit'])}" + (f" (só em {b['month']})" if b.get("month") else " (padrão)") for b in budgets) or "nenhum"))
    lines.append("Metas: " + (", ".join(f"{g['name']} {brl(g.get('saved',0))} de {brl(g['target'])}" + (f" até {g['deadline']}" if g.get("deadline") else "") for g in goals) or "nenhuma"))
    lines.append("Recorrentes: " + (", ".join(f"{r['name']} {brl(r['amount'])} dia {r['day']}" for r in recs) or "nenhuma"))
    return "\n".join(lines) if lines else "Nenhum dado registrado ainda."


@api.get("/chat/history")
async def chat_history(user: User = Depends(current_user)):
    docs = await db.chat_messages.find({"user_id": user.id}).sort("created_at", 1).to_list(200)
    return [ChatMessage.from_mongo(d).model_dump() for d in docs]


@api.delete("/chat/history")
async def clear_chat(user: User = Depends(current_user)):
    await db.chat_messages.delete_many({"user_id": user.id})
    return {"ok": True}


@api.post("/chat")
async def chat(body: ChatIn, user: User = Depends(current_user)):
    ctx = await finance_context(user)
    prev = await db.chat_messages.find({"user_id": user.id}).sort("created_at", -1).to_list(10)
    convo = "\n".join(f"{'Usuário' if m['role']=='user' else 'Assistente'}: {m['content']}" for m in reversed(prev))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    system = (
        f"Você é o assistente financeiro do app Finance Nunes, ajudando {user.name or 'o usuário'}. Hoje é {today}. "
        "Responda sempre em português do Brasil, de forma curta, clara e amigável, com valores em reais (R$). "
        "Use somente os dados abaixo para falar dos gastos; se algo não estiver nos dados, diga isso. "
        "Pode dar dicas práticas de organização financeira. Use markdown leve (negrito e listas curtas).\n\n"
        f"DADOS FINANCEIROS (últimos 12 meses):\n{ctx}\n\nCONVERSA ANTERIOR:\n{convo or '(nenhuma)'}"
    )
    await db.chat_messages.insert_one(ChatMessage(user_id=user.id, role="user", content=body.message).to_mongo())
    llm = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"fn-{user.id}-{uuid.uuid4()}", system_message=system).with_model("anthropic", "claude-sonnet-5-5")

    async def gen():
        full = ""
        try:
            async for ev in llm.stream_message(UserMessage(text=body.message)):
                if isinstance(ev, TextDelta):
                    full += ev.content
                    yield f"data: {json.dumps({'delta': ev.content})}\n\n"
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.exception("chat error")
            yield f"data: {json.dumps({'error': 'Não consegui responder agora. Tente de novo em instantes.'})}\n\n"
        if full:
            await db.chat_messages.insert_one(ChatMessage(user_id=user.id, role="assistant", content=full).to_mongo())
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@api.get("/")
async def root():
    return {"app": "Finance Nunes"}


app.include_router(api)
app.include_router(create_files_router(db, current_user))
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ["FRONTEND_URL"], "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_storage():
    await db.files.create_index("id", unique=True)
    await db.files.create_index([("user_id", 1), ("is_deleted", 1), ("created_at", -1)])
    try:
        await storage.initialize()
        logger.info("Private file storage initialized")
    except HTTPException:
        logger.warning("Private file storage unavailable; file requests will retry initialization")


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.transactions.create_index([("user_id", 1), ("date", -1)])
    for name, info in (await db.budgets.index_information()).items():
        if info["key"] == [("user_id", 1), ("category", 1)]:
            await db.budgets.drop_index(name)
    await db.budgets.update_many({"month": {"$exists": False}}, {"$set": {"month": None}})
    await db.budgets.create_index([("user_id", 1), ("category", 1), ("month", 1)], unique=True)
    email = os.environ["ADMIN_EMAIL"].lower()
    if not await db.users.find_one({"email": email}):
        await db.users.insert_one({"email": email, "password_hash": hash_password(os.environ["ADMIN_PASSWORD"]), "name": "Rian Nunes",
                                   "role": "admin", "created_at": datetime.now(timezone.utc).isoformat()})


@app.on_event("shutdown")
async def shutdown():
    await storage.close()
    client.close()
