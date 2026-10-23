# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-23

### Added
- Initial project skeleton with FastAPI backend and React frontend
- SQLite database with SQLAlchemy models for users, routines, exercises, workouts
- Health check endpoints (`/api/health`, `/api/health/db`)
- Dockerfiles for backend and frontend
- Docker Compose with Keycloak OIDC integration
- GitHub Actions CI workflow (backend tests, frontend typecheck/build/test, Docker builds)
- Keycloak realm export with passkey/WebAuthn support
- README with install/run/test instructions
- MIT License

### Security
- Non-root Docker users
- HttpOnly cookie-ready auth architecture
- PKCE for SPA authentication
- Environment-based configuration

## [Unreleased]

### Planned
- Routine CRUD API and UI
- Workout session logging with sets/reps/weight
- Exercise catalogue with muscle mapping
- Import from FitNotes/Strong/Hevy
- Muscle fatigue/detraining tracking
- OIDC authentication integration
- Optional AI Coach (LLM-backed)