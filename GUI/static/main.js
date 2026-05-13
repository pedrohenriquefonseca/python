/* ═══════════════════════════════════════════════
   KEEPALIVE  (SSE — server detecta fechamento do browser)
   ═══════════════════════════════════════════════ */
new EventSource('/api/keepalive');

/* ═══════════════════════════════════════════════
   ERRO GLOBAL  (torna qualquer falha visível)
   ═══════════════════════════════════════════════ */
window.addEventListener('error', e => {
  const painel = document.querySelector('.tool-panel.active');
  if (!painel) return;
  const st = painel.querySelector('.status-msg');
  if (st) { st.textContent = `Erro JS: ${e.message} (${e.filename}:${e.lineno})`; st.className = 'status-msg error'; }
});

/* ═══════════════════════════════════════════════
   NAVEGAÇÃO ENTRE FERRAMENTAS
   ═══════════════════════════════════════════════ */
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const tool = link.dataset.tool;

    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');

    document.querySelectorAll('.tool-panel').forEach(p => p.classList.remove('active'));
    document.getElementById(`panel-${tool}`).classList.add('active');
  });
});

/* ═══════════════════════════════════════════════
   ZONA DE ARQUIVO  (clique + drag & drop)
   ═══════════════════════════════════════════════ */
['report', 'desembolso', 'cronograma', 'ferias'].forEach(id => {
  const input = document.getElementById(`file-${id}`);
  const text  = document.getElementById(`file-text-${id}`);
  const zone  = document.getElementById(`zone-${id}`);
  if (!input || !text || !zone) return;

  function setFiles(files) {
    if (!files || files.length === 0) return;
    text.textContent = files.length === 1 ? files[0].name : `${files.length} arquivos selecionados`;
    zone.classList.add('has-file');
  }

  input.addEventListener('change', () => setFiles(input.files));

  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', ()  => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
      const dt = new DataTransfer();
      // Para report (multiple), aceita todos; para os demais, só o primeiro
      const lista = input.multiple ? e.dataTransfer.files : [e.dataTransfer.files[0]];
      Array.from(lista).forEach(f => dt.items.add(f));
      input.files = dt.files;
      setFiles(dt.files);
    }
  });
});

/* ═══════════════════════════════════════════════
   TOGGLE  (Projetos / Equipe)
   ═══════════════════════════════════════════════ */
document.querySelectorAll('.toggle-btn').forEach(btn => {
  btn.addEventListener('click', e => {
    if (e.ctrlKey) {
      // Ctrl+clique: adiciona/remove da seleção, mas mantém ao menos 1 ativo
      const ativos = document.querySelectorAll('.toggle-btn.active');
      if (btn.classList.contains('active') && ativos.length === 1) return;
      btn.classList.toggle('active');
    } else {
      // Clique normal: seleciona apenas este
      document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }
  });
});

/* ═══════════════════════════════════════════════
   UTILITÁRIOS
   ═══════════════════════════════════════════════ */
function setLoading(id, on) {
  const btn = document.getElementById(`btn-${id}`);
  btn.disabled = on;
  btn.querySelector('.btn-text').classList.toggle('hidden', on);
  btn.querySelector('.btn-loading').classList.toggle('hidden', !on);
}

function showStatus(id, msg, isError = false) {
  const el = document.getElementById(`status-${id}`);
  el.textContent = msg;
  el.className = `status-msg ${isError ? 'error' : 'success'}`;
  if (!isError) setTimeout(() => { el.textContent = ''; el.className = 'status-msg'; }, 5000);
}

