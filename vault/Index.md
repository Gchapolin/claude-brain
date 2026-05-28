---
type: hub-mobile
created: 2026-05-09
tags: [hub, mobile]
cssclasses: [brain-hub]
---

<!-- status line + KPIs sao renderizados pelo dataviewjs abaixo (uma so query, KPI e tabs sempre concordam) -->

```button
name Nova captura
type command
action Templater: Open Insert Template Modal
color purple
```
```button
name Atualizar tudo
type command
action Shell commands: Execute: ClaudeBrain: Atualizar tudo
color blue
```

```dataviewjs
// Force full width on the dataviewjs container itself
dv.container.style.width = '100%';
dv.container.style.maxWidth = '100%';
dv.container.style.margin = '0';
dv.container.style.padding = '0';
const dvBlock = dv.container.closest('.block-language-dataviewjs');
if (dvBlock) {
  dvBlock.style.width = '100%';
  dvBlock.style.maxWidth = '100%';
  dvBlock.style.margin = '0';
  dvBlock.style.padding = '0';
}

const state = { tab: 'projetos', filter: '', status: 'todos', stack: 'todos' };

// Data
const projects = dv.pages('#projecthub').sort(p => p.file.name).array();

// Pendencias index: walks <Projeto>/Pendencias/<slug>/{spec,task,tests,resultado}.md
const pendIndex = {}; // { projeto: { slug: { spec:true, task:true, tests:true, resultado:true } } }
let legadoTotal = 0;
const legadoByProj = {}; // { projeto: N }
for (const p of dv.pages('').array()) {
  const parts = p.file.path.split('/');
  const idxPend = parts.indexOf('Pendencias');
  if (idxPend === -1 || idxPend === 0) continue;
  const projeto = parts[idxPend - 1];
  if (parts.length === idxPend + 2 && parts[idxPend + 1].endsWith('.md')) {
    legadoTotal++;
    legadoByProj[projeto] = (legadoByProj[projeto] || 0) + 1;
    continue;
  }
  if (parts.length === idxPend + 3 && ['spec.md','task.md','tests.md','resultado.md'].includes(parts[idxPend + 2])) {
    const slug = parts[idxPend + 1];
    const fname = parts[idxPend + 2].replace('.md','');
    pendIndex[projeto] = pendIndex[projeto] || {};
    pendIndex[projeto][slug] = pendIndex[projeto][slug] || {};
    pendIndex[projeto][slug][fname] = true;
  }
}

function classify(files) {
  const has = k => !!files[k];
  if (!has('spec')) return 'invalid';
  if (!has('task')) return (has('tests') || has('resultado')) ? 'invalid' : 'aberta';
  if (!has('tests')) return has('resultado') ? 'invalid' : 'planejamento';
  if (!has('resultado')) return 'pronta';
  return 'realizada';
}

const stages = ['aberta','planejamento','pronta','realizada'];
const byProjeto = {};
const globalCounts = { aberta:0, planejamento:0, pronta:0, realizada:0 };
for (const projeto of Object.keys(pendIndex)) {
  byProjeto[projeto] = { aberta:0, planejamento:0, pronta:0, realizada:0 };
  for (const slug of Object.keys(pendIndex[projeto])) {
    const s = classify(pendIndex[projeto][slug]);
    if (stages.includes(s)) {
      byProjeto[projeto][s]++;
      globalCounts[s]++;
    }
  }
}

const counts = { projetos: projects.length, pendencias: globalCounts.aberta + globalCounts.planejamento + globalCounts.pronta };

// Build root
const root = dv.container.createEl('div', { cls: 'ts-root' });

// Status line + KPIs (mesmo source que o tab bar — sem race condition entre blocks)
root.createEl('p', { text: `${projects.length} projetos · sincronizado · ClaudeBrain`, cls: 'ts-status' });
const kpisHost = root.createEl('div', { cls: 'kpis' });
const kpiCard = (v, l) => {
  const wrap = kpisHost.createEl('div', { cls: 'kpi' });
  wrap.createEl('div', { cls: 'v', text: String(v) });
  wrap.createEl('div', { cls: 'l', text: l });
};
const totalNotesGrafo = projects.reduce((s, p) => s + (p.notes_count || 0), 0);
kpiCard(projects.length, 'Projetos');
kpiCard(globalCounts.aberta, 'Aberta');
kpiCard(globalCounts.planejamento, 'Planejamento');
kpiCard(globalCounts.pronta, 'Pronta');
kpiCard(globalCounts.realizada, 'Realizada');
kpiCard(totalNotesGrafo || '—', 'Nodes do grafo');

// Legado banner
if (legadoTotal > 0) {
  const banner = root.createEl('div', { cls: 'legado-banner' });
  banner.createEl('strong', { text: `${legadoTotal} pendencia(s) em formato legado` });
  const detail = Object.entries(legadoByProj).map(([p, n]) => `${p}: ${n}`).join(' · ');
  banner.createEl('span', { text: ` (${detail}). Rode /pendencia migrate <projeto> pra converter.` });
}

// Tab bar
const tabBar = root.createEl('div', { cls: 'ts-tabs' });
[['projetos','Projetos'],['pendencias','Pendencias']].forEach(([id, label]) => {
  const tab = tabBar.createEl('span', { cls: 'ts-tab' + (state.tab === id ? ' active' : ''), attr: { 'data-id': id } });
  tab.createEl('span', { text: label });
  tab.createEl('span', { text: String(counts[id]), cls: 'ts-badge' });
  tab.onclick = () => { state.tab = id; render(); };
});

// Filter bar (only on Projetos)
const filterBar = root.createEl('div', { cls: 'ts-filters' });
const searchInput = filterBar.createEl('input', { type: 'text', cls: 'ts-search', attr: { placeholder: 'Filtrar projetos...' } });
const statusEl = filterBar.createEl('select', { cls: 'ts-select' });
['todos','ativo','notes-only'].forEach(v => statusEl.createEl('option', { value: v, text: 'Status: ' + v }));
const stackEl = filterBar.createEl('select', { cls: 'ts-select' });
['todos','SW','KT','JS','TS','HTML','PY','RS','WORK'].forEach(v => stackEl.createEl('option', { value: v, text: 'Stack: ' + v }));
const counter = filterBar.createEl('span', { cls: 'ts-counter' });

searchInput.oninput = (e) => { state.filter = e.target.value; render(); };
statusEl.onchange = (e) => { state.status = e.target.value; render(); };
stackEl.onchange = (e) => { state.stack = e.target.value; render(); };

// Content
const content = root.createEl('div', { cls: 'ts-content' });

const escapeHtml = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fileLink = p => `<a class="internal-link" data-href="${escapeHtml(p.file.path)}" href="${escapeHtml(p.file.path)}">${escapeHtml(p.file.name)}</a>`;
const stackPills = arr => (arr || []).map(s => `<span class="pill pill-${String(s).toLowerCase()}">${escapeHtml(s)}</span>`).join(' ') || '—';
const statusBadge = p => p.no_graphify
  ? '<span class="status-dot status-work"></span>notes-only'
  : '<span class="status-dot status-active"></span>ativo';
const dt = (m) => m ? m.toFormat('dd/MM HH:mm') : '—';

function render() {
  tabBar.querySelectorAll('.ts-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.id === state.tab);
  });
  filterBar.style.display = state.tab === 'projetos' ? '' : 'none';
  content.innerHTML = '';
  if (state.tab === 'projetos') renderProjetos();
  else if (state.tab === 'pendencias') renderPendencias();
}

function renderProjetos() {
  let rows = projects;
  const q = state.filter.toLowerCase();
  if (q) rows = rows.filter(p => p.file.name.toLowerCase().includes(q) || (p.description||'').toLowerCase().includes(q));
  if (state.status === 'ativo') rows = rows.filter(p => !p.no_graphify);
  if (state.status === 'notes-only') rows = rows.filter(p => p.no_graphify);
  if (state.stack !== 'todos') rows = rows.filter(p => (p.stack||[]).includes(state.stack));
  counter.textContent = `${rows.length} de ${projects.length} · ordem: nome`;
  content.innerHTML = `
    <table class="ts-table">
      <thead><tr><th>Projeto</th><th>Descricao</th><th>Stack</th><th>Status</th><th>Nodes</th><th>Notas</th></tr></thead>
      <tbody>${rows.map(p => `
        <tr>
          <td class="ts-name"><span class="dot dot-${p.color||'gray'}"></span>${fileLink(p)}</td>
          <td class="muted">${escapeHtml(p.description || '—')}</td>
          <td>${stackPills(p.stack)}</td>
          <td>${statusBadge(p)}</td>
          <td class="num">${p.notes_count ?? '—'}</td>
          <td class="num">${p.no_graphify ? '—' : (p.notes_count ?? '—')}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderPendencias() {
  const rows = Object.keys(byProjeto).sort();
  if (rows.length === 0) {
    content.innerHTML = '<p class="muted">Nenhuma pendencia em cascata.</p>';
    return;
  }
  const totalCol = stages.map(s => `<th class="num">${s}</th>`).join('');
  content.innerHTML = `
    <table class="ts-table">
      <thead><tr><th>Projeto</th>${totalCol}<th class="num">total</th></tr></thead>
      <tbody>${rows.map(proj => {
        const c = byProjeto[proj];
        const total = stages.reduce((s, k) => s + c[k], 0);
        return `<tr>
          <td class="ts-name">${escapeHtml(proj)}</td>
          ${stages.map(s => `<td class="num">${c[s]}</td>`).join('')}
          <td class="num"><strong>${total}</strong></td>
        </tr>`;
      }).join('')}
      </tbody>
    </table>`;
}

content.addEventListener('click', (e) => {
  const a = e.target.closest('a.internal-link');
  if (!a) return;
  e.preventDefault();
  const path = a.dataset.href;
  app.workspace.openLinkText(path, '', false);
});

render();
```

#hub #claudebrain #dataview
