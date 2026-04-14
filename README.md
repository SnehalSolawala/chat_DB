link : https://chatsql-latest.onrender.com

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

