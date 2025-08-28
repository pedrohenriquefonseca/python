# script_cef_tipo_apartamento_v4.py
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis"

# ---------- utilidades ----------
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
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_function(
        """(txt) => {
            const toU = s => (s||'').trim().toUpperCase();
            // main
            const mainSel = Array.from(document.querySelectorAll('select'));
            if (mainSel.some(s => Array.from(s.options).some(o => toU(o.textContent)===txt))) return true;
            // iframes
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

# ---------- fluxo principal ----------
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visível para inspeção
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(45000)
        page.set_default_navigation_timeout(45000)

        print("[1] Abrindo página…")
        page.goto(URL, wait_until="domcontentloaded")

        # -------- ETAPA 1 --------
        print("[2] Encontrando frame da Etapa 1…")
        frame1 = find_frame_with_selector(page, "select", timeout_ms=20000, state="attached")

        print("[3] Estado = MG…")
        estado_sel = find_select_with_option(frame1, "MG", timeout_ms=20000)
        if not select_option_by_text_handle(estado_sel, "MG"):
            raise RuntimeError("Falha ao definir Estado = MG")

        print("[4] Cidade = BELO HORIZONTE…")
        cidade_sel = find_select_with_option(frame1, "BELO HORIZONTE", timeout_ms=20000)
        if not select_option_by_text_handle(cidade_sel, "BELO HORIZONTE"):
            raise RuntimeError("Falha ao definir Cidade = BELO HORIZONTE")

        print("[5] Marcando TODOS os bairros…")
        frame1.wait_for_selector("input[type='checkbox']", timeout=20000, state="attached")
        mark_all_checkboxes(frame1)

        print("[6] Próximo → Etapa 2…")
        click_next(frame1)

        # -------- ETAPA 2 --------
        print("[7] Localizando frame da Etapa 2 (opção 'APARTAMENTO')…")
        frame2 = find_frame_with_option(page, "APARTAMENTO", timeout_ms=25000)

        print("[8] Tipo de Imóvel = Apartamento…")
        tipo_sel = find_select_with_option(frame2, "APARTAMENTO", timeout_ms=20000)
        ok = select_option_by_text_handle(tipo_sel, "APARTAMENTO")
        if not ok:
            try:
                if frame2.query_selector("select[name='sltTipoImovel']"):
                    frame2.select_option("select[name='sltTipoImovel']", label="Apartamento")
                    ok = True
            except Exception:
                pass
        txt = get_selected_text(tipo_sel)
        print(f"    - Valor em 'Tipo' após set: {txt!r}")
        if txt.strip().upper() != "APARTAMENTO":
            raise RuntimeError("Tipo de Imóvel NÃO ficou como Apartamento.")

        print("[9] QUARTOS/VAGAS/ÁREA = INDIFERENTE (sem mexer no 'Tipo' e na 'Faixa')")
        frame2.evaluate(
            """(tipoEl) => {
                const U = t => (t||"").normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().trim();
                const faixa = document.querySelector("select[name='cmb_faixa_vlr'], #cmb_faixa_vlr");
                const selects = Array.from(document.querySelectorAll('select'));
                for (const s of selects) {
                    if (s === tipoEl) continue;        // não tocar no Tipo
                    if (faixa && s === faixa) continue; // não tocar na Faixa
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

        print("[10] Faixa de valor = 200k–400k (value=3)…")
        try:
            if frame2.query_selector("select[name='cmb_faixa_vlr']") or frame2.query_selector("#cmb_faixa_vlr"):
                frame2.select_option("select[name='cmb_faixa_vlr'], #cmb_faixa_vlr", value="3")
            else:
                faixa_sel = find_select_with_option(frame2, "DE R$200.000,01 ATÉ R$400.000,00", timeout_ms=12000)
                select_option_by_text_handle(faixa_sel, "DE R$200.000,01 ATÉ R$400.000,00")
            print("    - Faixa definida.")
        except Exception as e:
            raise RuntimeError(f"Falha ao definir Faixa de valor: {e}")

        print("[11] Reforçando Tipo = Apartamento…")
        select_option_by_text_handle(tipo_sel, "APARTAMENTO")
        txt = get_selected_text(tipo_sel)
        print(f"    - Valor final em 'Tipo': {txt!r}")

        print("[12] Próximo → Resultados…")
        click_next(frame2)

        print("✔ Concluído. Deixe a janela aberta para inspecionar.")
        print(">>> Quando terminar, feche a janela do navegador.")

        # ====== Espera elegante pelo FECHAMENTO, sem erro ======
        # Opção A (recomendada): esperar o fechamento da aba atual
        try:
            page.wait_for_event("close")  # bloqueia até você fechar a janela/aba
        except PWTimeout:
            pass
        # Alternativa:
        # browser.wait_for_event("disconnected")

if __name__ == "__main__":
    main()
