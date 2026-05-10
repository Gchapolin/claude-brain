# ClaudeBrain

Setup de Obsidian opinionado pra usar como **segundo cerebro de desenvolvimento** quando voce tem multiplos projetos de codigo localmente. Combina:

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
├── Index.md                 hub central — KPIs, projetos, captures
├── Capturar.md              pagina-form pra criar nota nova
├── Notas Pendentes/         INBOX — captures aguardando triagem
├── Templates/
│   └── Captura.md           template do form (DataviewJS + Modal Forms)
├── _seeds/                  notas-stub que alimentam autocomplete (status, etc)
└── <Projeto>/               UM por projeto sob ~/PROJETOS
    ├── <Projeto>.md         hub do projeto (frontmatter + wikilinks)
    ├── Pendencias/          itens acionaveis nao-resolvidos
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

#### `Notas Pendentes/` — INBOX
Quando voce captura uma ideia rapida (botao "Nova captura" no Index, ou Cmd+P → Templater), a nota cai aqui. **Nunca diretamente num projeto.** Isso evita decisoes prematuras: voce captura agora, decide depois onde ela mora.

A nota tem `status: pendente` no frontmatter. Quando voce processar (triar) — move pra `Pendencias/` ou `Geral/` do projeto correspondente, ou deleta.

#### `<Projeto>/Pendencias/` — items acionaveis
Bugs conhecidos, TODOs, decisoes a tomar, configuracoes manuais a fazer. Tudo o que demanda **acao futura**. Aqui voce escreve a mao (depois de triagem ou direto pro projeto).

A regra: se voce ler a nota e nao houver nada pra fazer, ela nao pertence aqui — pertence a `Geral/`.

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
Templates do Templater. Por enquanto so tem `Captura.md` (que abre o Modal Form e cria nota em `Notas Pendentes/`). Voce adiciona mais conforme precisar.

#### `_seeds/`
Notas curtas que existem **so pra alimentar o autocomplete** do Obsidian. Por exemplo: 3 notas com `status: pendente`, `status: feito`, `status: cancelado`. Quando voce clica no campo `status` de qualquer nota, Obsidian sugere essas 3 opcoes.

Voce pode esconder do file explorer com `Settings → Files & Links → Excluded files`.

### Pastas no nivel `~/PROJETOS/<projeto>/`

Cada projeto local tem sua pasta `notes/Pendencias/` e `notes/Geral/` que sao **symlinks pra iCloud**. Isso significa:

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

## Setup

Veja `docs/SETUP.md` pro passo-a-passo. Resumido:

1. Instalar [graphify](https://github.com/safishamsi/graphify) e gerar o grafo de cada projeto
2. Criar o vault do Obsidian em `~/PROJETOS/Obsidian/ClaudeBrain/`
3. Copiar o conteudo de `vault/` deste repo pra raiz do seu vault
4. Instalar plugins community: **Dataview**, **Templater**, **Modal Forms**, **Buttons**, **Shell Commands** (Mac), **Meld Encrypt** (opcional)
5. Aplicar configs em `vault/.obsidian/plugins-config/*.json.example` (renomeie pra `data.json` no folder do plugin)
6. Copiar `scripts/claudebrain-update.sh` pra `~/.local/bin/` e dar permissao executavel
7. Pra cada projeto, rodar `scripts/reorganize_vault.py <projeto/graphify-out/obsidian>` pra mirror da estrutura

---

## Comandos pos-setup

| Comando | O que faz |
|---|---|
| **Cmd+P → Templater: Captura** | abre form, cria nota em `Notas Pendentes/` |
| **Cmd+P → Shell commands: Execute: ClaudeBrain: Atualizar tudo** | detecta projetos novos em `~/PROJETOS`, integra; roda `graphify update` em todos |
| **Botao "Atualizar tudo" no Index** | mesma coisa que acima |
| **Botao "Nova captura" no Index** | mesma coisa que Templater Captura |

---

## Filosofia de captura → triagem

Inspirado em Tiago Forte's PARA + Karpathy's "LLM Wiki":

1. **Captura**: rapido, sem decidir onde fica. Nota cai em `Notas Pendentes/` com `status: pendente`.
2. **Revisao**: voltando pro Mac, voce abre o Index → tab "Notas Pendentes" → triagem nota a nota.
3. **Decisao binaria**: ou move pra `<projeto>/Pendencias/` (acionavel) ou `<projeto>/Geral/` (referencia), ou deleta.
4. **Processamento**: o `claudebrain-update.sh` re-roda o graphify pra incorporar tudo no grafo.

Resultado: voce nao decide na hora. Captura sempre. Decide quando esta com a cabeca pra isso.

---

## Compatibilidade

- **Obsidian 1.5+** (Mac, Windows, Linux, iOS, Android)
- **macOS** pra usar o `claudebrain-update.sh` (Shell Commands plugin so funciona em desktop)
- **iCloud Drive** pro sync mobile (alternativas: Obsidian Sync $4/mes, Syncthing free)
- **Python 3.10+** pros scripts auxiliares

---

## Licenca

MIT — ver `LICENSE`.

---

## Disclaimer

Este e um **template de setup pessoal** que funciona pra mim. Pode nao ser ideal pra voce. Adapta livremente. Issues e PRs sao bem-vindos mas nao garanto manutencao ativa.
