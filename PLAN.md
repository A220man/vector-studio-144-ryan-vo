# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

continue-implementation

## Roadmap

### continue-implementation — Continue implementation and resolve known failures

Status: done

Acceptance:
- Run checks, fix failures, and implement the next planned feature

Implementation: `backend/app/api/health.py`, `backend/app/core/config.py`

Tests: `backend/tests/test_health.py`, `frontend/src/App.test.tsx`

### feature-routines — Routine CRUD API

Status: planned

Acceptance:
- Create, read, update, delete routines with phases

Implementation: `backend/app/api/routines.py`

Tests: `backend/tests/test_routines.py`

### feature-workouts — Workout session logging API

Status: planned

Acceptance:
- Start workout, log entries/sets, complete workout

Implementation: `backend/app/api/workouts.py`

Tests: `backend/tests/test_workouts.py`

### feature-exercises — Exercise catalogue API

Status: planned

Acceptance:
- Search exercises with muscle/equipment filters

Implementation: `backend/app/api/exercises.py`

Tests: `backend/tests/test_exercises.py`

### feature-import-export — Import from FitNotes/Strong/Hevy

Status: planned

Acceptance:
- CSV/JSON import creates routines and workouts

Implementation: `backend/app/services/import_export.py`

Tests: `backend/tests/test_import.py`

### feature-ai-coach — Optional AI routine generation

Status: planned

Acceptance:
- Provider-agnostic LLM calls for routine generation/adjustment

Implementation: `backend/app/services/ai_coach.py`

Tests: `backend/tests/test_ai_coach.py`

