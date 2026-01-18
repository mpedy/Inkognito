import esbuild from "esbuild";
//import browserslist from "browserslist";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { bundle as lightningBundle/*, browserslistToTargets*/} from "lightningcss";

const OUTDIR = "static/dist";

function ensureDir(dir) {
    fs.mkdirSync(dir, { recursive: true });
}

function cleanOld(patterns, dir = OUTDIR) {
    if (!fs.existsSync(dir)) return;
    const files = fs.readdirSync(dir);
    for (const f of files) {
        if (patterns.some((re) => re.test(f))) {
            fs.unlinkSync(path.join(dir, f));
        }
    }
}

function shortHash(buf) {
    return crypto.createHash("sha256").update(buf).digest("hex").slice(0, 10);
}
//esbuild static/app.js --bundle --minify --sourcemap --target=es2017 --outdir=static/dist --entry-names=app.[hash] --metafile=static/dist/meta.json
async function buildJS() {
    const result = await esbuild.build({
        entryPoints: ["static/app.js"],
        bundle: true,
        minify: true,
        sourcemap: true,
        target: ["es2017"],
        outdir: OUTDIR,
        entryNames: "app.[hash]",
        metafile: true,
        //metafile: "static/dist/meta.json",
        write: true,
    });

    // Trova il file JS generato (app.<hash>.js) dentro result.metafile.outputs
    const outputs = Object.keys(result.metafile.outputs);
    const jsOut = outputs.find((p) => p.replaceAll("\\", "/").match(/static\/dist\/app\..+\.js$/));
    if (!jsOut) throw new Error("JS output app.<hash>.js non trovato");

    // Converti in path relativo a /static
    //const rel = jsOut.replaceAll("\\", "/").replace(/^static\//, "");
    const rel = jsOut;
    return { js: rel };
}

//esbuild static/styles.css --bundle --minify --sourcemap --target=chrome58,firefox57,safari11 --outdir=static/dist --entry-names=style.[hash] --metafile=static/dist/meta_css.json
async function buildCSS() {
    // targets da browserslist ("> 2%, not dead")
    //const targets = browserslistToTargets(browserslist("> 2%, not dead")); // :contentReference[oaicite:3]{index=3}
    const targets = {
        chrome: 58,
        firefox: 57,
        safari: 11,
        edge: 79,
        ios_saf: 11
    };

    // bundle CSS (risolve @import), minify, sourcemap
    const res = await lightningBundle({
        filename: path.resolve("static/styles.css"),
        bundle: true,
        minify: true,
        sourceMap: true,
        targets,
        outdir: OUTDIR,
        entryNames: "style.[hash]",
        metafile: true,
    });

    // res.code è Uint8Array; res.map è Uint8Array (sourcemap)
    const cssCode = Buffer.from(res.code);
    const cssMap = Buffer.from(res.map);

    const h = shortHash(cssCode);
    const cssName = `style.${h}.css`;
    const mapName = `${cssName}.map`;

    fs.writeFileSync(path.join(OUTDIR, cssName), cssCode);
    fs.writeFileSync(path.join(OUTDIR, mapName), cssMap);

    return { css: `static/dist/${cssName}` };
}

async function main() {
    ensureDir(OUTDIR);

    // pulisci vecchi app.* e style.* (solo dentro static/dist)
    cleanOld([
        /^app\..+\.js$/,
        /^app\..+\.js\.map$/,
        /^style\..+\.css$/,
        /^style\..+\.css\.map$/,
        /^manifest\.json$/,
    ]);

    const js = await buildJS();
    const css = await buildCSS();

    const manifest = { ...js, ...css };
    fs.writeFileSync(path.join(OUTDIR, "manifest.json"), JSON.stringify(manifest, null, 2));

    console.log("Build OK:", manifest);
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
