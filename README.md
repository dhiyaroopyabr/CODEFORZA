# College CP — Competitive Programming Platform

A Codeforces-like competitive programming platform built with **FastAPI**, **SQLAlchemy**, **PostgreSQL**, and a clean HTML/CSS/JS frontend with **Monaco Editor** for code editing.

## Features

- 🔐 **JWT Authentication** with `user` and `admin` roles
- 🔒 **bcrypt password hashing** via passlib
- 🧑‍💻 **Monaco Editor** (VS Code-style) with C++, C, Python, Java support
- ⚡ **Online Judge** — run & submit code against test cases
- 👥 **Admin Panel** — manage users, change roles, add problems
- 📊 **Dashboard** — problem list, submission history, stats
- 🛡️ Rate limiting on login, CORS locked to localhost

---

## Project Structure

```
college-cp/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          ← FastAPI app, mounts all routers
│   │   ├── database.py      ← SQLAlchemy engine + get_db
│   │   ├── models.py        ← ORM: users, problems, test_cases, submissions
│   │   ├── schemas.py       ← Pydantic v2 schemas
│   │   ├── auth.py          ← bcrypt + JWT utilities
│   │   ├── dependencies.py  ← get_current_user, require_admin
│   │   ├── executor.py      ← sandboxed code runner
│   │   └── routers/
│   │       ├── auth_router.py      ← /api/auth/*
│   │       ├── users_router.py     ← /api/users/*  (admin)
│   │       ├── problems_router.py  ← /api/problems/*
│   │       └── judge_router.py     ← /api/judge/*
│   ├── .env.example
│   ├── .gitignore
│   └── requirements.txt
└── frontend/
    ├── index.html      ← Login
    ├── register.html   ← Registration
    ├── dashboard.html  ← Problem list
    ├── problem.html    ← Problem + Monaco editor
    ├── admin.html      ← Admin panel
    ├── styles.css
    └── app.js
```

---

## Setup

### 1. PostgreSQL — Create the database

```bash
psql -U postgres
CREATE DATABASE college_cp;
\q
```

### 2. Configure environment

```bash
cd backend
cp .env.example .env
```

Edit `.env`:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/college_cp
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run the server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

- **API docs (Swagger)**: http://localhost:8000/api/docs
- **Register**: http://localhost:8000/register.html

---

## Making yourself an admin

All registrations default to `user` role. Promote yourself:

```sql
-- In psql or any PostgreSQL client:
UPDATE users SET role = 'admin' WHERE email = 'your@email.com';
```

Or use the admin panel once you have one admin — it lets you change other users' roles from the UI.

---

## Compiler requirements

The online judge uses system-installed compilers:

| Language | Tool needed   | Install on macOS |
|----------|---------------|------------------|
| Python 3 | `python3`     | Already installed |
| C++ 17   | `g++`         | `xcode-select --install` or `brew install gcc` |
| C        | `gcc`         | Same as above |
| Java     | `javac` + `java` | Install JDK from adoptium.net |

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | — | Register new user |
| POST | `/api/auth/login` | — | Login, get JWT |
| GET  | `/api/auth/me` | User | Current user info |
| GET  | `/api/problems/` | User | List problems |
| POST | `/api/problems/` | Admin | Create problem |
| GET  | `/api/problems/{id}` | User | Problem detail + samples |
| DELETE | `/api/problems/{id}` | Admin | Delete problem |
| POST | `/api/problems/{id}/test-cases` | Admin | Add test case |
| POST | `/api/judge/run` | User | Run code (playground) |
| POST | `/api/judge/submit` | User | Submit to judge |
| GET  | `/api/judge/submissions` | User | My submissions |
| GET  | `/api/users/` | Admin | List all users |
| PUT  | `/api/users/{id}/role` | Admin | Change user role |
| DELETE | `/api/users/{id}` | Admin | Deactivate user |

---

## Security notes

- Passwords hashed with **bcrypt** (never stored plaintext)
- JWT tokens expire in 30 minutes (configurable)
- Hidden test cases **never** sent to the client — only verdicts
- Users can only see their own submissions
- Admin role required for all management operations
- CORS locked to `localhost:8000` in dev
- ⚠️ The code executor runs arbitrary code via subprocess — **do not expose to public internet** without Docker sandboxing

---

## Production checklist

- [ ] Replace `SECRET_KEY` with a strong random 256-bit hex key
- [ ] Set `ACCESS_TOKEN_EXPIRE_MINUTES` appropriately (15–60 min)
- [ ] Update CORS origins to your actual domain
- [ ] Wrap the executor in Docker containers for isolation
- [ ] Add HTTPS (nginx/caddy in front of uvicorn)
- [ ] Use `--workers 4` with gunicorn for production uvicorn
- [ ] Set up Alembic for database migrations
