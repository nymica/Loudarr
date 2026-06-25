'use strict';

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  mode:         'genre',
  category:     null,   // full category object from taxonomy
  genre:        '',     // active search tag
  range:        'month',
  page:         1,
  profiles:     null,
  pending:      null,
};

let taxonomyData = [];  // full taxonomy from API, kept in memory

// ── Toast ─────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const stack = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  stack.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s';
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

// ── Helpers ───────────────────────────────────────────────────────────────
function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtNum(n) {
  if (n === null || n === undefined) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000)     return Math.round(n / 1_000) + 'K';
  return String(n);
}

async function apiFetch(url, opts = {}) {
  const res  = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

const SOURCE_LABELS = {
  lastfm: 'Last.fm', musicbrainz: 'MusicBrainz',
  deezer: 'Deezer',  listenbrainz: 'ListenBrainz',
};

function sourceBadge(source) {
  if (!source) return '';
  return `<span class="source-badge source-${esc(source)}">${esc(SOURCE_LABELS[source] || source)}</span>`;
}

// ── Init ──────────────────────────────────────────────────────────────────
function initDiscoverPage() {
  loadTaxonomy();
}

// ── Mode switching ────────────────────────────────────────────────────────
function switchMode(mode, btn) {
  state.mode = mode;
  state.page = 1;

  document.querySelectorAll('.mode-tab')
    .forEach(t => t.classList.toggle('is-active', t === btn));

  const catBar      = document.getElementById('cat-bar');
  const subBar      = document.getElementById('sub-bar');
  const trendingBar = document.getElementById('trending-bar');
  const thBased     = document.getElementById('th-based');

  catBar.style.display      = mode === 'genre'    ? '' : 'none';
  subBar.style.display      = mode === 'genre'    ? '' : 'none';
  trendingBar.style.display = mode === 'trending' ? '' : 'none';
  if (thBased) thBased.style.display = mode === 'similar' ? '' : 'none';

  if (mode === 'genre') {
    if (state.genre) loadSuggestions();
  } else {
    loadSuggestions();
  }
}

// ── Taxonomy / category loading ───────────────────────────────────────────
async function loadTaxonomy() {
  const scroll = document.getElementById('cat-scroll');
  try {
    taxonomyData = await apiFetch('/api/taxonomy');
    renderCategoryTabs(taxonomyData);

    // Auto-select first category that has library artists, else first overall
    const first = taxonomyData.find(c => c.in_library) || taxonomyData[0];
    if (first) {
      const btn = document.querySelector(`.cat-tab[data-cat="${CSS.escape(first.name)}"]`);
      if (btn) selectCategory(first.name, btn);
    }
  } catch (err) {
    scroll.innerHTML = `<span class="cat-loading" style="color:#e07070">${esc(err.message)}</span>`;
  }
}

function renderCategoryTabs(taxonomy) {
  const scroll = document.getElementById('cat-scroll');
  scroll.innerHTML = '';
  taxonomy.forEach(cat => {
    const btn = document.createElement('button');
    btn.className   = 'cat-tab' + (cat.in_library ? ' has-library' : '');
    btn.dataset.cat = cat.name;
    // lib-dot + label
    const dot  = document.createElement('span');
    dot.className = 'lib-dot';
    dot.title = cat.in_library ? 'Artists from this category are in your library' : '';
    const label = document.createTextNode(cat.name);
    btn.appendChild(dot);
    btn.appendChild(label);
    btn.addEventListener('click', () => selectCategory(cat.name, btn));
    scroll.appendChild(btn);
  });
}

function selectCategory(catName, btn) {
  const cat = taxonomyData.find(c => c.name === catName);
  if (!cat) return;

  state.category = cat;
  state.genre    = cat.tag;
  state.page     = 1;

  document.querySelectorAll('.cat-tab')
    .forEach(t => t.classList.toggle('is-active', t === btn));

  renderSubGenres(cat);
  loadSuggestions();
}

function renderSubGenres(cat) {
  const scroll = document.getElementById('sub-scroll');
  scroll.innerHTML = '';

  // "All [Category]" button
  const allBtn = makeSubBtn(`All ${cat.name}`, cat.tag, true, false, true);
  scroll.appendChild(allBtn);

  // Individual sub-genre chips
  cat.subs.forEach(sub => {
    scroll.appendChild(makeSubBtn(sub.name, sub.tag, false, sub.in_library, false));
  });
}

function makeSubBtn(label, tag, isActive, inLibrary, isAll) {
  const btn = document.createElement('button');
  btn.className = [
    'sub-btn',
    isActive   ? 'is-active' : '',
    inLibrary  ? 'has-library' : '',
    isAll      ? 'sub-all' : '',
  ].filter(Boolean).join(' ');
  btn.dataset.tag = tag;
  btn.textContent = label;
  btn.addEventListener('click', () => selectSubGenre(tag, btn));
  return btn;
}

function selectSubGenre(tag, btn) {
  state.genre = tag;
  state.page  = 1;
  document.querySelectorAll('.sub-btn')
    .forEach(b => b.classList.toggle('is-active', b === btn));
  loadSuggestions();
}

// ── Trending range ────────────────────────────────────────────────────────
function selectRange(range, btn) {
  state.range = range;
  state.page  = 1;
  document.querySelectorAll('.range-btn')
    .forEach(b => b.classList.toggle('is-active', b === btn));
  loadSuggestions();
}

// ── Suggestions ───────────────────────────────────────────────────────────
async function loadSuggestions() {
  setLoading(true);
  document.getElementById('artist-tbody').innerHTML = '';

  const params = new URLSearchParams({ mode: state.mode, page: state.page });
  if (state.mode === 'genre')    params.set('genre', state.genre);
  if (state.mode === 'trending') params.set('range', state.range);

  try {
    const data = await apiFetch(`/api/discover?${params}`);
    setLoading(false);
    renderTable(data);
  } catch (err) {
    setLoading(false);
    showError(err.message);
  }
}

function setLoading(on) {
  document.getElementById('loading-state').style.display = on ? 'flex' : 'none';
  document.getElementById('error-state').style.display   = 'none';
  document.getElementById('artist-table').style.display  = on ? 'none' : '';
  document.getElementById('empty-state').style.display   = 'none';
  document.getElementById('pagination').style.display    = 'none';
}

function showError(msg) {
  document.getElementById('error-state').style.display = 'block';
  document.getElementById('error-state').textContent   = msg;
  document.getElementById('artist-table').style.display = 'none';
}

// ── Table render ──────────────────────────────────────────────────────────
function renderTable(data) {
  const tbody   = document.getElementById('artist-tbody');
  const table   = document.getElementById('artist-table');
  const empty   = document.getElementById('empty-state');
  const thBased = document.getElementById('th-based');

  if (thBased) thBased.style.display = state.mode === 'similar' ? '' : 'none';

  if (!data.items?.length) {
    empty.style.display = 'block';
    table.style.display = 'none';
    return;
  }

  table.style.display = '';

  data.items.forEach(artist => {
    const tagsHtml = (artist.tags || [])
      .map(t => `<span class="tag-chip">${esc(t)}</span>`).join('');

    const basedCell = state.mode === 'similar'
      ? `<td class="cell-based">${esc(artist.based_on || '')}</td>` : '';

    const tr = document.createElement('tr');
    tr.className    = 'artist-row';
    tr.dataset.name = artist.name;
    tr.innerHTML = `
      <td class="col-name">
        <button class="artist-name-btn" onclick="toggleDetail(this)">
          <svg class="icon chevron-icon"><use href="#ic-chevron-right"/></svg>
          ${esc(artist.name)}
        </button>
        ${sourceBadge(artist.source)}
      </td>
      <td><div class="cell-tags">${tagsHtml}</div></td>
      <td class="cell-listeners col-listeners">${fmtNum(artist.listeners)}</td>
      ${basedCell}
      <td class="col-actions"></td>`;

    // Build action buttons safely (avoids HTML-encoding issues with artist data)
    const actionsCell = tr.querySelector('.col-actions');
    const addBtn = document.createElement('button');
    addBtn.className = 'btn btn-primary btn-sm';
    addBtn.innerHTML = '<svg class="icon"><use href="#ic-plus"/></svg>Add';
    addBtn.addEventListener('click', () => openAddModal(artist));

    const ignBtn = document.createElement('button');
    ignBtn.className = 'btn btn-ghost btn-sm';
    ignBtn.style.marginLeft = '4px';
    ignBtn.innerHTML = '<svg class="icon"><use href="#ic-ban"/></svg>Ignore';
    ignBtn.addEventListener('click', () => ignoreArtist({ name: artist.name, mbid: artist.mbid }, ignBtn));

    actionsCell.appendChild(addBtn);
    actionsCell.appendChild(ignBtn);

    tbody.appendChild(tr);

    // Detail row
    const colspan = state.mode === 'similar' ? 5 : 4;
    const detail  = document.createElement('tr');
    detail.className     = 'is-detail-row';
    detail.style.display = 'none';
    detail.dataset.for   = artist.name;
    detail.dataset.image = artist.image || '';
    detail.dataset.bio   = artist.bio   || '';
    detail.dataset.url   = artist.url   || '';

    detail.innerHTML = `<td class="detail-cell" colspan="${colspan}">
      <div class="detail-inner">
        <div class="detail-thumb-placeholder" id="dthumb-${esc(artist.name)}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 18V5l12-2v13"/>
            <circle cx="6" cy="18" r="3"/>
            <circle cx="18" cy="16" r="3"/>
          </svg>
        </div>
        <div class="detail-body">
          <p class="detail-bio" id="dbio-${esc(artist.name)}">${
            artist.bio
              ? esc(artist.bio)
              : '<span style="color:var(--text-3)">Loading&hellip;</span>'
          }</p>
          <div class="detail-albums" id="dalbums-${esc(artist.name)}"></div>
          ${artist.url
            ? `<div class="detail-lastfm">
                <a href="${esc(artist.url)}" target="_blank" rel="noopener">
                  View on ${esc(SOURCE_LABELS[artist.source] || 'source')}
                  <svg class="icon"><use href="#ic-external"/></svg>
                </a>
               </div>`
            : ''}
        </div>
      </div>
    </td>`;
    tbody.appendChild(detail);
  });

  renderPagination(data.page, data.pages);
}

// ── Detail expand ─────────────────────────────────────────────────────────
function toggleDetail(btn) {
  const mainRow   = btn.closest('tr');
  const detailRow = mainRow.nextElementSibling;
  const isOpen    = detailRow.style.display !== 'none';

  btn.classList.toggle('is-expanded', !isOpen);
  detailRow.style.display = isOpen ? 'none' : '';
  if (!isOpen) loadDetailData(detailRow);
}

async function loadDetailData(detailRow) {
  const name  = detailRow.dataset.for;
  const image = detailRow.dataset.image;
  const bio   = detailRow.dataset.bio;

  const thumbEl = document.getElementById(`dthumb-${name}`);
  if (image && thumbEl && thumbEl.tagName !== 'IMG') {
    const img     = document.createElement('img');
    img.src       = image;
    img.alt       = name;
    img.className = 'detail-thumb';
    img.onerror   = () => {};
    thumbEl.replaceWith(img);
  }

  const bioEl = document.getElementById(`dbio-${name}`);
  if (bioEl && bio) bioEl.textContent = bio;

  const albumsEl = document.getElementById(`dalbums-${name}`);
  if (albumsEl && !albumsEl.dataset.loaded) {
    albumsEl.dataset.loaded = '1';
    try {
      const d = await apiFetch(`/api/artist/details?name=${encodeURIComponent(name)}`);
      if (d.albums?.length) {
        albumsEl.innerHTML = d.albums
          .map(a => `<span class="album-item">${esc(a.name)}</span>`).join('');
      }
    } catch (_) {}
  }
}

// ── Ignore ────────────────────────────────────────────────────────────────
async function ignoreArtist(artistInfo, btn) {
  btn.disabled = true;
  try {
    await apiFetch('/api/artist/ignore', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(artistInfo),
    });
    const row  = btn.closest('tr');
    const next = row.nextElementSibling;
    [row, next].forEach(r => {
      r.style.transition = 'opacity 0.2s';
      r.style.opacity    = '0';
      setTimeout(() => r.remove(), 200);
    });
    showToast(`${artistInfo.name} ignored`, 'info');
  } catch (err) {
    btn.disabled = false;
    showToast(err.message, 'error');
  }
}

