import json
from pathlib import Path

META = Path("static/dist/meta.json")
MANIFEST = Path("static/dist/manifest.json")

def main():
    meta = json.loads(META.read_text(encoding="utf-8"))

    # Trova l'output JS principale generato da esbuild
    # meta["outputs"] ha chiavi tipo "static/app.<hash>.js"
    outputs = list(meta.get("outputs", {}).keys())

    js_outputs = [o for o in outputs if o.endswith(".js") and "/app." in o.replace("\\", "/")]
    if not js_outputs:
        raise SystemExit("Non trovo l'output app.<hash>.js in meta.json")

    # Se per qualche motivo ce ne sono più di uno, prendiamo il primo (di solito è uno solo)
    app_js = js_outputs[0]

    # Salviamo un manifest semplice con path relativo a /static
    # static/app.X.js -> app.X.js
    rel = app_js.replace("\\", "/")
    if rel.startswith("static/"):
        rel = rel[len("static/"):]

    manifest = {
        "app": rel
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Wrote", MANIFEST, "->", manifest)

if __name__ == "__main__":
    main()
