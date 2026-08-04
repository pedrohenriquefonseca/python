"""Regenera o subset da fonte Tabler Icons com EXATAMENTE os ícones usados no app.

Varre os ícones referenciados nos templates (classes `ti-xxx`) e nos dicionários
CATEGORY_ICONS/ASSET_ICONS de app.py, mapeia cada nome para seu codepoint usando o
CSS completo do Tabler e gera:
  - static/fonts/tabler-icons-subset.woff2  (só os glifos necessários)
  - static/icons.css                        (só as classes necessárias)

Fonte completa (TTF) e CSS completo são baixados sob demanda para /tmp. Rode após
adicionar um ícone novo:  ./venv/bin/python build_icons.py
"""
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
FULL_CSS = Path("/tmp/tabler-full.css")
FULL_TTF = Path("/tmp/tabler-icons.ttf")
CSS_URL = "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.31.0/dist/tabler-icons.min.css"
TTF_URL = "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.31.0/dist/fonts/tabler-icons.ttf"


def ensure(path: Path, url: str):
    if not path.exists() or path.stat().st_size == 0:
        urllib.request.urlretrieve(url, path)


# Ícones cujo nome é montado dinamicamente no template (ex.: ti-trending-{{up/down}}),
# que o regex não consegue capturar inteiro. Liste-os à mão.
DYNAMIC_ICONS = {"trending-up", "trending-down"}


def used_icons() -> set:
    names = set(DYNAMIC_ICONS)
    for tpl in (ROOT / "templates").glob("*.html"):
        names |= set(re.findall(r"ti ti-([a-z0-9-]+)", tpl.read_text()))
    app = (ROOT / "app.py").read_text()
    # valores dos dicionários CATEGORY_ICONS / ASSET_ICONS e defaults
    for block in re.findall(r"_ICONS\s*=\s*\{(.*?)\}", app, re.S):
        names |= set(re.findall(r":\s*\"([a-z0-9-]+)\"", block))
    names |= set(re.findall(r'"ti ti-" \+ \w+\.get\([^,]+,\s*"([a-z0-9-]+)"\)', app))
    return {n for n in names if n}


def codepoints(css_text: str) -> dict:
    return {m.group(1): m.group(2)
            for m in re.finditer(r"\.ti-([a-z0-9-]+):before\{content:\"\\([0-9a-f]+)\"", css_text)}


def main():
    ensure(FULL_CSS, CSS_URL)
    ensure(FULL_TTF, TTF_URL)
    cp = codepoints(FULL_CSS.read_text())
    # descarta prefixos dinâmicos incompletos (ex.: "trending-"), já cobertos por DYNAMIC_ICONS
    names = sorted(n for n in used_icons() if not n.endswith("-"))

    missing = [n for n in names if n not in cp]
    if missing:
        print("AVISO: ícones sem codepoint no Tabler (verifique o nome):", missing)

    chosen = [(n, cp[n]) for n in names if n in cp]
    unicodes = ",".join("U+" + c.upper() for _, c in chosen)

    out_woff2 = ROOT / "static/fonts/tabler-icons-subset.woff2"
    subprocess.run([
        sys.executable, "-m", "fontTools.subset", str(FULL_TTF),
        f"--unicodes={unicodes}", "--flavor=woff2",
        f"--output-file={out_woff2}", "--no-layout-closure",
    ], check=True)

    # cache-bust: muda sempre que o conteúdo da fonte muda, evitando o navegador
    # servir glifos antigos do cache quando o subset é regenerado.
    ver = out_woff2.stat().st_size
    css = ['@font-face{font-family:"ti";font-style:normal;font-weight:400;'
           f'src:url("fonts/tabler-icons-subset.woff2?v={ver}") format("woff2")}}',
           '.ti{font-family:"ti"!important;font-style:normal;font-weight:400;font-variant:normal;'
           'text-transform:none;line-height:1;-webkit-font-smoothing:antialiased;'
           '-moz-osx-font-smoothing:grayscale;display:inline-block;vertical-align:-.125em}']
    for n, c in chosen:
        css.append(f'.ti-{n}:before{{content:"\\{c}"}}')
    (ROOT / "static/icons.css").write_text("\n".join(css) + "\n")

    print(f"OK: {len(chosen)} ícones no subset ({out_woff2.stat().st_size} bytes).")


if __name__ == "__main__":
    main()
