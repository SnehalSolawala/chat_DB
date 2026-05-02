# 🚀 ChatSQL — Natural Language Database Interface

## 🔗 **Live Demo:** https://chatsql-latest.onrender.com  

### you can run on your database which is on server

### for example you can check with my database which i can store on railway

  host="metro.proxy.rlwy.net",
  
  port=49330,
  
  user="root",
  
  password="pBvzCPWbFLgPNopSSfOFrnZZmNpFdrlr",
  
  database="railway"


### if you want to run on your local database then you can take my docker image from https://hub.docker.com/repository/docker/snehalsolawala/chatsql then run on it



ChatSQL — Natural Language Database Interface
Python FastAPI MySQL OpenAI GPT-4 Docker Railway

Built a full-stack AI-powered web app that converts plain English questions into MySQL queries using OpenAI GPT-4o-mini, eliminating the need to write SQL manually
Designed a session-based multi-user architecture with per-session database credentials, supporting concurrent users each connected to their own MySQL instance
Implemented an AI table profiler that analyzes schema, detects data quality issues, identifies semantic column roles (dimension/measure/time/id), and suggests JOIN recommendations
Engineered a cookie-free session system using X-Session-ID headers + sessionStorage to reliably handle reverse proxy deployments (Railway/Heroku)
Containerized with Docker and deployed to Railway with CI/CD via DockerHub
Built REST API with FastAPI exposing MCP-compatible endpoints for profiling and schema discovery


Skills it adds to your resume

Backend: FastAPI, Python, REST API design, session management
AI/LLM: Prompt engineering, OpenAI API, NL-to-SQL, AI agents
Database: MySQL, schema profiling, SQL generation
DevOps: Docker, docker-compose, Railway, DockerHub
Frontend: Vanilla JS, async/await, sessionStorage, fetch API




---

## 📌 Overview

ChatSQL is an AI-powered web application that allows users to interact with databases using **natural language instead of SQL queries**.

It leverages OpenAI GPT-4o-mini to convert plain English questions into executable MySQL queries, making data access simple, fast, and accessible to non-technical users.

---

## ✨ Key Features

- 💬 **Natural Language to SQL (NL-to-SQL)**  
  Ask questions in plain English and get SQL queries + results instantly.

- 🧠 **AI Table Profiler**  
  - Detects data quality issues  
  - Identifies column roles (dimension, measure, time, ID)  
  - Suggests JOIN relationships  

- 🔐 **Session-Based Multi-User Architecture**  
  - Each user connects to their own MySQL database  
  - Supports concurrent users  
  - Secure per-session credentials  

- 🍪 **Cookie-Free Session Handling**  
  - Uses `X-Session-ID` headers  
  - Stores session in `sessionStorage`  
  - Works behind reverse proxies (Railway/Heroku)

- ⚡ **FastAPI Backend**  
  - RESTful APIs  
  - MCP-compatible endpoints for schema & profiling  

- 🐳 **Dockerized Deployment**  
  - Docker & Docker Compose  
  - CI/CD via DockerHub  
  - Deployed on Railway  

---


##What was hard to build?

Honestly, two things frustrated me more than I expected.
The first one was the session problem.
So I was testing the app locally and everything worked perfectly. Connect to the database, ask a question, get results. No issues.
Then I deployed it and randomly — not always, but randomly — users were getting this error saying 'no database connected' even though they just connected two seconds ago.
I couldn't reproduce it locally. It took me a while to figure out what was happening.
The issue was I was running two uvicorn workers in production. Each worker is a separate Python process — separate memory. So when a user hits /connect, that request goes to worker one, credentials get stored in worker one's dictionary. Then when they hit /ask, that request goes to worker two — completely different memory — worker two has no idea who this user is.
Once I understood that, the fix was simple — force single worker in Docker. But understanding why it was happening took time. And now I know — in-memory storage and multiple workers don't mix.

The second one was the LLM output problem.
I assumed — naively — that if I ask GPT to return SQL, it just returns SQL. Clean. Ready to run.
It doesn't.
Sometimes it returns this —
Sure! Here is the SQL query for you:
```sql
SELECT * FROM customers LIMIT 5

```
And when you try to execute that string directly against MySQL — it crashes immediately.

So I had to build a cleaning step — strip the markdown fences, strip any explanation text the model adds before or after. Then I realized even after cleaning, sometimes the model would **invent column names** that don't exist in the table. So I started passing the actual schema — column names and types — into the prompt, plus 3 real sample rows, so the model has no excuse to guess.

That combination — schema plus sample rows plus explicit instructions to return raw SQL only — made it reliable enough to actually run in production."

