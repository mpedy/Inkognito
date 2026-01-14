PY=python
UV=uvicorn
UVFLAGS=--host 0.0.0.0 --port 8000
SSLKEYFILE?=certs/key.pem
SSLCERTFILE?=certs/cert.pem
UVFLAGS_HTTPS=--host 0.0.0.0 --port 8000 --ssl-keyfile=$(SSLKEYFILE) --ssl-certfile=$(SSLCERTFILE)

run: bundle_assets
	$(UV) server:app $(UVFLAGS)

run-https: bundle_assets
	$(UV) server:app $(UVFLAGS_HTTPS)

bundle_assets:
	$(PY) tools/clean_dist_folder.py
	npm run build:assets
	$(PY) tools/build_assets.py

check:
	ruff check