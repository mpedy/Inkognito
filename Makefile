PY=python
UV=uvicorn
UVFLAGS=--reload --host 0.0.0.0 --port 8000

run:
	$(UV) server:app $(UVFLAGS)

check:
	ruff check