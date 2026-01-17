import json
from pathlib import Path

META_JS = Path("static/dist/meta.json")
META_CSS = Path("static/dist/meta_css.json")

MANIFEST = Path("static/dist/manifest.json")

def main():
    meta_js = json.loads(META_JS.read_text(encoding="utf-8"))
    meta_css = json.loads(META_CSS.read_text(encoding="utf-8"))

    # Trova l'output JS principale generato da esbuild
    # meta["outputs"] ha chiavi tipo "static/app.<hash>.js"
    outputs_js = list(meta_js.get("outputs", {}).keys())
    outputs_css = list(meta_css.get("outputs", {}).keys())

    js_outputs = [o for o in outputs_js if o.endswith(".js") and "/app." in o.replace("\\", "/")]
    if not js_outputs:
        raise SystemExit("Non trovo l'output app.<hash>.js in meta.json")
    
    css_outputs = [o for o in outputs_css if o.endswith(".css") and "/style." in o.replace("\\", "/")]
    if not css_outputs:
        raise SystemExit("Non trovo l'output style.<hash>.css in meta_css.json")

    # Se per qualche motivo ce ne sono più di uno, prendiamo il primo (di solito è uno solo)
    app_js = js_outputs[0]
    style_css = css_outputs[0]

    # Salviamo un manifest semplice con path relativo a /static
    # static/app.X.js -> app.X.js
    rel_js = app_js.replace("\\", "/")
    if rel_js.startswith("static/"):
        rel_js = rel_js[len("static/"):]

    rel_css = style_css.replace("\\", "/")
    if rel_css.startswith("static/"):
        rel_css = rel_css[len("static/"):]

    manifest = {
        "app": rel_js,
        "style": rel_css
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Wrote", MANIFEST, "->", manifest)

if __name__ == "__main__":
    main()
