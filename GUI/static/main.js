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
['report', 'desembolso', 'cronograma'].forEach(id => {
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

  setLoading('cronograma', true);
  const todasImgs = [], todosNomes = [], erros = [];

  for (let i = 0; i < tipos.length; i++) {
    const tipo = tipos[i];
    if (tipos.length > 1) showStatus('cronograma', `Processando ${i + 1} / ${tipos.length}…`);
    try {
      const fd = new FormData();
      fd.append('arquivo', arquivo);
      const res = await fetch(endpoints[tipo], { method: 'POST', body: fd });
      const j   = await res.json();
      if (!res.ok || j.error) throw new Error(j.error);

      const prefixo = `${hoje} - Horizontes - ${labels[tipo]}`;
      if (tipo === 'projetos') {
        // Projetos por Cliente: um único gráfico
        todasImgs.push(j.image);
        todosNomes.push(`${prefixo}.png`);
      } else if (tipo === 'clientes') {
        // Projetos: apenas o gráfico Horizontes
        if (j.horizontes) { todasImgs.push(j.horizontes); todosNomes.push(`${prefixo}.png`); }
      } else if (tipo === 'equipe') {
        // Fornecedores: apenas o gráfico de fornecedores
        if (j.fornecedores) { todasImgs.push(j.fornecedores); todosNomes.push(`${prefixo}.png`); }
      } else {
        // Equipe Interna: apenas o gráfico horizontes
        if (j.horizontes) { todasImgs.push(j.horizontes); todosNomes.push(`${prefixo}.png`); }
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
