
# LifeMirror — AI Perception Engine

LifeMirror is an AI system that analyzes a user's appearance, media, and online presence to generate socially intelligent perception insights. It breaks down perception across signals such as fashion, face, posture, vibe, strengths, weaknesses, and fix-it suggestions.

This repository contains the backend services, analysis pipeline, media ingestion, and agent orchestration for LifeMirror. Frontend/UI is intentionally out of scope for this phase.

---

## 🚀 Features

- Media ingestion via presigned URLs
- Vision tools (face, fashion, posture)
- Embedding + similarity search (pgvector)
- Multi-agent perception pipeline (LangGraph)
- Fix-it & improvement suggestions
- Analysis history + notifications
- Auth + consent + privacy controls
- Background processing with Celery
- MinIO object storage

---

## 🧱 High-Level Architecture

- **API:** FastAPI
- **Orchestration:** LangGraph
- **Models:** Vision + Embeddings + LLMs
- **Database:** Postgres + pgvector
- **Object Storage:** MinIO
- **Workers:** Celery + Redis

---

## 📂 Repository Structure



````
src/
├─ api/           # HTTP routes (auth, media, perception, fixit, history)
├─ agents/        # Face, Fashion, Fixit, Orchestrator, etc.
├─ tools/         # YOLO, Face tool, Posture tool, Embed tool
├─ db/            # Models, sessions, migrations
├─ workers/       # Celery tasks for analysis pipeline
├─ services/      # Storage + perception helpers
├─ utils/         # Validation, tracing, mocks, logging

````



---

## 📍 Current Status

Mid implementation stage.

Completed:

✓ Media ingestion & storage
✓ Vision tools (face, fashion, posture)
✓ Bio / Vibe agent
✓ Embeddings pipeline
✓ Orchestrator (LangGraph)
✓  history
✓ Auth + consent system
✓ Celery background workers

In progress:

* Aggregator + Formatter agent
* Notifications
* Guardrails I/O validation
* DSpy prompt optimization
* Eval suite + tracing
* Deployment manifests (k8s)
* Mobile app integration



---


## 📢 Connect with Me  
<div align="center">
    <a href="https://www.linkedin.com/in/rayyanmerchant2004/" target="_blank">
        <img src="https://img.shields.io/badge/LinkedIn-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"/>
    </a>
    <a href="mailto:merchantrayyan43@gmail.com" target="_blank">
        <img src="https://img.shields.io/badge/Email-%23D14836.svg?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"/>
    </a>
    <a href="https://github.com/rayyan-merchant" target="_blank">
        <img src="https://img.shields.io/badge/GitHub-%23181717.svg?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/>
    </a>
</div>
