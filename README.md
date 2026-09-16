# ClaudeBrain

Setup de Obsidian opinativo pra usar como **segundo cerebro de desenvolvimento** quando voce tem multiplos projetos de codigo localmente. Combina:

- **Graphify** (knowledge graph por projeto, queryable pelo Claude Code)
- **Vault Obsidian unificado** com cada projeto como subpasta
- **Sync iCloud Drive** entre Mac e iPhone/iPad (free)
- **Form de captura rapida** (Modal Forms + Templater)
- **Atualizacao automatica** ao detectar novos projetos (Shell Commands)
- **Visual Notion-like** com Dataview + CSS snippet customizado

Nao e um plugin. E um **conjunto de configuracoes + scripts** que voce aplica num vault novo.

---

## Filosofia da organizacao de pastas

A estrutura nao e arbitraria. Cada pasta tem um proposito explicito ligado a **como voce captura, processa e revisita** informacao.

### Hierarquia geral

```
ClaudeBrain/
├── Index.md                 hub central — KPIs, projetos, pendencias por estagio
├── Capturar.md              pagina-form pra criar nota nova
├── Notas Pendentes/         legado (captura antiga; deprecated apos cascata)
├── Templates/
│   └── Captura.md           template do form (cria pendencia em cascata)
├── _seeds/                  notas-stub que alimentam autocomplete (status, etc)
└── <Projeto>/               UM por projeto sob ~/PROJETOS
    ├── <Projeto>.md         hub do projeto (frontmatter + wikilinks)
    ├── Pendencias/<slug>/   cascata: spec.md / task.md / tests.md / resultado.md
    ├── Geral/               conhecimento operacional recorrente
    ├── _root/               notas geradas de arquivos no root do projeto
    ├── _communities/        notas-resumo por cluster do graphify
    ├── _misc/               notas sem source_file claro
    ├── _canvas/
    │   └── graph.canvas     visualizacao do grafo (JSON Canvas)
    └── <subpastas>/         espelham a arvore de codigo do projeto
                             (android/, ios/, src/, docs/, ...)
```

### Por que essas pastas existem

#### `Notas Pendentes/` — legado (deprecated)
Era a INBOX onde captures caiam pra triagem manual posterior. **Deprecated** apos a chegada da cascata: o Modal Form agora pergunta projeto + slug e cria direto `<Projeto>/Pendencias/<slug>/spec.md`. Capturas existentes em `Notas Pendentes/` continuam la ate voce migrar manualmente.

#### `<Projeto>/Pendencias/<slug>/` — cascata acionavel
Cada pendencia e uma **pasta** com ate 4 arquivos: `spec.md`, `task.md`, `tests.md`, `resultado.md`. Estado e definido pela presenca de arquivos (sem campo `status:` pra esquecer). Detalhes na secao "Cascata de pendencias" abaixo.

A regra: se voce ler a nota e nao houver nada pra fazer, nem comecou — entao nem deveria ser pendencia. Mova pra `Geral/`.

#### `<Projeto>/Geral/` — conhecimento operacional
Comandos de deploy memorizados, URLs importantes, decisoes arquiteturais que voce nao quer perder, referencias a secrets em 1Password, paths de keystores, env vars necessarias.

A regra: voce vai consultar isso de novo. Nao tem prazo nem acao.

#### `<Projeto>/_root/` — gerada pelo graphify
Notas auto-geradas a partir de arquivos no root do projeto (README.md, package.json, CLAUDE.md, etc.). Ficam separadas da estrutura espelhada porque o codigo no root nao tem subpasta natural.

#### `<Projeto>/_communities/` — clusters do graphify
Quando o graphify roda Leiden clustering nos nodes, cada community vira uma `_COMMUNITY_<nome>.md` que lista os membros. Util pra ter overview semantico ("toda a parte de Cloud Sync", "tudo relacionado a UI de Settings").

#### `<Projeto>/_misc/` — sem source_file
Notas que o graphify gerou mas nao tem caminho de arquivo claro (conceitos abstratos, rationale puro, etc.). Ficam isoladas pra nao poluir as pastas espelhadas.

#### `<Projeto>/_canvas/graph.canvas`
Arquivo JSON Canvas nativo do Obsidian — abre como **visualizacao interativa do grafo**. Cada projeto tem o seu.

#### `<Projeto>/<subpastas espelhadas>/`
Mirror da arvore do codigo real. Se o projeto tem `android/feature/settings/SettingsModels.kt`, a nota dele vive em `<Projeto>/android/feature/settings/SettingsModels.kt.md`.

Por que? **Quando voce procura por algo no Obsidian, a estrutura mental bate com a do codigo.** Nao precisa traduzir.