// ── Add modal ─────────────────────────────────────────────────────────────
async function openAddModal(artist) {
  state.pending = artist;

  document.getElementById('modal-name').textContent      = artist.name;
  document.getElementById('modal-listeners').textContent =
    artist.listeners != null ? `${fmtNum(artist.listeners)} listeners` : '';
  document.getElementById('modal-tags').innerHTML =
    (artist.tags || []).map(t => `<span class="tag-chip">${esc(t)}</span>`).join('');

  const imgEl = document.getElementById('modal-img');
  if (artist.image) { imgEl.src = artist.image; imgEl.style.display = ''; }
  else              { imgEl.style.display = 'none'; }

  document.getElementById('modal-overlay').style.display = 'flex';
  document.getElementById('btn-confirm-add').disabled    = true;

  if (!state.profiles) {
    try {
      state.profiles = await apiFetch('/api/lidarr/profiles');
    } catch (err) {
      showToast(`Could not load profiles: ${err.message}`, 'error');
      closeModal();
      return;
    }
  }

  populateSelect('sel-quality',  state.profiles.quality_profiles,  'id',   'name');
  populateSelect('sel-metadata', state.profiles.metadata_profiles, 'id',   'name');
  populateSelect('sel-root',     state.profiles.root_folders,      'path', 'path');
  document.getElementById('btn-confirm-add').disabled = false;
}

