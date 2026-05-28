---
name: project-new
description: "Bootstrap vault-only de um projeto novo no ClaudeBrain. Cria <Projeto>/ com hub minimo + primeira pendencia 'visao-do-projeto'. NAO cria codigo nem git init no diretorio de codigo."
trigger: /project-new
---

# /project-new

Bootstrap **vault-only** de um projeto novo. Filosofia: pense primeiro (no vault), codifique depois.

## Usage

```
/project-new <nome>          # cria <nome>/ no vault com hub + primeira pendencia
/project-new <nome> --dry-run
```

## O que esta skill NAO faz

- Nao cria `~/PROJETOS/<nome>/` (diretorio de codigo).
- Nao roda `git init`.
- Nao escreve `CLAUDE.md`, `README.md`, `.gitignore`.
- Nao configura symlink iCloud (essa fase vem depois via `/claudebrain-init`).

## Step 0 — Resolve repo path

Leia `~/.claude/skills/project-new/.repo-path`. Salve como `$REPO`.

## Step 1 — Validar nome

1. Normalize pra slug: ja existe `scripts/pendencia/slug.py` (a skill pode reusar).
   ```bash
   python3 -c "import sys; sys.path.insert(0, '$REPO/scripts'); from pendencia.slug import normalize; print(normalize('$RAW_NAME'))"
   ```
2. Mas mantenha o NOME ORIGINAL pra display (so o folder e slug-normalizado).
3. Pergunte ao usuario qual nome usar. Padrao: usar o nome original com PascalCase se for camelCase, ou kebab-case se for o que faz sentido.

## Step 2 — Localizar o vault

Default: `~/PROJETOS/Obsidian/ClaudeBrain/`. Se nao existir: avise e sugira `/claudebrain-init` primeiro.

## Step 3 — Criar estrutura

```
<VAULT>/<Nome>/
├── <Nome>.md             hub
├── Pendencias/
│   └── visao-do-projeto/
│       └── spec.md
└── Geral/                (vazia)
```

### Hub `<Nome>.md`

```markdown
---
type: project-hub
project: <Nome>
created: <DATE>
tags: [hub, projecthub]
status: vault-only
---

# <Nome>

## Visao
Veja [[visao-do-projeto/spec]].

## Pendencias
Em construcao. Use `/pendencia status <Nome>` pra ver.

## Geral
(notas operacionais sobre o projeto)
```

### Primeira pendencia: `visao-do-projeto/spec.md`

Use o template `$REPO/scripts/pendencia/templates/spec.md.tpl` com placeholders preenchidos. O `{{CONTEXT}}` deve ser pre-populado com perguntas guia:

```markdown
## Contexto

Esta e a visao inicial do projeto. Preencha respondendo:

1. **Qual problema esse projeto resolve?** (1-2 frases)
2. **Quem usa?** (publico-alvo, persona)
3. **Como saberemos que funcionou?** (criterios de sucesso, metricas)
4. **Restricoes** (tecnologia, deadline, orcamento, dependencias externas)
5. **Riscos iniciais** (o que pode dar errado)

## Problema

(decorrencia da pergunta 1)

## Criterios de aceitacao

- [ ] (decorrencia da pergunta 3)

## Fora de escopo

- (o que decidimos NAO fazer mesmo sendo tentador)
```

## Step 4 — Anunciar

```
Projeto <Nome> criado no vault.
   Hub:        <VAULT>/<Nome>/<Nome>.md
   Pendencia:  <VAULT>/<Nome>/Pendencias/visao-do-projeto/spec.md

Proximos passos:
   1. Abra o Obsidian e preencha 'visao-do-projeto/spec.md'.
   2. Quando estiver pronto, rode `/pendencia next visao-do-projeto`.
   3. Quando decidir codificar, crie o diretorio em ~/PROJETOS/<nome>/
      e rode `/claudebrain-init` pra integrar (symlink iCloud, mirror, etc).
```

## Casos de falha

- **Vault nao existe**: pare. Sugira `/claudebrain-init` primeiro.
- **`<Nome>/` ja existe no vault**: pergunte se quer abortar, mergear (so cria o que falta), ou usar nome diferente.
- **`<Nome>/` existe mas e symlink (projeto ja integrado)**: avise — esse projeto ja existe. Ofereca `/pendencia new <Nome>/visao-do-projeto`.

## Modo --dry-run

Imprima a estrutura que seria criada, nao escreva nada.