### Pastas no nivel raiz (`<root>/`)

#### `Templates/`
Templates do Templater. Por enquanto so tem `Captura.md` (que abre o Modal Form e cria pendencia em cascata em `<Projeto>/Pendencias/<slug>/spec.md`). Voce adiciona mais conforme precisar.

#### `_seeds/`
Notas curtas que existem **so pra alimentar o autocomplete** do Obsidian. Por exemplo: 3 notas com `status: pendente`, `status: feito`, `status: cancelado`. Quando voce clica no campo `status` de qualquer nota, Obsidian sugere essas 3 opcoes.

Voce pode esconder do file explorer com `Settings → Files & Links → Excluded files`.

### Pastas no nivel `~/PROJETOS/<projeto>/`

Cada projeto local tem suas pastas `notes/Pendencias/` e `notes/Geral/` que sao **symlinks pra iCloud**. Isso significa:

```
~/PROJETOS/<Projeto>/
├── (codigo do projeto, intacto)
├── graphify-out/             gerado pelo /graphify (nao versionado)
│   └── obsidian/             vault local do projeto
└── notes/
    ├── Pendencias/  ──→ symlink pra iCloud Drive
    └── Geral/       ──→ symlink pra iCloud Drive
```

A fonte de verdade das notas Pendencias/Geral vive em **iCloud Drive** (`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile/`). Mac e iPhone leem o mesmo arquivo. Two-way sync.

---

## Cascata de pendencias

Cada pendencia vive em `<Projeto>/Pendencias/<slug>/` com ate 4 arquivos:

| Arquivo | Estagio | Conteudo |
|---|---|---|
| `spec.md` | aberta | O que e por que (contexto, problema, criterios) |
| `task.md` | planejamento | Como (passos, dependencias, riscos) |
| `tests.md` | pronta | O que provar (casos de teste em linguagem natural) |
| `resultado.md` | realizada | O que aconteceu (commits, files, decisoes) |

**Estado e definido pela presenca de arquivos** — nao tem campo `status:` pra esquecer.

### Skills

- `/pendencia new <projeto>/<slug>` — cria pasta + spec.md
- `/pendencia next [<slug>]` — avanca pro proximo estagio (gera task / tests / dispara TDD / fecha)
- `/pendencia status [<projeto>]` — lista pendencias por estagio
- `/pendencia migrate <projeto>` — converte `.md` soltos legados
- `/project-new <nome>` — cria projeto novo no vault (so vault, codigo vem depois)

### Captura mobile

O Modal Form de captura agora cria `<Projeto>/Pendencias/<slug>/spec.md` direto (em vez de `Notas Pendentes/`). Pergunta projeto + slug. Slug e normalizado client-side.

### Migracao do formato antigo

Projetos com `<Projeto>/Pendencias/*.md` soltos (formato antigo) sao migrados via `/pendencia migrate <projeto>`. A operacao e idempotente — pode ser feita aos poucos.

---

## Setup

Voce tem duas opcoes:

### A) Setup guiado via Claude Code (recomendado)

```bash
git clone <repo-url> ~/PROJETOS/claude-brain
cd ~/PROJETOS/claude-brain
bash scripts/install-skill.sh
```

Depois, dentro do Claude Code (qualquer diretorio):

```
/claudebrain-init
```

A skill detecta seu estado atual, pergunta antes de cada fase, e aplica so o que voce aprovar. Idempotente — pode rodar de novo depois pra adicionar projetos novos.

Suporta `--dry-run` (mostra o que faria) e `--only 2,3` (roda so fases especificas).

**O que e automatizado:**
- Criacao do vault e copia do template
- Download dos plugins do Obsidian nas versoes pinadas em `plugins.lock.json` (GitHub releases)
- Aplicacao dos configs dos plugins (.example -> data.json)
- Symlinks dos projetos com `graphify-out/`
- Mirror das pastas via `reorganize_vault.py`
- Dropdown do Modal Forms com seus projetos
- Symlinks iCloud por projeto

**O que NAO da pra automatizar (limitacao do Obsidian):**
- "Trust author" dos plugins comunitarios (1 click vault-wide na primeira abertura)
- Toggle do CSS snippet `brain-hub` em Settings -> Aparencia

### B) Setup manual

Veja `docs/SETUP.md` pro passo-a-passo. Resumido:

1. Instalar [graphify](https://github.com/safishamsi/graphify) e gerar o grafo de cada projeto
2. Criar o vault do Obsidian em `~/PROJETOS/Obsidian/ClaudeBrain/`
3. Copiar o conteudo de `vault/` deste repo pra raiz do seu vault
4. Instalar plugins da comunidade: **Dataview**, **Templater**, **Modal Forms**, **Buttons**, **Shell Commands** (Mac), **Meld Encrypt** (opcional)
5. Aplicar configs em `vault/.obsidian/plugins-config/*.json.example` (renomeie pra `data.json` na pasta do plugin)
6. Copiar `scripts/claudebrain-update.sh` pra `~/.local/bin/` e dar permissao executavel
7. Pra cada projeto, rodar `scripts/reorganize_vault.py <projeto/graphify-out/obsidian>` pra espelhar a estrutura
8. Rodar `scripts/init/link_claude_memory.sh <icloud_dir>` pra levar a memoria do Claude Code (`~/.claude/projects/*/memory`) pro iCloud. Em um segundo Mac, o mesmo comando so cria os symlinks pras pastas que ja sincronizaram

---

## Comandos pos-setup

| Comando | O que faz |
|---|---|
| **Cmd+P → Templater: Captura** | abre form, cria pendencia em `<Projeto>/Pendencias/<slug>/spec.md` |
| **Cmd+P → Shell commands: Execute: ClaudeBrain: Atualizar tudo** | detecta projetos novos em `~/PROJETOS`, integra; roda `graphify update` em todos |
| **Botao "Atualizar tudo" no Index** | mesma coisa que acima |
| **Botao "Nova captura" no Index** | mesma coisa que Templater Captura |
| **`/pendencia next [<slug>]`** | avanca pendencia no proximo estagio (no Claude Code) |
| **`/pendencia status [<projeto>]`** | lista pendencias por estagio |
| **`/pendencia migrate <projeto>`** | converte `.md` soltos legados pra cascata |
| **`/project-new <nome>`** | bootstrap vault-only de projeto novo |

---

## Filosofia: captura -> cascata

Inspirado no PARA do Tiago Forte + na "LLM Wiki" do Karpathy + TDD:

1. **Captura** (mobile ou Mac): Modal Form pergunta projeto + slug + descricao. Cria `<Projeto>/Pendencias/<slug>/spec.md` direto. Decisao minima na hora — slug e projeto.
2. **Refinamento via cascata**: `/pendencia next <slug>` gera `task.md` (passos), depois `tests.md` (casos de teste em linguagem natural), depois dispara TDD no codigo real, depois fecha com `resultado.md`.
3. **Revisitar**: Index mostra pendencias por estagio (aberta / planejamento / pronta / realizada). Filtra por projeto.
4. **Processamento**: `claudebrain-update.sh` re-roda graphify pra incorporar tudo no grafo.

Resultado: voce captura rapido, decide profundidade depois, e cada pendencia carrega rastreio uniforme do "o que queria" ate "o que entregou".

---

## Memoria / contexto pro Claude Code

Quatro lugares ortogonais, sem overlap:

| Lugar | Papel | Auto-carrega? |
|---|---|---|
| `~/.claude/CLAUDE.md` | Convencoes globais (todos os projetos) | Sim, sempre |
| `<projeto>/CLAUDE.md` | Convencoes do projeto + decisao "onde poe?" | Sim, quando CWD=projeto |
| `<projeto>/notes/Geral/` | Conhecimento operacional (comandos, decisoes, URLs) | Nao (Claude le on-demand) |
| `~/.claude/projects/<encoded>/memory/` | `session_*.md` (gerado por `/save-session`) + feedback cross-projeto. Symlink pra `<iCloud>/_claude-memory/<encoded>/`, sincroniza entre Macs (`scripts/init/link_claude_memory.sh`) | `MEMORY.md` sim |

A regra **onde colocar coisa nova** vive embutida no `<projeto>/CLAUDE.md` (veja exemplo em `CLAUDE.md` na raiz deste repo). Isso elimina a duvida "memory/ ou notes/Geral/?".

Piloto rodando neste repo. Skill `/claude-md-init` pra rollout em outros projetos esta como decisao adiada.

---

## Compatibilidade

- **Obsidian 1.5+** (Mac, Windows, Linux, iOS, Android)
- **macOS** pra usar o `claudebrain-update.sh` (Shell Commands plugin so funciona em desktop)
- **iCloud Drive** pro sync mobile (alternativas: Obsidian Sync $4/mes, Syncthing gratuito)
- **Python 3.10+** pros scripts auxiliares

---

## Licenca

MIT — ver `LICENSE`.

---

## Disclaimer

Este e um **template de setup pessoal** que funciona pra mim. Pode nao ser ideal pra voce. Adapte livremente. Issues e PRs sao bem-vindos mas nao garanto manutencao ativa.
