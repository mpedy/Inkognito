PY=python
UV=uvicorn
UVFLAGS=--host 0.0.0.0 --port 8000

run:
	$(UV) server:app $(UVFLAGS)

check:
	ruff check