function populateSelect(id, items, valKey, labelKey) {
  document.getElementById(id).innerHTML =
    items.map(i => `<option value="${esc(i[valKey])}">${esc(i[labelKey])}</option>`).join('');
}

function closeModal(e) {
  if (e && e.target !== document.getElementById('modal-overlay')) return;
  document.getElementById('modal-overlay').style.display = 'none';
  state.pending = null;
}

async function confirmAdd() {
  const artist = state.pending;
  if (!artist) return;

  const btn = document.getElementById('btn-confirm-add');
  btn.disabled    = true;
  btn.textContent = 'Looking up…';

  try {
    const lookup = await apiFetch(`/api/artist/lookup?name=${encodeURIComponent(artist.name)}`);
    btn.textContent = 'Adding…';

    await apiFetch('/api/artist/add', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        artist:                 lookup.artist,
        qualityProfileId:       document.getElementById('sel-quality').value,
        metadataProfileId:      document.getElementById('sel-metadata').value,
        rootFolderPath:         document.getElementById('sel-root').value,
        monitor:                document.getElementById('sel-monitor').value,
        searchForMissingAlbums: document.getElementById('chk-search').checked,
      }),
    });

    showToast(`${artist.name} added to Lidarr`, 'success');
    closeModal();

    document.querySelectorAll(
      `tr[data-name="${CSS.escape(artist.name)}"], tr[data-for="${CSS.escape(artist.name)}"]`
    ).forEach(r => {
      r.style.transition = 'opacity 0.2s';
      r.style.opacity    = '0';
      setTimeout(() => r.remove(), 200);
    });
  } catch (err) {
    showToast(err.message, 'error');
    btn.disabled  = false;
    btn.innerHTML = '<svg class="icon"><use href="#ic-plus"/></svg> Add Artist';
  }
}

