<%*
const modal = app.plugins.plugins.modalforms.api;
if (!modal) {
    new Notice("Modal Forms plugin nao esta ativo.");
    return;
}
const result = await modal.openForm("capturar-nota");
if (!result || result.status !== "ok") return;
const data = result.getData();

const projeto = data.projeto || "geral";
const titulo = (data.titulo || "sem-titulo").trim();
const conteudo = (data.conteudo || "").trim();
const tagsRaw = (data.tags || "").trim();
const tagsList = tagsRaw ? tagsRaw.split(",").map(t => t.trim()).filter(Boolean) : [];

const date = tp.date.now("YYYY-MM-DD");
const time = tp.date.now("HH-mm");

const safeTitulo = titulo.replace(/[\\\/:\*\?\"<>\|]/g, "-").replace(/\s+/g, " ").trim();
const filename = `${date} ${time} ${safeTitulo}`;
const filepath = `Notas Pendentes/${filename}.md`;

const tagsYaml = ["pendente", "captura", projeto, ...tagsList].join(", ");
const body = `---
project: ${projeto}
created: ${date} ${time.replace("-", ":")}
status: pendente
tags: [${tagsYaml}]
---

# ${titulo}

${conteudo}
`;

const file = await app.vault.create(filepath, body);
await app.workspace.getLeaf(true).openFile(file);
new Notice(`Nota criada em ${filepath}`);
%>
