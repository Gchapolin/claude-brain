---
name: pendencia
description: "Gerencia o ciclo de vida de pendencias do ClaudeBrain como cascata spec -> task -> tests -> resultado. Subcomandos: new, next, status, migrate, from-geral."
trigger: /pendencia
---

# /pendencia

Skill que orquestra o lifecycle de pendencias no vault ClaudeBrain. Cada pendencia vive em `<Projeto>/Pendencias/<slug>/` com 4 arquivos: `spec.md`, `task.md`, `tests.md`, `resultado.md`. Estado e definido por presenca de arquivos — disco e fonte de verdade.

## Usage

```
/pendencia new <projeto>/<slug> [--quick]      # cria pasta e gera spec.md
/pendencia next [<slug>]                       # avanca para o proximo estagio
/pendencia status [<projeto>]                  # lista pendencias por estagio
/pendencia migrate <projeto>                   # converte .md soltos legados
/pendencia from-geral <projeto>/<arquivo>      # promove nota de Geral/ pra cascata
```

## Filosofia

- **Estado por disco**: nada de `status:` em frontmatter pra esquecer. A pasta da pendencia DIZ o estagio.
- **Cascata explicita**: cada estagio depende do anterior. Pular estagios e erro.
- **Anuncia antes de agir**: `/pendencia next` sempre diz o que vai fazer antes de fazer.
- **Idempotente**: rodar 2x e seguro.

## Step 0 — Resolve repo path

Leia `~/.claude/skills/pendencia/.repo-path`. Esse arquivo contem o path absoluto do clone do repo `claude-brain`. Guarde como `$REPO`.

Se nao existir: avise o usuario e pare. Sugira `bash scripts/install-pendencia.sh`.

## Step 1 — Parse subcomando

Primeira palavra apos `/pendencia` define o verbo: `new`, `next`, `status`, `migrate`, `from-geral`. Se ausente ou desconhecido: peca esclarecimento. NUNCA invente.

---

## Subcomando: new

`/pendencia new <projeto>/<slug> [--quick]`

### Validar input

1. Parse `<projeto>/<slug>`. Se faltar `/`, peca.
2. Normalize slug via:
   ```bash
   python3 -c "import sys; sys.path.insert(0, '$REPO/scripts'); from pendencia.slug import normalize; print(normalize('$RAW_SLUG'))"
   ```
3. Confirme projeto existe no vault. Caminho do vault: prefira o que o usuario configurou; senao default `~/PROJETOS/Obsidian/ClaudeBrain/`. Se nao existir: ofereca `/project new <projeto>`.

### Resolver conflito de slug

```bash
python3 -c "import sys; sys.path.insert(0, '$REPO/scripts'); from pendencia.slug import resolve_conflict; from pathlib import Path; print(resolve_conflict(Path('$VAULT/$PROJECT/Pendencias'), '$SLUG'))"
```
Avisa o usuario se o slug original ja existia.

### Gerar spec.md

1. Pergunte ao usuario uma descricao curta da pendencia (1-3 frases) — a menos que o usuario ja tenha colado contexto suficiente.
2. Leia o template: `$REPO/scripts/pendencia/templates/spec.md.tpl`.
3. Substitua placeholders: `{{PROJECT}}`, `{{SLUG}}`, `{{DATE}}` (hoje, formato YYYY-MM-DD), `{{TITLE}}` (derive do conteudo), `{{CONTEXT}}` (use a descricao do usuario), `{{NOTES}}` (vazio).
4. Crie `<Projeto>/Pendencias/<slug>/spec.md`.
5. Anuncie: "Spec criada em `<Projeto>/Pendencias/<slug>/spec.md`. Abra no Obsidian pra editar. Rode `/pendencia next <slug>` quando estiver pronto."

### Modo --quick

Quando `--quick` e passado, NAO geramos task/tests/implementacao. Criamos so `spec.md` + `resultado.md` direto (1-line log). Util pra pendencias triviais. Pergunte: "Descreva em 1 frase o que voce fez/quer registrar."

---

## Subcomando: next

`/pendencia next [<slug>]`

### Determinar a pendencia alvo

1. Se `<slug>` foi passado: localize `<Projeto>/Pendencias/<slug>/`. Se nao achar e CWD esta dentro de `~/PROJETOS/<algo>`, use esse projeto. Senao peca o projeto.
2. Se `<slug>` ausente: rode `classify_project_pendencias` em todos os projetos do vault e mostre as nao-realizadas. Peca pro usuario escolher.

