# Finance Nunes – PRD

## Problem statement
"https://claude.ai/artifact/ApmwTa5r6KPJwrPkz21MSF, veja como foi feito essas modificações e coloque nesse arquivo e melhore o que puder" — rebuild the Claude artifact "Finance Nunes" (Liquid Glass personal finance dashboard) as a real persistent app. (Artifact link required sign-in and uploaded file was empty; built from approved plan.)

## Architecture
- FastAPI + MongoDB (motor), JWT httpOnly cookies (access 15min + refresh 7d), bcrypt, brute-force lockout
- Claude Sonnet 5.5 via Emergent LLM key, SSE streaming chat with stored history
- React + framer-motion + recharts, pt-BR / BRL

## User persona
Rian Nunes – single user tracking monthly personal finances on desktop/mobile.

## Implemented (2026-06)
- Login/register, profile edit
- Dashboard: month switcher, income/expense/balance, category donut (15 categories, 4 groups), 50-30-20 rule, 6-month bar chart, budgets, goals, recent transactions
- Transactions: search/filter, edit/delete with confirm
- Recurring expenses (virtual monthly entries), installment purchases (auto-split across months)
- Budgets (color progress), goals with deposits/withdrawals
- AI assistant answering from user's saved data
- Origin-animated glass modals / mobile bottom sheets, keyboard category picker, reduced motion
- Tested: 44/44 backend, full frontend flow (iteration_1)
- Per-month budget overrides (special limit for a single month, falls back to default) – 2026-06
- Excel export (.xlsx) of the month's transactions with totals – 2026-06 (iteration_2 passed)

## Backlog
- P1: CSV/Excel export, password reset flow, per-month budget overrides
- P2: bank statement import, notifications for due recurring bills, dark/light toggle