// ── Pagination ────────────────────────────────────────────────────────────
function renderPagination(page, pages) {
  const el = document.getElementById('pagination');
  if (pages <= 1) { el.style.display = 'none'; return; }
  el.style.display = 'flex';

  let html = `<button class="page-btn" ${page === 1 ? 'disabled' : ''}
                       onclick="goPage(${page - 1})">&#8249;</button>`;
  for (let i = 1; i <= pages; i++) {
    if (pages > 7 && Math.abs(i - page) > 2 && i !== 1 && i !== pages) {
      if (i === page - 3 || i === page + 3) html += '<span class="page-ellipsis">…</span>';
      continue;
    }
    html += `<button class="page-btn ${i === page ? 'is-active' : ''}"
                     onclick="goPage(${i})">${i}</button>`;
  }
  html += `<button class="page-btn" ${page === pages ? 'disabled' : ''}
                    onclick="goPage(${page + 1})">&#8250;</button>`;
  el.innerHTML = html;
}

function goPage(p) {
  state.page = p;
  document.querySelector('.content').scrollTo(0, 0);
  loadSuggestions();
}

// ── Library Health ────────────────────────────────────────────────────────

function initLibraryHealthPage() {
  document.getElementById('btn-scan').addEventListener('click', () => healthScan(false));
  document.getElementById('btn-rescan').addEventListener('click', () => healthScan(true));
  healthScan(false, /*silent=*/true);
}

