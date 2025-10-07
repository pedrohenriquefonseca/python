# scraper_cef_etapa2_excel_voltar_cols.py
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import pandas as pd
import re

URL = "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis"
EXCEL_OUT = "resultados_cef.xlsx"

# ===================== utilidades de navegação / frames =====================

def find_frame_with_selector(page, css, timeout_ms=15000, state="attached"):
    page.wait_for_load_state("domcontentloaded")
    elapsed = 0
    step = 500
    while elapsed < timeout_ms:
        for f in page.frames:
            try:
                el = f.query_selector(css)
                if el:
                    try:
                        f.wait_for_selector(css, timeout=1000, state=state)
                        return f
                    except Exception:
                        pass
            except Exception:
                pass
        page.wait_for_timeout(step)
        elapsed += step
    raise RuntimeError(f"Não encontrei frame com seletor: {css}")

def find_frame_with_option(page, option_text_upper, timeout_ms=20000):
    """Retorna o frame que contém um <select> com a opção (texto UPPER) informada."""
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_function(
        """(txt) => {
            const toU = s => (s||'').trim().toUpperCase();
            const mainSel = Array.from(document.querySelectorAll('select'));
            if (mainSel.some(s => Array.from(s.options).some(o => toU(o.textContent)===txt))) return true;
            const ifs = Array.from(document.querySelectorAll('iframe'));
            for (const i of ifs) {
                try {
                    const doc = i.contentDocument;
                    if (!doc) continue;
                    const sels2 = Array.from(doc.querySelectorAll('select'));
                    if (sels2.some(s => Array.from(s.options).some(o => toU(o.textContent)===txt))) return true;
                } catch(e){}
            }
            return false;
        }""",
        arg=option_text_upper,
        timeout=timeout_ms
    )
    for f in page.frames:
        try:
            has = f.evaluate(
                """(txt) => {
                    const toU = s => (s||'').trim().toUpperCase();
                    const sels = Array.from(document.querySelectorAll('select'));
                    return sels.some(s => Array.from(s.options).some(o => toU(o.textContent)===txt));
                }""",
                option_text_upper
            )
            if has:
                return f
        except Exception:
            pass
    return page.main_frame

def find_select_with_option(frame, option_text_upper, timeout_ms=15000):
    frame.wait_for_function(
        """(txt) => {
            const toU = s => (s||'').trim().toUpperCase();
            const sels = Array.from(document.querySelectorAll('select'));
            return sels.some(s => Array.from(s.options).some(o => toU(o.textContent) === txt));
        }""",
        arg=option_text_upper,
        timeout=timeout_ms
    )
    handle = frame.evaluate_handle(
        """(txt) => {
            const toU = s => (s||'').trim().toUpperCase();
            const sels = Array.from(document.querySelectorAll('select'));
            return sels.find(s => Array.from(s.options).some(o => toU(o.textContent) === txt)) || null;
        }""",
        option_text_upper
    )
    if not handle:
        raise RuntimeError(f"Select com a opção '{option_text_upper}' não encontrado.")
    return handle.as_element()

def select_option_by_text_handle(select_el, text_upper):
    """Define a opção pelo texto visível (UPPER) e dispara eventos."""
    return select_el.evaluate(
        """(s, txt) => {
            const toU = t => (t||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().trim();
            const opt = Array.from(s.options).find(o => toU(o.textContent) === txt);
            if (!opt) return false;
            s.value = opt.value;
            s.dispatchEvent(new Event('change', { bubbles: true }));
            s.dispatchEvent(new Event('input', { bubbles: true }));
            (s.blur && s.blur());
            return true;
        }""",
        text_upper
    )

def get_selected_text(select_el):
    return select_el.evaluate(
        """(s) => {
            const i = s.selectedIndex;
            if (i < 0) return "";
            return (s.options[i]?.textContent || "").trim();
        }"""
    )

def mark_all_checkboxes(frame):
    frame.evaluate(
        """() => {
            const cbs = document.querySelectorAll("input[type='checkbox']");
            cbs.forEach(cb => { if (!cb.disabled && !cb.checked) cb.click(); });
        }"""
    )

def click_next(frame):
    btn = frame.query_selector("input[type='submit'][value='Próximo']")
    if btn:
        btn.click()
        return
    try:
        frame.get_by_role("button", name="Próximo").click()
        return
    except Exception:
        pass
    raise RuntimeError("Botão 'Próximo' não encontrado.")

# ===================== coleta de resultados / paginação =====================

