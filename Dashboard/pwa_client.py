"""
Cliente PWA — versão definitiva que extrai TUDO via expand na lista /Projects.

Descobertas-chave:
- /_api/ProjectServer/Projects(id)/Tasks → 404 (bloqueio de permissão)
- /_api/ProjectServer/Projects?$filter=Id eq guid'...'&$expand=Tasks → 200 (FUNCIONA!)
- Lookup CF values: via $expand=Draft/IncludeCustomFields, propriedades Custom_x005f_<cf_id>
- Não-lookup CF values: idem, mas retorna valor direto (não wrapped em Entry_)

Autenticação: MSAL device flow (OAuth2 + AllSites.Read), suporta MFA.
"""

import logging
import os
import re
import threading
from urllib.parse import urlencode
from datetime import datetime, timezone

import msal
import requests

# ── Configuração ──────────────────────────────────────────────────────────────
PWA_URL    = "https://horizontesarq.sharepoint.com/sites/pwa"
SP_HOST    = "https://horizontesarq.sharepoint.com"
PS_BASE    = f"{PWA_URL}/_api/ProjectServer"
PDATA_BASE = f"{PWA_URL}/_api/ProjectData"

CLIENT_ID  = "23bdfa12-e9f6-4759-90bf-e6d65bd5fd09"
TENANT_ID  = "c4cae996-6b0f-4e97-86b8-3f59107fe51c"
AUTHORITY  = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES     = ["https://horizontesarq.sharepoint.com/AllSites.Read"]
CACHE_FILE = os.path.join(os.path.dirname(__file__), ".token_cache.json")

# ── Mapeamento de Custom Fields (Project entity) ──────────────────────────────
# IDs descobertos via /CustomFields endpoint
CF_PROJECT = {
    "Cidade":       "bf41a3bd-bbd1-ee11-8cb9-00155de49236",
    "Cliente":      "4bb21a18-69e1-ee11-b3a1-00155de44340",
    "Coordenador":  "58ddf97d-9bd4-ee11-a15a-00155de04e43",
    "Numero":       "0e73e9fa-58d2-ee11-bc6b-00155de08238",
    "Status":       "d51e0c2e-42d2-ee11-ab3a-00155de43a39",
    "TipoProjeto":  "02ecf97c-26e2-ee11-9730-00155de09043",
}

logger = logging.getLogger(__name__)

_session: requests.Session | None = None
_pending_flow: dict | None = None
_pending_app: msal.PublicClientApplication | None = None
_flow_lock = threading.Lock()
_lookup_cache: dict[str, str] = {}  # entry_id (sem hifens) → FullValue


# ── Cache de token ────────────────────────────────────────────────────────────

def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache


def _save_cache(cache: msal.SerializableTokenCache):
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def _make_app(cache: msal.SerializableTokenCache) -> msal.PublicClientApplication:
    return msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)


# ── Autenticação MSAL (device flow) ──────────────────────────────────────────

def get_token_silent() -> str | None:
    cache = _load_cache()
    app = _make_app(cache)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(cache)
            return result["access_token"]
    return None


def start_device_flow() -> dict:
    global _pending_flow, _pending_app
    with _flow_lock:
        cache = _load_cache()
        app = _make_app(cache)
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Falha ao iniciar device flow: {flow.get('error_description')}")
        _pending_flow = flow
        _pending_app  = app
        logger.info("Device flow iniciado — código: %s", flow["user_code"])
        return {
            "verification_uri": flow["verification_uri"],
            "user_code":        flow["user_code"],
            "expires_in":       flow.get("expires_in", 900),
        }


def poll_device_flow() -> str | None:
    global _pending_flow, _pending_app, _session
    with _flow_lock:
        if not _pending_flow or not _pending_app:
            return None
        result = _pending_app.acquire_token_by_device_flow(
            _pending_flow,
            exit_condition=lambda flow: True,
        )
        if "access_token" in result:
            _save_cache(_pending_app.token_cache)
            _pending_flow = None
            _pending_app  = None
            _session = None
            logger.info("Autenticado com sucesso via device flow.")
            return result["access_token"]
        err = result.get("error")
        if err and err not in ("authorization_pending", "slow_down"):
            _pending_flow = None
            _pending_app  = None
            raise RuntimeError(result.get("error_description", err))
        return None


