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
['report', 'desembolso', 'fisico', 'cronograma'].forEach(id => {
  const input = document.getElementById(`file-${id}`);
  const text  = document.getElementById(`file-text-${id}`);
  const zone  = document.getElementById(`zone-${id}`);

  function setFile(file) {
    if (!file) return;
    text.textContent = file.name;
    zone.classList.add('has-file');
  }

  input.addEventListener('change', () => setFile(input.files[0]));

  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', ()  => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
      // Cria um DataTransfer para injetar o arquivo no input
      const dt = new DataTransfer();
      dt.items.add(e.dataTransfer.files[0]);
      input.files = dt.files;
      setFile(e.dataTransfer.files[0]);
    }
  });
});

/* ═══════════════════════════════════════════════
   TOGGLE  (Projetos / Equipe)
   ═══════════════════════════════════════════════ */
document.querySelectorAll('.toggle-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tipo-cronograma').value = btn.dataset.type;
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

function mostrarModal(imagens) {
  modalBody.innerHTML = '';
  imagens.forEach(src => {
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${src}`;
    modalBody.appendChild(img);
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
  const arquivo = document.getElementById('file-report').files[0];
  const nome    = document.getElementById('nome-report').value.trim();
  if (!arquivo) { showStatus('report', 'Selecione um arquivo Excel.', true); return; }
  if (!nome)    { showStatus('report', 'Informe o nome do projeto.', true);  return; }

  setLoading('report', true);
  try {
    const fd = new FormData();
    fd.append('arquivo', arquivo);
    fd.append('nome_projeto', nome);
    const res = await fetch('/api/report', { method: 'POST', body: fd });
    if (!res.ok) { const j = await res.json(); throw new Error(j.error); }
    downloadBlob(await res.blob(), res);
    showStatus('report', 'Relatório gerado com sucesso!');
  } catch (err) {
    showStatus('report', `Erro: ${err.message}`, true);
  } finally {
    setLoading('report', false);
  }
});

/* ═══════════════════════════════════════════════
   CURVA DE DESEMBOLSO
   ═══════════════════════════════════════════════ */
document.getElementById('form-desembolso').addEventListener('submit', async e => {
  e.preventDefault();
  const arquivo = document.getElementById('file-desembolso').files[0];
  const nome    = document.getElementById('nome-desembolso').value.trim();
  const corte   = document.getElementById('corte-desembolso').value;
  if (!arquivo) { showStatus('desembolso', 'Selecione um arquivo Excel.', true); return; }
  if (!nome)    { showStatus('desembolso', 'Informe o nome do projeto.', true);  return; }

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
   FÍSICO FINANCEIRO
   ═══════════════════════════════════════════════ */
document.getElementById('form-fisico').addEventListener('submit', async e => {
  e.preventDefault();
  const arquivo = document.getElementById('file-fisico').files[0];
  const nome    = document.getElementById('nome-fisico').value.trim();
  const corte   = document.getElementById('corte-fisico').value;
  if (!arquivo) { showStatus('fisico', 'Selecione um arquivo Excel.', true); return; }
  if (!nome)    { showStatus('fisico', 'Informe o nome do projeto.', true);  return; }

  setLoading('fisico', true);
  try {
    const fd = new FormData();
    fd.append('arquivo', arquivo);
    fd.append('nome_projeto', nome);
    fd.append('dia_corte', corte);
    const res = await fetch('/api/fisico-financeiro', { method: 'POST', body: fd });
    if (!res.ok) { const j = await res.json(); throw new Error(j.error); }
    downloadBlob(await res.blob(), res);
    showStatus('fisico', 'Tabela gerada com sucesso!');
  } catch (err) {
    showStatus('fisico', `Erro: ${err.message}`, true);
  } finally {
    setLoading('fisico', false);
  }
});

/* ═══════════════════════════════════════════════
   CRONOGRAMA DE EQUIPE
   ═══════════════════════════════════════════════ */
document.getElementById('form-cronograma').addEventListener('submit', async e => {
  e.preventDefault();
  const arquivo = document.getElementById('file-cronograma').files[0];
  const tipo    = document.getElementById('tipo-cronograma').value;
  if (!arquivo) { showStatus('cronograma', 'Selecione um arquivo Excel.', true); return; }

  setLoading('cronograma', true);
  try {
    const fd       = new FormData();
    fd.append('arquivo', arquivo);
    const endpoint = tipo === 'projetos' ? '/api/cronograma/projetos' : '/api/cronograma/equipe';
    const res      = await fetch(endpoint, { method: 'POST', body: fd });
    const j        = await res.json();
    if (!res.ok || j.error) throw new Error(j.error);

    const imgs = tipo === 'projetos'
      ? [j.image]
      : [j.horizontes, j.fornecedores].filter(Boolean);

    mostrarModal(imgs);
    showStatus('cronograma', 'Gráfico gerado!');
  } catch (err) {
    showStatus('cronograma', `Erro: ${err.message}`, true);
  } finally {
    setLoading('cronograma', false);
  }
});