def get_result_link_locators(frame):
    """
    Retorna uma lista de locators (não URLs) para os 'links de detalhes' na página.
    Critérios:
      - href contendo "detal" ou "imovel"
      - OU texto 'Detalhes'/'Detalhe'/'Ver'/'Visualizar'
    """
    locs = frame.locator("a[href]").filter(
        has_text=re.compile(r"(Detalhe|Detalhes|Ver|Visualizar)", re.I)
    )
    # se muito estrito, amplia por href
    if locs.count() == 0:
        locs = frame.locator("a[href*='detal'], a[href*='imovel'], a[href*='im\u00F3vel']")
    return locs

def get_pagination_numbers(frame):
    """
    Coleta os números de página (1,2,3,...) como texto e retorna lista ordenada de ints únicos.
    """
    nums = frame.evaluate(
        """() => {
            const out = [];
            const links = Array.from(document.querySelectorAll('a[href]'));
            for (const a of links) {
                const t = (a.textContent||'').trim();
                if (/^\d+$/.test(t)) out.push(parseInt(t,10));
            }
            return Array.from(new Set(out)).sort((a,b)=>a-b);
        }"""
    )
    return nums or [1]

def click_pagination(frame, number_str):
    """
    Clica na paginação pelo número (texto exato). Usa fallback via JS se necessário.
    """
    try:
        frame.get_by_role("link", name=number_str, exact=True).click()
        return
    except Exception:
        pass
    # fallback JS
    frame.evaluate(
        """(txt) => {
            const a = Array.from(document.querySelectorAll('a')).find(x => (x.textContent||'').trim()===txt);
            if (a) a.click();
        }""",
        number_str
    )

def wait_results_list_ready(page):
    """
    Aguarda a lista de resultados estar pronta (heurística: existir pelo menos 1 link de detalhe).
    """
    try:
        frame = find_frame_with_selector(page, "a[href]", timeout_ms=10000)
    except Exception:
        frame = page.main_frame
    # espera por um link que pareça "detalhe"
    frame.wait_for_function(
        """() => {
            const as = Array.from(document.querySelectorAll('a[href]'));
            return as.some(a => /detal|imovel|im\u00F3vel/i.test(a.getAttribute('href')||'') ||
                                /(Detalhe|Detalhes|Ver|Visualizar)/i.test(a.textContent||''));
        }""",
        timeout=15000
    )
    return frame

def wait_detail_ready(page):
    """
    Aguarda a página de detalhe (heurística: existir botão/link Voltar com javascript:Retornar()).
    """
    try:
        frame = find_frame_with_selector(page, "a[href^='javascript:Retornar']", timeout_ms=15000)
        return frame
    except Exception:
        # fallback: procura texto 'Voltar' com href javascript
        for f in page.frames:
            try:
                if f.query_selector("a[href^='javascript:Retornar']") or f.get_by_text("Voltar", exact=True).count():
                    return f
            except Exception:
                pass
    return page.main_frame

def click_voltar(frame):
    """
    Clica no botão/anchor Voltar da página de detalhe.
    """
    a = frame.query_selector("a[href^='javascript:Retornar']")
    if a:
        a.click()
        return
    # fallback por texto
    try:
        frame.get_by_text("Voltar", exact=True).click()
        return
    except Exception:
        pass
    # último recurso: disparar a função se existir
    frame.evaluate(
        """() => { if (typeof Retornar === 'function') Retornar(); }"""
    )

# ===================== parsing da página de detalhes (campos solicitados) =====================

TARGET_COLUMNS = [
    "Nome do Imóvel",
    "Tipo de Imóvel",
    "Área Total",
    "Área Privativa",
    "Quartos",
    "Garagem",
    "Endereço",
    "Descrição",
    "Link do Detalhe",
]

def normalize(s):
    return (s or "").strip()

def upper_no_accents(s):
    if not s:
        return ""
    t = s.upper()
    # normaliza acentos para comparação
    import unicodedata
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return t