### Inspecionar estado

```bash
python3 -c "import sys; sys.path.insert(0, '$REPO/scripts'); from pendencia.classify import classify_pendencia, next_stage; from pathlib import Path; p = Path('$PENDENCIA_DIR'); print(classify_pendencia(p)); print(next_stage(p))"
```

### Acao por estado

| `next_stage()` retorna | Acao |
|---|---|
| `task` | Le `spec.md`, gera `task.md` a partir do template + LLM. Anuncia "Vou gerar task.md a partir do spec — ok?" antes. |
| `tests` | Le `spec.md` + `task.md`, gera `tests.md`. Mesmo padrao de confirmacao. |
| `implement` | Invoca skill `superpowers:test-driven-development` passando `tests.md` como input + path do codigo do projeto (`~/PROJETOS/<projeto>/`). |
| `done` | Avisa "Pendencia ja realizada. Reabrir significa apagar `resultado.md`. Quer fazer isso?" |

### Gerar resultado.md (apos implementacao)

Quando o estado e `pronta` mas `tests.md` ja foi processado (presenca de commits relacionados desde o `created` em `tests.md`), perguntar ao usuario se a implementacao terminou. Se sim:

1. `git -C ~/PROJETOS/<projeto> log --since="<tests.md created>" --oneline` — lista commits.
2. `git -C ~/PROJETOS/<projeto> diff --name-only <range>` — lista files alterados.
3. Le `$REPO/scripts/pendencia/templates/resultado.md.tpl`, substitui placeholders.
4. Pergunta: "Tem session salva via `/save-session`? Quer linkar?" — usa wikilink.
5. Cria `resultado.md`.
6. Anuncia: "Pendencia `<slug>` realizada. Estado: realizada."

---

## Subcomando: status

`/pendencia status [<projeto>]`

```bash
python3 -c "
import sys
sys.path.insert(0, '$REPO/scripts')
from pendencia.classify import classify_project_pendencias, count_legado
from pathlib import Path
VAULT = Path('$VAULT')
for proj in sorted(VAULT.iterdir()):
    if not proj.is_dir() or proj.name.startswith('_') or proj.name.startswith('.'):
        continue
    p = proj / 'Pendencias'
    if not p.is_dir():
        continue
    cls = classify_project_pendencias(p)
    legado = count_legado(p)
    if cls or legado:
        print(f'{proj.name}: {cls} legado={legado}')
"
```

Formate a saida como tabela legivel agrupando por projeto e por estagio.

---

## Subcomando: migrate

`/pendencia migrate <projeto>`

1. `plan = plan_migration(<Projeto>/Pendencias, project=<projeto>)`
2. Imprima o plano: cada item mostra `source -> target`. Pergunte: "Aplicar?".
3. Se sim: `apply(plan, ..., dry_run=False)`.
4. Anuncie quantas migrou.

Suporta `--dry-run`: mostra o plano e nao escreve.

---

## Subcomando: from-geral

`/pendencia from-geral <projeto>/<arquivo>`

1. Localize `<Projeto>/Geral/<arquivo>`.
2. Pergunte slug (sugira normalizado).
3. Mova o conteudo pra `<Projeto>/Pendencias/<slug>/spec.md`.
4. Substitua frontmatter pelo da pendencia.
5. Delete o original em `Geral/`.

---

## Casos de falha

- **Estado invalido** (ex: `task.md` sem `spec.md`): pare e mostre o que falta. Sugira `/pendencia new <projeto>/<slug>` pra recomecar.
- **Slug com so chars invalidos**: peca novo slug.
- **Projeto nao existe**: ofereca `/project new`.
- **`tests.md` vazio** ao tentar invocar TDD: pare e peca revisao.
- **Sem commits desde `tests.md`** ao gerar `resultado.md`: pergunte se quer escrever resultado manualmente ou abortar.

## Convencoes

- Sem acentos em slugs (normalizado automaticamente).
- Datas no formato `YYYY-MM-DD`.
- Wikilinks entre arquivos da mesma pendencia: `[[spec]]`, `[[task]]`, `[[tests]]`.
- Quando o repo do vault for git, commitar cada estagio com mensagem `pendencia(<slug>): <stage>`.