function downloadBlob(blob, res) {
  const cd  = res.headers.get('Content-Disposition') || '';
  const match = cd.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
  const name = match ? decodeURIComponent(match[1].replace(/['"]/g, '')) : 'download';
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

/* ═══════════════════════════════════════════════
   MODAL
   ═══════════════════════════════════════════════ */
const modal     = document.getElementById('modal');
const modalBody = document.getElementById('modal-body');

document.getElementById('modal-close').addEventListener('click', fecharModal);
modal.addEventListener('click', e => { if (e.target === modal) fecharModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharModal(); });

function mostrarModal(imagens, nomes) {
  modalBody.innerHTML = '';
  imagens.forEach((src, i) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'modal-img-wrap';

    const img = document.createElement('img');
    img.src = `data:image/png;base64,${src}`;

    const btn = document.createElement('button');
    btn.className = 'modal-download';
    btn.textContent = 'Baixar imagem';
    btn.addEventListener('click', () => {
      const a = document.createElement('a');
      a.href = img.src;
      a.download = nomes[i] || `cronograma_${i + 1}.png`;
      a.click();
    });

    wrapper.appendChild(img);
    wrapper.appendChild(btn);
    modalBody.appendChild(wrapper);
  });
  modal.classList.add('visible');
}

function fecharModal() {
  modal.classList.remove('visible');
}

/* ═══════════════════════════════════════════════
   REPORT SEMANAL
   ═══════════════════════════════════════════════ */
document.getElementById('form-report').addEventListener('submit', async e => {
  e.preventDefault();
  const arquivos = Array.from(document.getElementById('file-report').files);
  if (arquivos.length === 0) { showStatus('report', 'Selecione ao menos um arquivo Excel.', true); return; }

  setLoading('report', true);
  const erros = [], relatorios = [];

  for (let i = 0; i < arquivos.length; i++) {
    const arquivo = arquivos[i];
    const nome = arquivo.name.replace(/\.[^/.]+$/, '');
    if (arquivos.length > 1) showStatus('report', `Processando ${i + 1} / ${arquivos.length}…`);
    try {
      const fd = new FormData();
      fd.append('arquivo', arquivo);
      fd.append('nome_projeto', nome);
      const res = await fetch('/api/report', { method: 'POST', body: fd });
      const j   = await res.json();
      if (!res.ok || j.error) throw new Error(j.error);
      relatorios.push({ nome, content: j.content, filename: j.filename });
    } catch (err) {
      erros.push(`${nome}: ${err.message}`);
    }
  }

  setLoading('report', false);

  if (relatorios.length > 0) mostrarRelatorios(relatorios);

  if (erros.length === 0) {
    showStatus('report', relatorios.length === 1 ? 'Relatório gerado!' : `${relatorios.length} relatórios gerados!`);
  } else {
    showStatus('report', `Erros: ${erros.join(' | ')}`, true);
  }
});

function mostrarRelatorios(relatorios) {
  modalBody.innerHTML = '';
  relatorios.forEach(({ nome, content, filename }, idx) => {
    if (idx > 0) {
      const sep = document.createElement('hr');
      sep.className = 'report-sep';
      modalBody.appendChild(sep);
    }

    const wrap = document.createElement('div');
    wrap.className = 'report-wrap';

    const header = document.createElement('div');
    header.className = 'report-header';

    const title = document.createElement('span');
    title.className = 'report-title';
    title.textContent = nome;

    const btn = document.createElement('button');
    btn.className = 'modal-download';
    btn.textContent = 'Baixar .md';
    btn.addEventListener('click', () => {
      const blob = new Blob([content], { type: 'text/markdown' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = filename; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1500);
    });

    const btnSelecionar = document.createElement('button');
    btnSelecionar.className = 'modal-download';
    btnSelecionar.textContent = 'Copiar tudo';
    btnSelecionar.addEventListener('click', () => {
      navigator.clipboard.writeText(content).then(() => {
        btnSelecionar.textContent = 'Copiado!';
        setTimeout(() => { btnSelecionar.textContent = 'Copiar tudo'; }, 2000);
      });
    });

    const acoes = document.createElement('div');
    acoes.className = 'report-acoes';
    acoes.appendChild(btnSelecionar);
    acoes.appendChild(btn);

    header.appendChild(title);
    header.appendChild(acoes);

    const body = document.createElement('div');
    body.className = 'report-body';
    body.innerHTML = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>');

    wrap.appendChild(header);
    wrap.appendChild(body);
    modalBody.appendChild(wrap);
  });
  modal.classList.add('visible');
}

/* ═══════════════════════════════════════════════
   CURVA DE DESEMBOLSO
   ═══════════════════════════════════════════════ */
document.getElementById('form-desembolso').addEventListener('submit', async e => {
  e.preventDefault();
  const arquivo = document.getElementById('file-desembolso').files[0];
  const corte   = document.getElementById('corte-desembolso').value;
  if (!arquivo) { showStatus('desembolso', 'Selecione um arquivo Excel.', true); return; }
  const nome = arquivo.name.replace(/\.[^/.]+$/, '');

  setLoading('desembolso', true);
  try {
    const fd = new FormData();
    fd.append('arquivo', arquivo);
    fd.append('nome_projeto', nome);
    fd.append('dia_corte', corte);
    const res = await fetch('/api/desembolso', { method: 'POST', body: fd });
    const j   = await res.json();
    if (!res.ok || j.error) throw new Error(j.error);
    showStatus('desembolso', j.message);
  } catch (err) {
    showStatus('desembolso', `Erro: ${err.message}`, true);
  } finally {
    setLoading('desembolso', false);
  }
});

/* ═══════════════════════════════════════════════
   MODAL  (novos colaboradores)
   ═══════════════════════════════════════════════ */
function perguntarGrupos(desconhecidos) {
  return new Promise(resolve => {
    const body = document.getElementById('modal-grupos-body');
    body.innerHTML = '';

    desconhecidos.forEach(nome => {
      const row = document.createElement('div');
      row.className = 'grupos-row';

      const label = document.createElement('span');
      label.className = 'grupos-nome';
      label.textContent = nome;

      const tg = document.createElement('div');
      tg.className = 'grupos-toggle toggle-group';

      ['Horizontes', 'Fornecedores'].forEach((grupo, i) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'toggle-btn' + (i === 0 ? ' active' : '');
        btn.dataset.grupo = grupo;
        btn.dataset.recurso = nome;
        btn.textContent = grupo;
        btn.addEventListener('click', () => {
          tg.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
        });
        tg.appendChild(btn);
      });

      row.appendChild(label);
      row.appendChild(tg);
      body.appendChild(row);
    });

    document.getElementById('modal-grupos').classList.add('visible');

    document.getElementById('modal-grupos-confirmar').onclick = () => {
      const resultado = {};
      desconhecidos.forEach(nome => {
        const ativo = body.querySelector(`[data-recurso="${CSS.escape(nome)}"].active`);
        if (ativo) resultado[nome] = ativo.dataset.grupo;
      });
      document.getElementById('modal-grupos').classList.remove('visible');
      resolve(resultado);
    };

    document.getElementById('modal-grupos-cancelar').onclick = () => {
      document.getElementById('modal-grupos').classList.remove('visible');
      resolve(null);
    };
  });
}

/* ═══════════════════════════════════════════════
   CRONOGRAMA DE EQUIPE
   ═══════════════════════════════════════════════ */
document.getElementById('form-cronograma').addEventListener('submit', async e => {
  e.preventDefault();
  const arquivo = document.getElementById('file-cronograma').files[0];
  if (!arquivo) { showStatus('cronograma', 'Selecione um arquivo Excel.', true); return; }

  const tipos = Array.from(document.querySelectorAll('.toggle-btn.active')).map(b => b.dataset.type);

  const hoje = (() => {
    const d = new Date();
    const yy = String(d.getFullYear()).slice(2);
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yy}${mm}${dd}`;
  })();

  const endpoints = { projetos: '/api/cronograma/projetos', equipe: '/api/cronograma/equipe', clientes: '/api/cronograma/clientes' };
  const labels    = { projetos: 'Projetos por Cliente', equipe: 'Fornecedores', clientes: 'Equipe Interna' };

  // Verificar novos recursos apenas quando equipe ou clientes estiver selecionado
  let gruposNovos = {};
  const precisaVerificar = tipos.some(t => t === 'equipe' || t === 'clientes');

  if (precisaVerificar) {
    setLoading('cronograma', true);
    try {
      const fd = new FormData();
      fd.append('arquivo', arquivo);
      const res = await fetch('/api/cronograma/verificar', { method: 'POST', body: fd });
      const j   = await res.json();
      if (!res.ok || j.error) throw new Error(j.error);
      if (j.desconhecidos && j.desconhecidos.length > 0) {
        setLoading('cronograma', false);
        const resultado = await perguntarGrupos(j.desconhecidos);
        if (resultado === null) return; // usuário cancelou
        gruposNovos = resultado;
        setLoading('cronograma', true);
      }
    } catch (err) {
      setLoading('cronograma', false);
      showStatus('cronograma', `Erro: ${err.message}`, true);
      return;
    }
  }

  setLoading('cronograma', true);
  const todasImgs = [], todosNomes = [], erros = [];


  for (let i = 0; i < tipos.length; i++) {
    const tipo = tipos[i];
    if (tipos.length > 1) showStatus('cronograma', `Processando ${i + 1} / ${tipos.length}…`);
    try {
      const fd = new FormData();
      fd.append('arquivo', arquivo);
      if ((tipo === 'equipe' || tipo === 'clientes') && Object.keys(gruposNovos).length)
        fd.append('grupos_novos', JSON.stringify(gruposNovos));
      const res = await fetch(endpoints[tipo], { method: 'POST', body: fd });
      const j   = await res.json();
      if (!res.ok || j.error) throw new Error(j.error);

      const prefixo = `${hoje} - Horizontes - ${labels[tipo]}`;
      if (tipo === 'projetos') {
        todasImgs.push(j.image);
        todosNomes.push(`${prefixo}.png`);
      } else if (tipo === 'clientes') {
        if (j.horizontes) { todasImgs.push(j.horizontes); todosNomes.push(`${prefixo}.png`); }
      } else if (tipo === 'equipe') {
        if (j.fornecedores) { todasImgs.push(j.fornecedores); todosNomes.push(`${prefixo}.png`); }
      }
    } catch (err) {
      erros.push(`${labels[tipo]}: ${err.message}`);
    }
  }

  todasImgs.forEach((b64, i) => {
    const a = document.createElement('a');
    a.href = `data:image/png;base64,${b64}`;
    a.download = todosNomes[i];
    a.click();
  });

  setLoading('cronograma', false);
  if (erros.length) showStatus('cronograma', `Erros: ${erros.join(' | ')}`, true);
  else if (todasImgs.length) showStatus('cronograma', todasImgs.length === 1 ? 'Gráfico gerado!' : `${todasImgs.length} gráficos gerados!`);
});

/* ═══════════════════════════════════════════════
   ANOTAÇÃO DE FÉRIAS
   ═══════════════════════════════════════════════ */

// Estado local do funcionário consultado
let _feriasNome      = '';
let _feriasHistorico = [];

// Preenche o datalist com os funcionários cadastrados
async function feriasCarregarLista() {
  try {
    const res   = await fetch('/api/ferias/funcionarios');
    const nomes = await res.json();
    const dl    = document.getElementById('ferias-datalist');
    dl.innerHTML = nomes.map(n => `<option value="${n}">`).join('');
  } catch (_) {}
}
feriasCarregarLista();

// Consultar ao clicar no botão ou pressionar Enter
document.getElementById('btn-ferias-buscar').addEventListener('click', feriasBuscar);
document.getElementById('ferias-nome').addEventListener('keydown', e => {
  if (e.key === 'Enter') feriasBuscar();
});

async function feriasBuscar() {
  const nome = document.getElementById('ferias-nome').value.trim();
  if (!nome) { showStatus('ferias', 'Informe o nome do funcionário.', true); return; }

  try {
    const res  = await fetch('/api/ferias/consultar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome }),
    });
    const data = await res.json();
    _feriasNome = nome;

    if (data.novo) {
      document.getElementById('ferias-admissao-group').classList.remove('hidden');
      document.getElementById('ferias-form-section').classList.remove('hidden');
      document.getElementById('ferias-resultado').classList.add('hidden');
      showStatus('ferias', 'Funcionário não cadastrado — informe a data de admissão antes de registrar.');
    } else {
      document.getElementById('ferias-admissao-group').classList.add('hidden');
      document.getElementById('ferias-form-section').classList.remove('hidden');
      _feriasHistorico = data.ferias_tiradas || [];
      feriasRenderizar(data.saldo, _feriasHistorico, data.proximo);
      showStatus('ferias', '');
    }
  } catch (err) {
    showStatus('ferias', `Erro: ${err.message}`, true);
  }
}

// Preview do total de dias ao alterar as datas
['ferias-inicio', 'ferias-fim'].forEach(id =>
  document.getElementById(id).addEventListener('change', feriasAtualizarDias)
);

function feriasAtualizarDias() {
  const ini = document.getElementById('ferias-inicio').value;
  const fim = document.getElementById('ferias-fim').value;
  const el  = document.getElementById('ferias-dias-count');
  if (ini && fim) {
    const d = Math.round((new Date(fim) - new Date(ini)) / 86400000) + 1;
    el.textContent = d > 0 ? `${d} dia${d !== 1 ? 's' : ''}` : '—';
    el.classList.toggle('ferias-dias-ok', d > 0);
  } else {
    el.textContent = '—';
    el.classList.remove('ferias-dias-ok');
  }
}

// Registrar férias
document.getElementById('btn-ferias').addEventListener('click', async () => {
  const nome     = document.getElementById('ferias-nome').value.trim();
  const inicio   = document.getElementById('ferias-inicio').value;
  const fim      = document.getElementById('ferias-fim').value;
  const admissao = document.getElementById('ferias-admissao').value;

  if (!nome || !inicio || !fim) {
    showStatus('ferias', 'Preencha nome, início e fim das férias.', true);
    return;
  }

  const body = { nome, inicio, fim };
  if (admissao) body.admissao = admissao;

  setLoading('ferias', true);
  try {
    const res  = await fetch('/api/ferias/registrar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    setLoading('ferias', false);

    if (data.erro) { showStatus('ferias', data.mensagem || data.erro, true); return; }

    // Limpa campos do formulário
    document.getElementById('ferias-admissao-group').classList.add('hidden');
    document.getElementById('ferias-admissao').value  = '';
    document.getElementById('ferias-inicio').value    = '';
    document.getElementById('ferias-fim').value       = '';
    document.getElementById('ferias-dias-count').textContent = '—';
    document.getElementById('ferias-dias-count').classList.remove('ferias-dias-ok');

    _feriasHistorico = data.ferias_tiradas || [];
    feriasRenderizar(data.saldo, _feriasHistorico, null);
    showStatus('ferias', `Férias registradas com sucesso — ${data.entry.dias} dias debitados.`);
    feriasCarregarLista();
  } catch (err) {
    setLoading('ferias', false);
    showStatus('ferias', `Erro: ${err.message}`, true);
  }
});

// Cancelar (remover) um registro de férias
async function feriasCancelar(entryId) {
  if (!confirm('Remover este registro de férias?')) return;

  try {
    const res  = await fetch('/api/ferias/cancelar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome: _feriasNome, id: entryId }),
    });
    const data = await res.json();

    if (data.erro) { showStatus('ferias', data.erro, true); return; }

    _feriasHistorico = data.ferias_tiradas || [];
    feriasRenderizar(data.saldo, _feriasHistorico, null);
    showStatus('ferias', 'Registro removido.');
  } catch (err) {
    showStatus('ferias', `Erro: ${err.message}`, true);
  }
}

// Renderiza saldo e histórico na tela
function feriasRenderizar(saldo, historico, proximo) {
  const resultado = document.getElementById('ferias-resultado');
  resultado.classList.remove('hidden');

  // ── Saldo ──
  const saldoWrap = document.getElementById('ferias-saldo-wrap');
  if (!saldo || saldo.length === 0) {
    const msg = proximo
      ? `Nenhum período aquisitivo concluído ainda. Próximo saldo de 30 dias disponível em <strong>${proximo.concedido_em}</strong>.`
      : 'Nenhum período aquisitivo concluído ainda.';
    saldoWrap.innerHTML = `<p class="form-obs ferias-obs-vazio">${msg}</p>`;
  } else {
    const totalRestante = saldo.reduce((acc, p) => acc + p.dias_restantes, 0);
    saldoWrap.innerHTML = `
      <div class="ferias-section-header">
        <h3 class="ferias-section-title">Saldo de Férias</h3>
        <span class="ferias-total-badge">Total disponível: <strong>${totalRestante} dias</strong></span>
      </div>
      <table class="ferias-table">
        <thead>
          <tr>
            <th>Período Aquisitivo</th>
            <th>Concedido</th>
            <th>Usado</th>
            <th>Saldo</th>
          </tr>
        </thead>
        <tbody>
          ${saldo.map(p => `
            <tr class="${p.dias_restantes === 0 ? 'ferias-row-zerado' : ''}">
              <td>${p.label}</td>
              <td class="ferias-cell-num">${p.dias_totais} dias</td>
              <td class="ferias-cell-num">${p.dias_usados} dias</td>
              <td class="ferias-cell-num ${p.dias_restantes > 0 ? 'ferias-saldo-positivo' : 'ferias-saldo-zero'}">
                ${p.dias_restantes} dias
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      ${proximo ? `<p class="form-obs ferias-obs-proximo">Próximo período (Ano ${proximo.ano}) disponível em ${proximo.concedido_em}.</p>` : ''}
    `;
  }

  // ── Histórico ──
  const histWrap = document.getElementById('ferias-historico-wrap');
  const lista    = [...historico].sort((a, b) => a.inicio.localeCompare(b.inicio));

  if (lista.length === 0) {
    histWrap.innerHTML = '<p class="form-obs ferias-obs-vazio">Nenhuma férias registrada.</p>';
  } else {
    histWrap.innerHTML = `
      <h3 class="ferias-section-title ferias-section-title--hist">Histórico de Férias</h3>
      <table class="ferias-table">
        <thead>
          <tr>
            <th>Início</th>
            <th>Fim</th>
            <th>Dias</th>
            <th>Períodos Debitados</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${lista.map(ft => `
            <tr>
              <td>${ft.inicio}</td>
              <td>${ft.fim}</td>
              <td class="ferias-cell-num">${ft.dias}</td>
              <td class="ferias-cell-debitos">${ft.debitos.map(d => `Ano ${d.periodo_ano}: ${d.dias}d`).join(' + ')}</td>
              <td class="ferias-cell-acao">
                <button class="ferias-btn-cancelar" data-id="${ft.id}" title="Remover registro">✕</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    histWrap.querySelectorAll('.ferias-btn-cancelar').forEach(btn =>
      btn.addEventListener('click', () => feriasCancelar(btn.dataset.id))
    );
  }
}