def parse_detail_fields(frame, current_url):
    """
    Extrai os campos solicitados da página de detalhes atual (no frame informado).
    Busca:
      - título (h1/h2) como Nome do Imóvel (se fizer sentido)
      - pares label/valor em tabelas e listas (dt/dd)
      - blocos por heurística
    """
    data = {col: "não encontrei essa informação" for col in TARGET_COLUMNS}
    data["Link do Detalhe"] = current_url

    # 1) título como possível "Nome do Imóvel"
    try:
        titulo = frame.evaluate(
            """() => {
                const pick = sel => {
                    const el = document.querySelector(sel);
                    return el ? el.textContent.trim() : "";
                };
                return pick("h1") || pick("h2") || pick(".titulo, .title, .tit");
            }"""
        )
        if titulo:
            data["Nome do Imóvel"] = titulo
    except Exception:
        pass

    # 2) extrair pares label → valor
    try:
        pairs = frame.evaluate(
            """() => {
                const rows = [];
                const getTxt = (n) => (n?.textContent || "").replace(/\s+/g,' ').trim();
                // tabelas
                const tables = Array.from(document.querySelectorAll("table"));
                for (const t of tables) {
                    const trs = Array.from(t.querySelectorAll("tr"));
                    for (const tr of trs) {
                        const ths = Array.from(tr.querySelectorAll("th"));
                        const tds = Array.from(tr.querySelectorAll("td"));
                        if (ths.length === 1 && tds.length === 1) {
                            rows.push([getTxt(ths[0]), getTxt(tds[0])]);
                        } else if (tds.length >= 2 && ths.length === 0) {
                            const k = getTxt(tds[0]); const v = getTxt(tds[1]);
                            if (k && v) rows.push([k, v]);
                        }
                    }
                }
                // listas de definição (dt/dd)
                const dts = Array.from(document.querySelectorAll("dt"));
                for (const dt of dts) {
                    const dd = dt.nextElementSibling;
                    if (dd) rows.push([getTxt(dt), getTxt(dd)]);
                }
                return rows;
            }"""
        )
    except Exception:
        pairs = []

    # 3) varre pairs e preenche colunas alvo por rótulos (com sinônimos)
    for k, v in pairs:
        ku = upper_no_accents(k)
        val = normalize(v)

        if "TIPO" in ku and "IMOVEL" in ku:
            data["Tipo de Imóvel"] = val
        elif "AREA TOTAL" in ku:
            data["Área Total"] = val
        elif ("AREA PRIVATIVA" in ku) or ("AREA UTIL" in ku):
            data["Área Privativa"] = val
        elif ("QUARTO" in ku) or ("DORMITORIO" in ku):
            data["Quartos"] = val
        elif ("GARAGEM" in ku) or ("VAGA" in ku):
            data["Garagem"] = val
        elif ("ENDERECO" in ku) or ("LOGRADOURO" in ku):
            data["Endereço"] = val
        elif ("DESCRICAO" in ku):
            data["Descrição"] = val
        elif ("IMOVEL" in ku) and data["Nome do Imóvel"] == "não encontrei essa informação":
            # às vezes vem "Imóvel:" com o nome
            data["Nome do Imóvel"] = val

    # 4) se descrição não vier em pares, tenta blocos de texto marcados como "descrição"
    if data["Descrição"] == "não encontrei essa informação":
        try:
            desc = frame.evaluate(
                """() => {
                    const trySel = (sel) => {
                        const el = document.querySelector(sel);
                        return el ? el.textContent.trim() : "";
                    };
                    // ids/classes mais comuns
                    return (
                        trySel("#descricao") ||
                        trySel(".descricao") ||
                        trySel("[id*='descri']") ||
                        trySel("[class*='descri']")
                    );
                }"""
            )
            if desc:
                data["Descrição"] = desc
        except Exception:
            pass

    # 5) se endereço não vier, tenta heurística adicional
    if data["Endereço"] == "não encontrei essa informação":
        try:
            addr = frame.evaluate(
                """() => {
                    const txt = (n) => (n?.textContent||'').replace(/\s+/g,' ').trim();
                    // alguma tag com 'Endereço' forte seguido de valor
                    const labels = Array.from(document.querySelectorAll("b,strong"));
                    for (const lb of labels) {
                        const t = txt(lb).toUpperCase();
                        if (t.includes("ENDEREÇO") || t.includes("ENDERECO")) {
                            // valor pode estar no mesmo nó pai
                            const p = lb.parentElement;
                            if (p) {
                                const s = txt(p).replace(/^(ENDEREC[OÓ]:?)/i,'').trim();
                                if (s && s.length > 5) return s;
                            }
                        }
                    }
                    return "";
                }"""
            )
            if addr:
                data["Endereço"] = addr
        except Exception:
            pass

    # 6) normaliza pequenos detalhes de texto
    for key in TARGET_COLUMNS:
        data[key] = normalize(data.get(key, "não encontrei essa informação"))

    return data

# ===================== preenchimento inicial de filtros (Etapa 1/2) =====================