async function healthScan(force, silent = false) {
  const btnScan   = document.getElementById('btn-scan');
  const btnRescan = document.getElementById('btn-rescan');
  const loading   = document.getElementById('scan-loading');
  const errorEl   = document.getElementById('scan-error');
  const prompt    = document.getElementById('scan-prompt');
  const results   = document.getElementById('scan-results');

  prompt.style.display  = 'none';
  errorEl.style.display = 'none';
  results.style.display = 'none';
  loading.style.display = 'flex';
  btnScan.disabled   = true;
  btnRescan.disabled = true;

  try {
    const data = await apiFetch('/api/library/scan' + (force ? '?force=1' : ''));
    loading.style.display  = 'none';
    btnScan.disabled       = false;
    btnRescan.disabled     = false;
    btnScan.style.display  = 'none';
    btnRescan.style.display = '';
    renderHealthResults(data);
  } catch (err) {
    loading.style.display = 'none';
    btnScan.disabled      = false;
    btnRescan.disabled    = false;
    if (silent) {
      prompt.style.display = 'block';
    } else {
      errorEl.textContent   = err.message;
      errorEl.style.display = 'block';
    }
  }
}

function renderHealthResults(data) {
  const results = document.getElementById('scan-results');
  const metaEl  = document.getElementById('scan-meta');
  const empty   = document.getElementById('scan-empty');
  const table   = document.getElementById('health-table');
  const tbody   = document.getElementById('health-tbody');

  results.style.display = '';
  tbody.innerHTML = '';

  if (data.scanned_at) {
    metaEl.textContent = `Scanned ${new Date(data.scanned_at + 'Z').toLocaleString()}`;
  }

  const artists = data.artists || [];
  if (!artists.length) {
    empty.style.display = 'block';
    table.style.display = 'none';
    return;
  }

  empty.style.display = 'none';
  table.style.display = '';

  for (const a of artists) {
    const tr = document.createElement('tr');
    if (a.status === 'warning') tr.classList.add('health-row-warning');
    if (a.status === 'error')   tr.classList.add('health-row-error');

    // Status icon
    const statusTd = document.createElement('td');
    statusTd.className = 'col-health-status';
    if (a.status === 'ok') {
      statusTd.innerHTML = '<svg class="icon" style="color:var(--success)"><use href="#ic-check"/></svg>';
    } else if (a.status === 'warning') {
      statusTd.innerHTML = '<span class="health-warn-dot">!</span>';
    } else {
      statusTd.innerHTML = '<svg class="icon" style="color:var(--danger)"><use href="#ic-x"/></svg>';
    }
    tr.appendChild(statusTd);

    // Lidarr name
    const nameTd = document.createElement('td');
    nameTd.textContent = a.name;
    tr.appendChild(nameTd);

    // MusicBrainz name
    const mbTd = document.createElement('td');
    if (a.status === 'ok') {
      mbTd.innerHTML = '<span class="text-muted">Matches</span>';
    } else if (a.mb_name) {
      mbTd.textContent = a.mb_name;
      if (a.mb_disambiguation) {
        const dis = document.createElement('span');
        dis.className   = 'text-muted';
        dis.textContent = ` (${a.mb_disambiguation})`;
        mbTd.appendChild(dis);
      }
    } else {
      mbTd.innerHTML = '<span class="text-muted">—</span>';
    }
    tr.appendChild(mbTd);

    // Missing count
    const missingTd = document.createElement('td');
    missingTd.className = 'col-listeners';
    const badge = document.createElement('span');
    badge.className = 'missing-count';
    badge.textContent = a.missing_count;
    badge.title = (a.missing_titles || []).join('\n');
    missingTd.appendChild(badge);
    tr.appendChild(missingTd);

    // Issue description
    const issueTd = document.createElement('td');
    issueTd.textContent = a.issue || '';
    if (a.status === 'error')   issueTd.style.color = 'var(--danger)';
    if (a.status === 'warning') issueTd.style.color = 'var(--warning)';
    tr.appendChild(issueTd);

    // Actions
    const actionsTd = document.createElement('td');
    actionsTd.className = 'col-actions';

    const refreshBtn = document.createElement('button');
    refreshBtn.className = 'btn btn-ghost btn-sm';
    refreshBtn.innerHTML = '<svg class="icon"><use href="#ic-refresh"/></svg> Refresh';
    refreshBtn.title = 'Queue a metadata refresh for this artist in Lidarr';
    refreshBtn.addEventListener('click', () => healthRefreshArtist(a.lidarr_id, a.name, refreshBtn));
    actionsTd.appendChild(refreshBtn);

    if (a.mbid) {
      const mbLink = document.createElement('a');
      mbLink.className = 'btn btn-ghost btn-sm';
      mbLink.href      = `https://musicbrainz.org/artist/${encodeURIComponent(a.mbid)}`;
      mbLink.target    = '_blank';
      mbLink.rel       = 'noopener noreferrer';
      mbLink.innerHTML = '<svg class="icon"><use href="#ic-external"/></svg>';
      mbLink.title     = 'View on MusicBrainz';
      actionsTd.appendChild(mbLink);
    }

    tr.appendChild(actionsTd);
    tbody.appendChild(tr);
  }
}

async function healthRefreshArtist(artistId, artistName, btn) {
  btn.disabled  = true;
  btn.innerHTML = 'Queuing&hellip;';
  try {
    await apiFetch('/api/library/refresh-artist', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ artist_id: artistId }),
    });
    showToast(`Metadata refresh queued for ${artistName}`, 'success');
    btn.innerHTML = '<svg class="icon"><use href="#ic-check"/></svg> Queued';
  } catch (err) {
    showToast(err.message, 'error');
    btn.disabled  = false;
    btn.innerHTML = '<svg class="icon"><use href="#ic-refresh"/></svg> Refresh';
  }
}

// ── Cache clear ───────────────────────────────────────────────────────────
async function clearCacheAndReload() {
  const btn = document.getElementById('btn-refresh');
  btn.disabled = true;
  try {
    await apiFetch('/api/cache/clear', { method: 'POST' });
    state.profiles = null;
    taxonomyData   = [];
    showToast('Cache cleared — reloading…', 'info');
    setTimeout(() => { loadTaxonomy(); btn.disabled = false; }, 400);
  } catch (err) {
    showToast(err.message, 'error');
    btn.disabled = false;
  }
}