def is_authenticated() -> bool:
    return get_token_silent() is not None


# ── Sessão HTTP ───────────────────────────────────────────────────────────────

def _build_session() -> requests.Session:
    token = get_token_silent()
    if not token:
        raise RuntimeError("Não autenticado.")
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/json;odata=verbose",
        "Content-Type": "application/json;odata=verbose",
    })
    return session


def get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = _build_session()
    return _session


def reset_session():
    global _session
    _session = None


def logout():
    global _session, _pending_flow, _pending_app, _lookup_cache
    _session = _pending_flow = _pending_app = None
    _lookup_cache = {}
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = 90) -> dict:
    resp = get_session().get(url, timeout=timeout)
    if resp.status_code == 401:
        logger.warning("Token expirado, reconstruindo sessão...")
        reset_session()
        resp = get_session().get(url, timeout=timeout)
    if not resp.ok:
        logger.error("HTTP %s — %s", resp.status_code, resp.text[:400])
        resp.raise_for_status()
    return resp.json()


def _get_all(base_url: str, params: dict | None = None) -> list:
    """Busca todos os registros com paginação automática."""
    qs  = ("?" + urlencode(params, safe="$,()'")) if params else ""
    url = f"{base_url}{qs}"
    results = []
    while url:
        data = _get(url)
        d    = data.get("d") or {}
        page = d.get("results")
        if page is None:
            page = data.get("value") or []
        results.extend(page)
        url = d.get("__next") or data.get("@odata.nextLink")
    return results


# ── Conversão de datas e durações ────────────────────────────────────────────

_DATE_RE = re.compile(r"/Date\((-?\d+)(?:[+-]\d+)?\)/")
_EMPTY_DATES = {"0001-01-01T00:00:00", "0001-01-01T00:00:00Z", None, ""}


def _parse_date(raw) -> str | None:
    if raw in _EMPTY_DATES or not raw:
        return None
    if str(raw).startswith("0001-01-01"):
        return None
    m = _DATE_RE.search(str(raw))
    if m:
        ms = int(m.group(1))
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return str(raw)[:10]


def _parse_duration_ms(raw_ms) -> int | None:
    """Converte DurationMilliseconds em dias úteis (480 min/dia)."""
    try:
        ms = int(raw_ms)
        if ms <= 0:
            return 0
        # 480 min/dia = 480*60*1000 ms
        return round(ms / (480 * 60 * 1000))
    except (ValueError, TypeError):
        return None