def fill_filters_until_results(page):
    # -------- ETAPA 1 --------
    frame1 = find_frame_with_selector(page, "select", timeout_ms=20000, state="attached")

    estado_sel = find_select_with_option(frame1, "MG", timeout_ms=20000)
    if not select_option_by_text_handle(estado_sel, "MG"):
        raise RuntimeError("Falha ao definir Estado = MG")

    cidade_sel = find_select_with_option(frame1, "BELO HORIZONTE", timeout_ms=20000)
    if not select_option_by_text_handle(cidade_sel, "BELO HORIZONTE"):
        raise RuntimeError("Falha ao definir Cidade = BELO HORIZONTE")

    frame1.wait_for_selector("input[type='checkbox']", timeout=20000, state="attached")
    mark_all_checkboxes(frame1)
    click_next(frame1)

    # -------- ETAPA 2 --------
    frame2 = find_frame_with_option(page, "APARTAMENTO", timeout_ms=25000)

    tipo_sel = find_select_with_option(frame2, "APARTAMENTO", timeout_ms=20000)
    ok = select_option_by_text_handle(tipo_sel, "APARTAMENTO")
    if not ok:
        try:
            if frame2.query_selector("select[name='sltTipoImovel']"):
                frame2.select_option("select[name='sltTipoImovel']", label="Apartamento")
        except Exception:
            pass

    # garantir que permaneça "Apartamento"
    txt = get_selected_text(tipo_sel)
    if txt.strip().upper() != "APARTAMENTO":
        raise RuntimeError("Tipo de Imóvel NÃO ficou como Apartamento.")

    # demais = Indiferente (sem tocar em Tipo/Faixa)
    frame2.evaluate(
        """(tipoEl) => {
            const U = t => (t||"").normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().trim();
            const faixa = document.querySelector("select[name='cmb_faixa_vlr'], #cmb_faixa_vlr");
            const selects = Array.from(document.querySelectorAll('select'));
            for (const s of selects) {
                if (s === tipoEl) continue;
                if (faixa && s === faixa) continue;
                const optIndif = Array.from(s.options).find(o => U(o.textContent) === "INDIFERENTE");
                if (optIndif) {
                    s.value = optIndif.value;
                    s.dispatchEvent(new Event('change',{bubbles:true}));
                    s.dispatchEvent(new Event('input',{bubbles:true}));
                    (s.blur && s.blur());
                }
            }
        }""",
        tipo_sel
    )

    # faixa 200k–400k (value=3)
    if frame2.query_selector("select[name='cmb_faixa_vlr']") or frame2.query_selector("#cmb_faixa_vlr"):
        frame2.select_option("select[name='cmb_faixa_vlr'], #cmb_faixa_vlr", value="3")
    else:
        faixa_sel = find_select_with_option(frame2, "DE R$200.000,01 ATÉ R$400.000,00", timeout_ms=12000)
        select_option_by_text_handle(faixa_sel, "DE R$200.000,01 ATÉ R$400.000,00")

    click_next(frame2)  # vai para a lista de resultados

# ===================== fluxo principal =====================

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # manter visível
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(45000)
        page.set_default_navigation_timeout(45000)

        print("[1] Abrindo página…")
        page.goto(URL, wait_until="domcontentloaded")

        print("[2] Preenchendo filtros e indo para resultados…")
        fill_filters_until_results(page)

        print("[3] Coletando resultados com paginação…")
        resultados = []

        # garantir que a lista está pronta
        frame_list = wait_results_list_ready(page)
        paginas = get_pagination_numbers(frame_list)
        print("   - Páginas detectadas:", paginas)

        # percorre cada página
        for idx_pag, pag in enumerate(paginas, start=1):
            if idx_pag > 1:
                # navegar para a página N
                frame_list = wait_results_list_ready(page)  # revalida frame atual
                click_pagination(frame_list, str(pag))
                frame_list = wait_results_list_ready(page)

            print(f"   > Página {pag}")
            i = 0
            while True:
                frame_list = wait_results_list_ready(page)
                detail_links = get_result_link_locators(frame_list)
                total = detail_links.count()
                if i >= total:
                    break

                print(f"     - Abrindo item {i+1}/{total} …")
                link_i = detail_links.nth(i)
                # abre detalhe
                link_i.scroll_into_view_if_needed()
                link_i.click()

                # aguarda detalhe (botão Voltar/Retornar)
                frame_detail = wait_detail_ready(page)

                # extrai campos
                data = parse_detail_fields(frame_detail, page.url)
                resultados.append(data)

                # voltar pela função da página
                click_voltar(frame_detail)

                # espera voltar à lista
                frame_list = wait_results_list_ready(page)
                # segue para o próximo
                i += 1

        # salva Excel
        if resultados:
            df = pd.DataFrame(resultados, columns=TARGET_COLUMNS)
            df.to_excel(EXCEL_OUT, index=False)
            print(f"\n✔ Excel salvo: {EXCEL_OUT} (linhas: {len(df)})")
        else:
            print("\n⚠ Não foram coletados resultados. Verifique seletores de lista/detalhe.")

        print("\nNavegador permanecerá aberto para inspeção. Feche a janela quando terminar.")
        try:
            page.wait_for_event("close")  # evita TargetClosedError
        except PWTimeout:
            pass

if __name__ == "__main__":
    main()
