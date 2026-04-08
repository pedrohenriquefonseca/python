let allPhotos = [];
let currentPhotos = [];
let currentIndex = 0;
let activeTags = new Set();

// ─── Utilitários ──────────────────────────────────────────────

function formatDate(dateStr) {
  if (!dateStr) return '';
  // dateStr vem no formato '2026-03-19'
  const [year, month, day] = dateStr.split('-').map(Number);
  const meses = [
    'janeiro','fevereiro','março','abril','maio','junho',
    'julho','agosto','setembro','outubro','novembro','dezembro'
  ];
  return `${day} de ${meses[month - 1]} de ${year}`;
} // conjunto de tags ativas (vazio = todas)

// ─── Inicialização ────────────────────────────────────────────

async function init() {
  try {
    const res = await fetch(`fotos.json?v=${Date.now()}`);
    allPhotos = await res.json();
  } catch {
    allPhotos = [];
  }

  buildFilters();
  renderGallery();
  bindViewerEvents();
}

// ─── Filtros ──────────────────────────────────────────────────

function buildFilters() {
  const tags = new Set();
  allPhotos.forEach(f => (f.tags || []).forEach(t => tags.add(t)));

  const nav = document.getElementById('filters');
  nav.innerHTML = '';

  appendFilterBtn(nav, 'Todas', 'all');
  [...tags].sort((a, b) => a.localeCompare(b, 'pt')).forEach(tag => {
    appendFilterBtn(nav, tag, tag);
  });

  updateFilterUI();
}

function appendFilterBtn(nav, label, tag) {
  const btn = document.createElement('button');
  btn.className = 'filter-btn';
  btn.textContent = label;
  btn.dataset.tag = tag;

  btn.addEventListener('click', e => {
    if (tag === 'all') {
      activeTags.clear();
    } else if (e.ctrlKey || e.metaKey) {
      // Ctrl+clique: adiciona ou remove da seleção
      if (activeTags.has(tag)) {
        activeTags.delete(tag);
      } else {
        activeTags.add(tag);
      }
    } else {
      // Clique simples: seleciona só essa tag (ou limpa se já era a única)
      if (activeTags.size === 1 && activeTags.has(tag)) {
        activeTags.clear();
      } else {
        activeTags.clear();
        activeTags.add(tag);
      }
    }
    updateFilterUI();
    renderGallery();
  });

  nav.appendChild(btn);
}

function updateFilterUI() {
  document.querySelectorAll('.filter-btn').forEach(btn => {
    const tag = btn.dataset.tag;
    const isAll = tag === 'all';
    const isActive = isAll ? activeTags.size === 0 : activeTags.has(tag);
    btn.classList.toggle('active', isActive);
  });
}

// ─── Galeria ──────────────────────────────────────────────────

function renderGallery() {
  currentPhotos = activeTags.size === 0
    ? [...allPhotos]
    : allPhotos.filter(f => (f.tags || []).some(t => activeTags.has(t)));

  const gallery = document.getElementById('gallery');
  gallery.innerHTML = '';

  if (currentPhotos.length === 0) {
    gallery.innerHTML = '<p class="empty">Nenhuma foto encontrada. Adicione imagens à pasta <code>fotos/</code> e faça push.</p>';
    return;
  }

  currentPhotos.forEach((foto, idx) => {
    const item = document.createElement('div');
    item.className = 'gallery-item';

    const img = document.createElement('img');
    img.src = Config.getThumbnailUrl(foto);
    img.alt = foto.filename;
    img.loading = 'lazy';

    item.appendChild(img);
    item.addEventListener('click', () => openViewer(idx));
    gallery.appendChild(item);
  });
}

// ─── Visualizador ─────────────────────────────────────────────

function openViewer(index) {
  currentIndex = index;
  document.getElementById('viewer').hidden = false;
  document.body.style.overflow = 'hidden';
  updateViewer();
}

function closeViewer() {
  document.getElementById('viewer').hidden = true;
  document.body.style.overflow = '';
  if (document.fullscreenElement) document.exitFullscreen();
}

function navigate(dir) {
  const next = currentIndex + dir;
  if (next >= 0 && next < currentPhotos.length) {
    currentIndex = next;
    updateViewer();
  }
}

function updateViewer() {
  const foto = currentPhotos[currentIndex];

  // Contador
  document.getElementById('viewer-counter').textContent =
    `${currentIndex + 1} / ${currentPhotos.length}`;

  // Imagem
  const img = document.getElementById('viewer-img');
  img.src = Config.getImageUrl(foto);
  img.alt = foto.filename;

  // Metadados
  const title = foto.name || foto.filename;

  const camSettings = [
    foto.aperture,
    foto.shutter,
    foto.iso       ? `ISO ${foto.iso}`  : '',
    foto.focalLength || '',
  ].filter(Boolean).join('  ·  ');

  const lines = [
    { cls: 'info-filename', text: title },
    { cls: 'info-date',     text: formatDate(foto.date) },
    { cls: 'info-camera',   text: camSettings },
    { cls: 'info-body',     text: foto.camera },
    { cls: 'info-lens',     text: foto.lens },
  ].filter(l => l.text);

  document.getElementById('viewer-info').innerHTML =
    lines.map(l => `<span class="${l.cls}">${l.text}</span>`).join('');

  // Setas
  document.getElementById('btn-prev').disabled = currentIndex === 0;
  document.getElementById('btn-next').disabled = currentIndex === currentPhotos.length - 1;
}

function toggleFullscreen() {
  const img = document.getElementById('viewer-img');
  if (!document.fullscreenElement) {
    img.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen();
  }
}

// ─── Eventos ──────────────────────────────────────────────────

function bindViewerEvents() {
  document.getElementById('btn-close').addEventListener('click', closeViewer);
  document.getElementById('btn-prev').addEventListener('click', () => navigate(-1));
  document.getElementById('btn-next').addEventListener('click', () => navigate(1));
  document.getElementById('btn-fullscreen').addEventListener('click', toggleFullscreen);

  // Fechar clicando no fundo
  document.getElementById('viewer').addEventListener('click', e => {
    if (e.target === document.getElementById('viewer')) closeViewer();
  });

  // Teclado
  document.addEventListener('keydown', e => {
    if (document.getElementById('viewer').hidden) return;
    if (e.key === 'Escape')      closeViewer();
    if (e.key === 'ArrowLeft')   navigate(-1);
    if (e.key === 'ArrowRight')  navigate(1);
  });

  // Swipe no mobile
  let touchStartX = 0;
  const viewer = document.getElementById('viewer');
  viewer.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; });
  viewer.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 50) navigate(dx < 0 ? 1 : -1);
  });
}

// ─── Start ────────────────────────────────────────────────────

init();