def _calendar_days(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        return max(0, (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days + 1)
    except Exception:
        return None


def _pct_previsto(start: str | None, end: str | None, ref_date: datetime | None = None) -> int:
    """Calcula % Previsto: tempo decorrido / tempo total * 100."""
    if not start or not end:
        return 0
    try:
        ref = ref_date or datetime.now()
        d_start = datetime.strptime(start, "%Y-%m-%d")
        d_end   = datetime.strptime(end,   "%Y-%m-%d")
        if ref <= d_start:
            return 0
        if ref >= d_end:
            return 100
        total    = (d_end   - d_start).days or 1
        elapsed  = (ref     - d_start).days
        return max(0, min(100, round(elapsed / total * 100)))
    except Exception:
        return 0


# ── Lookup table cache ───────────────────────────────────────────────────────

def _build_lookup_cache() -> dict[str, str]:
    """Constrói cache global de entry_id (sem hifens) → FullValue."""
    global _lookup_cache
    if _lookup_cache:
        return _lookup_cache

    logger.info("Construindo cache de lookup entries...")
    lts = _get_all(f"{PS_BASE}/LookupTables", {"$select": "Id,Name", "$expand": "Entries"})
    for lt in lts:
        for e in lt.get("Entries", {}).get("results", []):
            eid_clean = e["Id"].replace("-", "")
            _lookup_cache[eid_clean] = e.get("FullValue", "")

    logger.info("  %d entries em cache.", len(_lookup_cache))
    return _lookup_cache


def _resolve_lookup_entry(entry_internal: str) -> str:
    """Converte 'Entry_xxxxx' (32 chars) em FullValue legível."""
    cache = _build_lookup_cache()
    if entry_internal.startswith("Entry_"):
        eid = entry_internal[6:]
        return cache.get(eid, entry_internal)
    return entry_internal


# ── Extração de custom field value (lookup ou scalar) ────────────────────────

def _cf_key(cf_id: str) -> str:
    """ID com hifens → chave 'Custom_x005f_<id_sem_hifens>' usada nos campos."""
    return f"Custom_x005f_{cf_id.replace('-', '')}"


def _extract_cf_value(custom_fields_dict: dict, cf_id: str) -> str:
    """Extrai valor de um CF dado o IncludeCustomFields dict."""
    raw = custom_fields_dict.get(_cf_key(cf_id))
    if raw is None:
        return ""
    # Lookup multi-value: {"results": ["Entry_..."]}
    if isinstance(raw, dict):
        entries = raw.get("results", [])
        return ", ".join(_resolve_lookup_entry(e) for e in entries)
    # Numero/scalar (string com número)
    if isinstance(raw, str) and "." in raw:
        try:
            n = float(raw)
            return str(int(n)) if n == int(n) else str(n)
        except Exception:
            return raw
    return str(raw)


# ── fetch_projects ────────────────────────────────────────────────────────────

def _fetch_batch(batch_ids: list[str]) -> list[dict]:
    """Busca um batch de projetos com tudo necessário (expand limitado a 20)."""
    filter_clauses = " or ".join(f"Id eq guid'{pid}'" for pid in batch_ids)
    url = (
        f"{PS_BASE}/Projects"
        f"?$filter={filter_clauses}"
        f"&$expand=ProjectSummaryTask,Draft/IncludeCustomFields"
        f"&$select=Id,Name,StartDate,FinishDate,LastPublishedDate,"
        f"ProjectSummaryTask/Start,ProjectSummaryTask/Finish,"
        f"ProjectSummaryTask/BaselineStart,ProjectSummaryTask/BaselineFinish,"
        f"ProjectSummaryTask/PercentComplete,"
        f"Draft/IncludeCustomFields"
    )
    try:
        r = _get(url)
        return r.get("d", {}).get("results", [])
    except Exception as e:
        logger.error("Batch falhou: %s", e)
        return []


def fetch_projects() -> list[dict]:
    """
    Retorna projetos com APENAS as 7 dimensões pedidas:
    Nome, Cliente, Número Horizontes, Coordenador, Cidade, %Concluída, %Previsto.

    Batches paralelos de 15 projetos (expand limitado a 20 pelo servidor).
    """
    from concurrent.futures import ThreadPoolExecutor

    logger.info("Buscando projetos no PWA...")
    _build_lookup_cache()

    # 1) Lista IDs (sem expand — sem limite)
    ids_raw = _get_all(f"{PS_BASE}/Projects", {"$top": "500", "$select": "Id"})
    all_ids = [p["Id"] for p in ids_raw]
    logger.info("  %d projeto(s) total.", len(all_ids))

    # 2) Batches paralelos
    BATCH = 15
    batches = [all_ids[i:i+BATCH] for i in range(0, len(all_ids), BATCH)]
    raw_projects: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for page in pool.map(_fetch_batch, batches):
            raw_projects.extend(page)
    logger.info("  %d projeto(s) carregados.", len(raw_projects))

    # 3) Monta lista com todos os campos necessários para o dashboard
    projects = []
    for p in raw_projects:
        draft = p.get("Draft") or {}
        cfs   = draft.get("IncludeCustomFields", {}) if isinstance(draft, dict) else {}

        st = p.get("ProjectSummaryTask") or {}

        # Datas de baseline (o que foi planejado originalmente)
        bl_start = _parse_date(st.get("BaselineStart"))
        bl_end   = _parse_date(st.get("BaselineFinish"))

        # Datas correntes (Start/Finish do PST refletem reprogramações;
        # ActualStart/Finish só são preenchidos quando o projeto é encerrado formalmente)
        ac_start = (_parse_date(st.get("Start"))
                    or _parse_date(p.get("StartDate")))
        ac_end   = (_parse_date(st.get("Finish"))
                    or _parse_date(p.get("FinishDate")))

        # Para % Previsto: usa baseline se disponível, senão datas correntes
        ref_start = bl_start or ac_start
        ref_end   = bl_end   or ac_end

        cliente     = _extract_cf_value(cfs, CF_PROJECT["Cliente"])     or "—"
        cidade      = _extract_cf_value(cfs, CF_PROJECT["Cidade"])      or "—"
        coordenador = _extract_cf_value(cfs, CF_PROJECT["Coordenador"]) or "—"
        numero      = _extract_cf_value(cfs, CF_PROJECT["Numero"])      or ""
        # PercentComplete correto vem do ProjectSummaryTask, não do Project
        pct_conc    = st.get("PercentComplete") or 0
        pct_prev    = _pct_previsto(ref_start, ref_end)

        # Duração planejada (baseline) e real em dias corridos
        plan_days = _calendar_days(bl_start or ac_start, bl_end or ac_end)
        real_days = _calendar_days(ac_start, ac_end)

        # Variância: dias corridos a mais (positivo = atraso)
        variance = 0
        if plan_days and real_days:
            variance = max(0, real_days - plan_days)

        # Aderência ao planejamento
        _today        = datetime.now().date()
        _bl_end_date  = (datetime.strptime(bl_end, "%Y-%m-%d").date() if bl_end else None)
        _past_bl      = _bl_end_date and _today > _bl_end_date and pct_conc < 100

        if _past_bl and plan_days and real_days:
            # Projeto passou a data da baseline sem concluir:
            # penaliza pela extensão de prazo (plan_days / real_days)
            schedule_adh = round(plan_days / real_days * 100)
            adh = max(0, min(int(pct_conc), schedule_adh))
        else:
            gap = max(0, pct_prev - pct_conc)
            adh = max(0, 100 - gap)

        # Status baseado na aderência final (consistente com thresholds do frontend)
        if adh >= 95:
            status = "ok"
        elif adh >= 80:
            status = "warning"
        else:
            status = "late"

        last_pub_raw = p.get("LastPublishedDate") or ""
        last_pub = _parse_date(last_pub_raw) if last_pub_raw else None

        projects.append({
            # Campos canônicos (pt-BR)
            "id":           p.get("Id"),
            "name":         p.get("Name", ""),
            "ultimaPublicacao": last_pub,
            "cliente":      cliente,
            "numero":       numero,
            "coordenador":  coordenador,
            "cidade":       cidade,
            "pctConcluido": pct_conc,
            "pctPrevisto":  pct_prev,
            # Campos de datas (baseline e real)
            "blStart":      bl_start,
            "blEnd":        bl_end,
            "acStart":      ac_start,
            "acEnd":        ac_end,
            # Métricas de desempenho
            "planDays":     plan_days,
            "realDays":     real_days,
            "variance":     variance,
            "adh":          adh,
            "status":       status,
            # Aliases para compatibilidade com index.html
            "client":       cliente,
            "city":         cidade,
            "pct":          pct_conc,
        })

    return projects


# ── fetch_tasks ───────────────────────────────────────────────────────────────

def fetch_tasks(project_id: str) -> list[dict]:
    """
    Retorna tarefas do projeto com APENAS as 9 dimensões pedidas:
    Nome, Nomes dos Recursos, Duração, Dias Corridos, Início, Início BL,
    Término, Término BL, Nível Outline.
    """
    logger.info("Buscando tarefas do projeto %s...", project_id)

    url = (
        f"{PS_BASE}/Projects"
        f"?$filter=Id eq guid'{project_id}'"
        f"&$expand=Tasks,Tasks/Assignments,Tasks/Assignments/Resource,ProjectSummaryTask"
    )
    r = _get(url)
    items = r.get("d", {}).get("results", [])
    if not items:
        return []

    raw_tasks = items[0].get("Tasks", {}).get("results", [])

    tasks = []

    # A tarefa-resumo do projeto (Nível de Estrutura de Tópicos = 0) NÃO vem
    # dentro da coleção "Tasks" (esta começa em OutlineLevel = 1). Ela é uma
    # sub-entidade própria, "ProjectSummaryTask", e precisa ser injetada
    # manualmente como a primeira linha (level 0) do Gantt.
    pst = items[0].get("ProjectSummaryTask") or {}
    if pst:
        p_start    = _parse_date(pst.get("Start"))
        p_end      = _parse_date(pst.get("Finish"))
        p_bl_start = _parse_date(pst.get("BaselineStart"))
        p_bl_end   = _parse_date(pst.get("BaselineFinish"))
        p_pct      = pst.get("PercentComplete") or 0
        p_days     = _calendar_days(p_start, p_end) or 0
        tasks.append({
            "id":           str(pst.get("Id", "")),
            "name":         pst.get("Name", ""),
            "resources":    "",
            "start":        p_start,
            "end":          p_end,
            "blStart":      p_bl_start,
            "blEnd":        p_bl_end,
            "level":        0,
            "type":         "project",
            "status":       "ok",
            "pct":          p_pct,
            "days":         p_days,
            "critical":     bool(pst.get("IsCritical", False)),
            "duracao":      p_days,
            "diasCorridos": p_days,
            "inicio":       p_start,
            "blInicio":     p_bl_start,
            "termino":      p_end,
            "blTermino":    p_bl_end,
            "outlineLevel": 0,
        })

    for t in raw_tasks:
        # Nomes dos recursos
        assigns = (t.get("Assignments") or {}).get("results", []) if isinstance(t.get("Assignments"), dict) else []
        recursos = ", ".join(
            (a.get("Resource") or {}).get("Name", "")
            for a in assigns if (a.get("Resource") or {}).get("Name")
        )

        start     = _parse_date(t.get("Start"))
        end       = _parse_date(t.get("Finish"))
        bl_start  = _parse_date(t.get("BaselineStart"))
        bl_end    = _parse_date(t.get("BaselineFinish"))
        _ol       = t.get("OutlineLevel")
        level     = _ol if _ol is not None else 1
        pct_conc  = t.get("PercentComplete") or 0

        # Tipo de linha no Gantt
        if level == 0:
            task_type = "project"
        elif level == 1:
            task_type = "summary"
        else:
            task_type = "task"

        # Status da tarefa com base na defasagem de % previsto vs % concluído
        task_pct_prev = _pct_previsto(bl_start or start, bl_end or end)
        gap = max(0, task_pct_prev - pct_conc)
        if gap < 5:
            task_status = "ok"
        elif gap < 20:
            task_status = "warning"
        else:
            task_status = "late"

        days = _calendar_days(start, end) or 0

        tasks.append({
            "id":           str(t.get("Id", "")),
            "name":         t.get("Name", ""),
            "resources":    recursos,
            # Nomes de campo que o Gantt do index.html espera
            "start":        start,
            "end":          end,
            "blStart":      bl_start,
            "blEnd":        bl_end,
            "level":        level,
            "type":         task_type,
            "status":       task_status,
            "pct":          pct_conc,
            "days":         days,
            "critical":     bool(t.get("IsCritical", False)),
            # Aliases pt-BR para compatibilidade
            "duracao":      _parse_duration_ms(t.get("DurationMilliseconds") or 0) or 0,
            "diasCorridos": days,
            "inicio":       start,
            "blInicio":     bl_start,
            "termino":      end,
            "blTermino":    bl_end,
            "outlineLevel": level,
        })

    logger.info("  %d tarefa(s).", len(tasks))
    return tasks
