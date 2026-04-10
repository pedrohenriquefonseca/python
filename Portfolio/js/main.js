let allPhotos = [];
let currentPhotos = [];
let currentIndex = 0;
let activeFilters = new Set(); // Set de strings "Categoria:Valor"

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
}

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

function parseCategories() {
  // Agrupa valores por categoria a partir das tags "Categoria:Valor"
  const cats = new Map();
  allPhotos.forEach(f => {
    (f.tags || []).forEach(tag => {
      const sep = tag.indexOf(':');
      if (sep === -1) return; // ignora tags sem formato
      const cat = tag.substring(0, sep).trim();
      const val = tag.substring(sep + 1).trim();
      if (!val) return; // ignora placeholders como "Subject:"
      if (!cats.has(cat)) cats.set(cat, new Set());
      cats.get(cat).add(val);
    });
  });
  return cats;
}

function buildFilters() {
  const nav = document.getElementById('filters');
  nav.innerHTML = '';

  // Botão "All"
  const allBtn = document.createElement('button');
  allBtn.className = 'filter-btn active';
  allBtn.id = 'filter-all';
  allBtn.textContent = 'All';
  allBtn.addEventListener('click', () => {
    activeFilters.clear();
    updateFilterUI();
    renderGallery();
  });
  nav.appendChild(allBtn);

  // Dropdowns por categoria
  const cats = parseCategories();
  [...cats.keys()].sort((a, b) => a.localeCompare(b, 'pt')).forEach(cat => {
    const values = [...cats.get(cat)].sort((a, b) => a.localeCompare(b, 'pt'));
    nav.appendChild(buildDropdown(cat, values));
  });

  // Fecha dropdowns ao clicar fora
  document.addEventListener('click', e => {
    if (!e.target.closest('.dropdown')) closeAllDropdowns();
  });
}

function buildDropdown(cat, values) {
  const wrap = document.createElement('div');
  wrap.className = 'dropdown';

  const btn = document.createElement('button');
  btn.className = 'dropdown-btn';
  btn.dataset.cat = cat;
  btn.innerHTML = `${cat} <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>`;

  const menu = document.createElement('div');
  menu.className = 'dropdown-menu';

  values.forEach(val => {
    const item = document.createElement('div');
    item.className = 'dropdown-item';
    item.textContent = val;
    item.dataset.filter = `${cat}:${val}`;
    item.addEventListener('click', e => {
      e.stopPropagation();
      const key = item.dataset.filter;
      if (activeFilters.has(key)) {
        activeFilters.delete(key);
      } else {
        activeFilters.add(key);
      }
      updateFilterUI();
      renderGallery();
    });
    menu.appendChild(item);
  });

  btn.addEventListener('click', e => {
    e.stopPropagation();
    const isOpen = wrap.classList.contains('open');
    closeAllDropdowns();
    if (!isOpen) wrap.classList.add('open');
  });

  wrap.appendChild(btn);
  wrap.appendChild(menu);
  return wrap;
}

function closeAllDropdowns() {
  document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
}

function getAvailableForCat(cat) {
  // Retorna os valores disponíveis para uma categoria dado os filtros das OUTRAS categorias
  const otherFilters = [...activeFilters].filter(f => !f.startsWith(cat + ':'));

  const photos = otherFilters.length === 0
    ? allPhotos
    : allPhotos.filter(f => {
        const photoTags = new Set(f.tags || []);
        const byCat = new Map();
        otherFilters.forEach(filter => {
          const c = filter.substring(0, filter.indexOf(':'));
          if (!byCat.has(c)) byCat.set(c, []);
          byCat.get(c).push(filter);
        });
        return [...byCat.values()].every(filters =>
          filters.some(filter => photoTags.has(filter))
        );
      });

  const available = new Set();
  photos.forEach(f => {
    (f.tags || []).forEach(tag => {
      if (tag.startsWith(cat + ':')) {
        const val = tag.substring(cat.length + 1).trim();
        if (val) available.add(val);
      }
    });
  });
  return available;
}

function updateFilterUI() {
  // Botão All — ativo quando não há filtros
  const allBtn = document.getElementById('filter-all');
  if (allBtn) allBtn.classList.toggle('active', activeFilters.size === 0);

  // Itens dos dropdowns — mostra só os disponíveis (itens ativos sempre visíveis)
  document.querySelectorAll('.dropdown').forEach(wrap => {
    const cat = wrap.querySelector('.dropdown-btn').dataset.cat;
    const available = getAvailableForCat(cat);

    wrap.querySelectorAll('.dropdown-item').forEach(item => {
      const isActive = activeFilters.has(item.dataset.filter);
      const val = item.dataset.filter.substring(cat.length + 1);
      const isAvailable = available.has(val);
      item.classList.toggle('active', isActive);
      // Itens ativos sempre visíveis; inativas só se disponíveis
      item.style.display = (isActive || isAvailable) ? '' : 'none';
    });
  });

  // Botões dos dropdowns — mostra contagem de seleções ativas
  document.querySelectorAll('.dropdown-btn').forEach(btn => {
    const cat = btn.dataset.cat;
    const count = [...activeFilters].filter(f => f.startsWith(cat + ':')).length;
    const label = count > 0 ? `${cat} <span class="dropdown-count">${count}</span>` : cat;
    btn.innerHTML = `${label} <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>`;
    btn.classList.toggle('has-active', count > 0);
  });
}

// ─── Galeria ──────────────────────────────────────────────────

function renderGallery() {
  currentPhotos = activeFilters.size === 0
    ? [...allPhotos]
    : allPhotos.filter(f => {
        const photoTags = new Set(f.tags || []);
        // Agrupa filtros por categoria
        const byCat = new Map();
        activeFilters.forEach(filter => {
          const cat = filter.substring(0, filter.indexOf(':'));
          if (!byCat.has(cat)) byCat.set(cat, []);
          byCat.get(cat).push(filter);
        });
        // AND entre categorias, OR dentro de cada categoria
        return [...byCat.values()].every(filters =>
          filters.some(filter => photoTags.has(filter))
        );
      });

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
    img.alt = '';
    img.loading = 'lazy';

    // Escudo transparente — captura cliques e bloqueia interação com a img
    const shield = document.createElement('div');
    shield.className = 'img-shield';
    shield.addEventListener('click', () => openViewer(idx));

    item.appendChild(img);
    item.appendChild(shield);
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
    { cls: 'info-gear', text: [foto.camera, foto.lens].filter(Boolean).join('  ·  ') },
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

  // ── Proteção de imagens ──────────────────────────────────────

  // Bloqueia clique direito em qualquer imagem
  document.addEventListener('contextmenu', e => {
    if (e.target.tagName === 'IMG') e.preventDefault();
  });

  // Bloqueia arrastar imagens
  document.addEventListener('dragstart', e => {
    if (e.target.tagName === 'IMG') e.preventDefault();
  });

  // Ajusta o escudo do visualizador para cobrir exatamente a foto
  const viewerImg    = document.getElementById('viewer-img');
  const viewerShield = document.querySelector('.viewer-img-shield');

  function fitViewerShield() {
    const r = viewerImg.getBoundingClientRect();
    viewerShield.style.width  = r.width  + 'px';
    viewerShield.style.height = r.height + 'px';
    viewerShield.style.top    = viewerImg.offsetTop  + 'px';
    viewerShield.style.left   = viewerImg.offsetLeft + 'px';
  }

  viewerImg.addEventListener('load', fitViewerShield);
  window.addEventListener('resize', fitViewerShield);

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
