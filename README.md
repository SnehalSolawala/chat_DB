# 🚀 ChatSQL — Natural Language Database Interface

🔗 **Live Demo:** https://chatsql-latest.onrender.com  

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
