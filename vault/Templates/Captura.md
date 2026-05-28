<%*
const modal = app.plugins.plugins.modalforms.api;
if (!modal) {
    new Notice("Modal Forms plugin nao esta ativo.");
    return;
}
const result = await modal.openForm("capturar-nota");
if (!result || result.status !== "ok") return;
const data = result.getData();

const projeto = (data.projeto || "").trim();
if (!projeto) {
    new Notice("Captura abortada: projeto e obrigatorio.");
    return;
}

const titulo = (data.titulo || "sem-titulo").trim();
const slugRaw = (data.slug || titulo).trim();
const conteudo = (data.conteudo || "").trim();
const tagsRaw = (data.tags || "").trim();
const tagsList = tagsRaw ? tagsRaw.split(",").map(t => t.trim()).filter(Boolean) : [];

const stripAccents = s => s.normalize("NFKD").replace(/[̀-ͯ]/g, "");
let slug = stripAccents(slugRaw).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
if (!slug) {
    new Notice("Captura abortada: slug invalido.");
    return;
}

let candidate = slug;
let i = 2;
while (app.vault.getAbstractFileByPath(`${projeto}/Pendencias/${candidate}`)) {
    candidate = `${slug}-${i}`;
    i += 1;
}
slug = candidate;

const date = tp.date.now("YYYY-MM-DD");
const folderpath = `${projeto}/Pendencias/${slug}`;
const filepath = `${folderpath}/spec.md`;

await app.vault.createFolder(folderpath).catch(() => {});

const tagsYaml = ["pendencia", projeto, ...tagsList].join(", ");
const body = `---
type: pendencia-spec
project: ${projeto}
slug: ${slug}
stage: spec
created: ${date}
updated: ${date}
tags: [${tagsYaml}]
---

# ${titulo}

## Contexto

${conteudo}

## Problema

(descreva o problema em 1-3 frases)

## Criterios de aceitacao

- [ ]

## Fora de escopo

-
`;

const file = await app.vault.create(filepath, body);
await app.workspace.getLeaf(true).openFile(file);
new Notice(`Pendencia criada: ${filepath}`);
%>
