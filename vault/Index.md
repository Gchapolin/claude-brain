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
const allPages = dv.pages('').where(p =>
  !p.file.path.endsWith('Index.md') &&
  !p.file.path.endsWith('Capturar.md') &&
  !p.file.path.startsWith('Templates/')
).array();
const pendentes = allPages.filter(p => p.file.path.startsWith('Notas Pendentes/'));

const counts = { projetos: projects.length, pendentes: pendentes.length };

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
const notasPessoais = allPages.length - pendentes.length;
const totalNotesGrafo = projects.reduce((s, p) => s + (p.notes_count || 0), 0);
kpiCard(projects.length, 'Projetos');
kpiCard(notasPessoais, 'Notas pessoais');
kpiCard(totalNotesGrafo || '—', 'Nodes do grafo');
kpiCard(pendentes.length, 'Aguardando triagem');

// Tab bar
const tabBar = root.createEl('div', { cls: 'ts-tabs' });
[['projetos','Projetos'],['pendentes','Notas Pendentes']].forEach(([id, label]) => {
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
  else if (state.tab === 'pendentes') renderPendentes();
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

function renderPendentes() {
  content.innerHTML = `
    <table class="ts-table">
      <thead><tr><th>Nota</th><th>Projeto</th><th>Capturada</th></tr></thead>
      <tbody>${pendentes.map(p => `
        <tr>
          <td>${fileLink(p)}</td>
          <td class="muted">${escapeHtml(p.project || '—')}</td>
          <td class="num">${dt(p.file.ctime)}</td>
        </tr>`).join('') || '<tr><td colspan="3" class="muted">Nada na fila de triagem.</td></tr>'}
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
