PY=python
UV=uvicorn
UVFLAGS=--host 0.0.0.0 --port 8000

run: bundle_assets
	$(UV) server:app $(UVFLAGS)

bundle_assets:
	$(PY) tools/clean_dist_folder.py
	npm run build:assets
	$(PY) tools/build_assets.py

check:
	ruff check