# Cascata de pendencias + project init Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Padronizar pendencias do ClaudeBrain como cascata `spec/task/tests/resultado` (pasta por pendencia), com skill `/pendencia` orquestrando geracao+TDD, skill `/project new` pra bootstrap vault-only de projetos novos, e migracao do legado (Notas Pendentes + .md soltos).

**Architecture:** Logica pura em Python testavel (classificacao por presenca de arquivos, normalizacao de slug, migracao). Skills `/pendencia` e `/project-new` orquestram via os scripts Python + integracao com `superpowers:test-driven-development`. Modal Form e Index.md atualizados pra escrever/exibir o novo formato. Instalacao via scripts shell idempotentes mirroring o padrao existente (`install-skill.sh`, `install-save-session.sh`).

**Tech Stack:** Python 3.10+ (stdlib only), Bash, Markdown (frontmatter YAML), JavaScript (Templater + Dataviewjs no Obsidian).

---

## File Structure

**New (created in this plan):**
- `scripts/pendencia/__init__.py` — package marker
- `scripts/pendencia/classify.py` — classifica pasta de pendencia por presenca de arquivos
- `scripts/pendencia/slug.py` — normaliza slug (kebab-case, sem acentos, conflito)
- `scripts/pendencia/migrate.py` — converte `.md` soltos em `<Projeto>/Pendencias/` pra `<slug>/spec.md`
- `scripts/pendencia/templates/spec.md.tpl` — template do spec.md
- `scripts/pendencia/templates/task.md.tpl` — template do task.md
- `scripts/pendencia/templates/tests.md.tpl` — template do tests.md
- `scripts/pendencia/templates/resultado.md.tpl` — template do resultado.md
- `scripts/install-pendencia.sh` — instala skill `/pendencia` em `~/.claude/skills/`
- `scripts/install-project-new.sh` — instala skill `/project-new` em `~/.claude/skills/`
- `skills/pendencia/SKILL.md` — definicao da skill
- `skills/project-new/SKILL.md` — definicao da skill
- `tests/test_pendencia_classify.py`
- `tests/test_pendencia_slug.py`
- `tests/test_pendencia_migrate.py`

**Modified:**
- `tests/_helpers.py` — extender pra carregar modulos de `scripts/pendencia/` tambem
- `vault/Templates/Captura.md` — escrever em `<Projeto>/Pendencias/<slug>/spec.md` em vez de `Notas Pendentes/`
- `vault/Index.md` — substituir dataviewjs da tab "Notas Pendentes" pela tabela de pendencias por estagio + banner de migracao
- `skills/claudebrain-init/SKILL.md` — adicionar Fase 9 (instalar skills `/pendencia` e `/project-new`)
- `README.md` — secao nova "Cascata de pendencias"

---

## Task 1: Pendencia classifier (pure logic)

**Files:**
- Create: `scripts/pendencia/__init__.py`
- Create: `scripts/pendencia/classify.py`
- Modify: `tests/_helpers.py:10-11` (add PENDENCIA_DIR)
- Test: `tests/test_pendencia_classify.py`

- [ ] **Step 1: Add helper to load modules from scripts/pendencia/**

Modify `tests/_helpers.py` to support loading both `scripts/init/` and `scripts/pendencia/`:

```python
"""Shared helpers for tests. Loads scripts/{init,pendencia}/*.py as importable modules."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_DIR = REPO_ROOT / "scripts" / "init"
PENDENCIA_DIR = REPO_ROOT / "scripts" / "pendencia"


def _load_from(dir_path: Path, name: str, file_stem: str):
    if name in sys.modules:
        return sys.modules[name]
    path = dir_path / f"{file_stem}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_module(name: str, file_stem: str):
    """Load <file_stem>.py from scripts/init/."""
    return _load_from(INIT_DIR, name, file_stem)


def load_pendencia_module(name: str, file_stem: str):
    """Load <file_stem>.py from scripts/pendencia/."""
    return _load_from(PENDENCIA_DIR, name, file_stem)
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_pendencia_classify.py`:

```python
"""Tests for scripts/pendencia/classify.py — classify by file presence."""

import tempfile
import unittest
from pathlib import Path

from tests._helpers import load_pendencia_module

classify = load_pendencia_module("classify", "classify")


class TestClassify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _touch(self, *names):
        for n in names:
            (self.dir / n).write_text("")

    def test_empty_folder_is_invalid(self):
        self.assertEqual(classify.classify_pendencia(self.dir), "invalid")

    def test_only_spec_is_aberta(self):
        self._touch("spec.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "aberta")

    def test_spec_and_task_is_planejamento(self):
        self._touch("spec.md", "task.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "planejamento")

    def test_spec_task_tests_is_pronta(self):
        self._touch("spec.md", "task.md", "tests.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "pronta")

    def test_all_four_is_realizada(self):
        self._touch("spec.md", "task.md", "tests.md", "resultado.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "realizada")

    def test_task_without_spec_is_invalid(self):
        self._touch("task.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "invalid")

    def test_resultado_without_tests_is_invalid(self):
        self._touch("spec.md", "task.md", "resultado.md")
        self.assertEqual(classify.classify_pendencia(self.dir), "invalid")

    def test_next_stage_aberta_returns_task(self):
        self._touch("spec.md")
        self.assertEqual(classify.next_stage(self.dir), "task")

    def test_next_stage_planejamento_returns_tests(self):
        self._touch("spec.md", "task.md")
        self.assertEqual(classify.next_stage(self.dir), "tests")

    def test_next_stage_pronta_returns_implement(self):
        self._touch("spec.md", "task.md", "tests.md")
        self.assertEqual(classify.next_stage(self.dir), "implement")

    def test_next_stage_realizada_returns_done(self):
        self._touch("spec.md", "task.md", "tests.md", "resultado.md")
        self.assertEqual(classify.next_stage(self.dir), "done")

    def test_next_stage_invalid_raises(self):
        with self.assertRaises(ValueError):
            classify.next_stage(self.dir)

    def test_classify_project_lists_all_pendencias(self):
        # /Projeto/Pendencias/<slug>/ folders
        proj = self.dir / "Pendencias"
        proj.mkdir()
        (proj / "a").mkdir()
        (proj / "a" / "spec.md").write_text("")
        (proj / "b").mkdir()
        (proj / "b" / "spec.md").write_text("")
        (proj / "b" / "task.md").write_text("")
        # Flat .md (legado) — should NOT count as pendencia
        (proj / "legado.md").write_text("")

        result = classify.classify_project_pendencias(proj)
        self.assertEqual(result, {
            "a": "aberta",
            "b": "planejamento",
        })

    def test_classify_project_counts_legado(self):
        proj = self.dir / "Pendencias"
        proj.mkdir()
        (proj / "legado1.md").write_text("")
        (proj / "legado2.md").write_text("")
        (proj / "a").mkdir()
        (proj / "a" / "spec.md").write_text("")

        self.assertEqual(classify.count_legado(proj), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd ~/PROJETOS/claude-brain && python -m unittest tests.test_pendencia_classify -v`
Expected: FAIL with import error (`scripts/pendencia/classify.py` missing).

- [ ] **Step 4: Implement classify.py**

Create `scripts/pendencia/__init__.py` (empty file).

Create `scripts/pendencia/classify.py`:

```python
"""Classify a pendencia folder by which cascade files are present.

The disk is the source of truth: no `status` frontmatter to maintain.

Stages:
    aberta        — only spec.md
    planejamento  — spec.md + task.md
    pronta        — spec.md + task.md + tests.md
    realizada     — all four files
    invalid       — anything else (missing spec, gap in cascade)

next_stage() returns the suffix indicating which file to generate next:
    "task" | "tests" | "implement" | "done"
"""

from __future__ import annotations

from pathlib import Path

STAGES = ("spec.md", "task.md", "tests.md", "resultado.md")


def _present(folder: Path) -> tuple[bool, ...]:
    return tuple((folder / name).is_file() for name in STAGES)


def classify_pendencia(folder: Path) -> str:
    spec, task, tests, resultado = _present(folder)
    if not spec:
        return "invalid"
    if not task:
        return "invalid" if (tests or resultado) else "aberta"
    if not tests:
        return "invalid" if resultado else "planejamento"
    if not resultado:
        return "pronta"
    return "realizada"


def next_stage(folder: Path) -> str:
    """Return the next action: 'task', 'tests', 'implement', or 'done'.

    Raises ValueError on invalid state.
    """
    state = classify_pendencia(folder)
    mapping = {
        "aberta": "task",
        "planejamento": "tests",
        "pronta": "implement",
        "realizada": "done",
    }
    if state not in mapping:
        raise ValueError(f"Pendencia em {folder} esta em estado invalido")
    return mapping[state]


def classify_project_pendencias(pendencias_dir: Path) -> dict[str, str]:
    """For a <Projeto>/Pendencias/ folder, return {slug: stage} for each subdir."""
    result = {}
    if not pendencias_dir.is_dir():
        return result
    for child in sorted(pendencias_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("_"):
            result[child.name] = classify_pendencia(child)
    return result


def count_legado(pendencias_dir: Path) -> int:
    """Count flat .md files in <Projeto>/Pendencias/ (legacy format)."""
    if not pendencias_dir.is_dir():
        return 0
    return sum(1 for f in pendencias_dir.iterdir() if f.is_file() and f.suffix == ".md")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ~/PROJETOS/claude-brain && python -m unittest tests.test_pendencia_classify -v`
Expected: PASS on all 14 tests.

- [ ] **Step 6: Commit**

```bash
git add scripts/pendencia/__init__.py scripts/pendencia/classify.py tests/_helpers.py tests/test_pendencia_classify.py
git commit -m "feat: classifier de pendencia por presenca de arquivos"
```

---

## Task 2: Slug normalization

**Files:**
- Create: `scripts/pendencia/slug.py`
- Test: `tests/test_pendencia_slug.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pendencia_slug.py`:

```python
"""Tests for scripts/pendencia/slug.py — normalize slug + conflict resolution."""

import tempfile
import unittest
from pathlib import Path

from tests._helpers import load_pendencia_module

slug_mod = load_pendencia_module("slug", "slug")


class TestNormalize(unittest.TestCase):
    def test_lowercase(self):
        self.assertEqual(slug_mod.normalize("OauthApple"), "oauthapple")

    def test_spaces_become_dash(self):
        self.assertEqual(slug_mod.normalize("login google"), "login-google")

    def test_accents_stripped(self):
        self.assertEqual(slug_mod.normalize("integracao acores"), "integracao-acores")

    def test_special_chars_removed(self):
        self.assertEqual(slug_mod.normalize("fix bug #42!"), "fix-bug-42")

    def test_collapses_multiple_dashes(self):
        self.assertEqual(slug_mod.normalize("a -- b"), "a-b")

    def test_strips_leading_trailing_dash(self):
        self.assertEqual(slug_mod.normalize("- hello -"), "hello")

    def test_empty_input_raises(self):
        with self.assertRaises(ValueError):
            slug_mod.normalize("")

    def test_only_invalid_chars_raises(self):
        with self.assertRaises(ValueError):
            slug_mod.normalize("!!!")


class TestResolveConflict(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_conflict_returns_same(self):
        self.assertEqual(slug_mod.resolve_conflict(self.dir, "oauth"), "oauth")

    def test_one_conflict_returns_2(self):
        (self.dir / "oauth").mkdir()
        self.assertEqual(slug_mod.resolve_conflict(self.dir, "oauth"), "oauth-2")

    def test_multiple_conflicts_increments(self):
        (self.dir / "oauth").mkdir()
        (self.dir / "oauth-2").mkdir()
        (self.dir / "oauth-3").mkdir()
        self.assertEqual(slug_mod.resolve_conflict(self.dir, "oauth"), "oauth-4")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/PROJETOS/claude-brain && python -m unittest tests.test_pendencia_slug -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement slug.py**

Create `scripts/pendencia/slug.py`:

```python
"""Slug normalization for pendencias.

Rules:
- lowercase, ASCII only (accents stripped)
- non-alphanumeric becomes single dash
- multiple dashes collapsed
- no leading/trailing dashes
- empty/all-invalid raises ValueError

Conflict resolution: append -2, -3, ... when the slug folder already exists.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def normalize(text: str) -> str:
    if not text:
        raise ValueError("slug vazio")

    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    lower = ascii_only.lower()
    replaced = re.sub(r"[^a-z0-9]+", "-", lower)
    stripped = replaced.strip("-")

    if not stripped:
        raise ValueError(f"slug {text!r} virou vazio apos normalizacao")
    return stripped


def resolve_conflict(parent: Path, slug: str) -> str:
    """Return slug as-is if no folder/file with that name exists in parent;
    otherwise append -2, -3, ... until unique."""
    if not (parent / slug).exists():
        return slug
    i = 2
    while (parent / f"{slug}-{i}").exists():
        i += 1
    return f"{slug}-{i}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/PROJETOS/claude-brain && python -m unittest tests.test_pendencia_slug -v`
Expected: PASS on all 11 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/pendencia/slug.py tests/test_pendencia_slug.py
git commit -m "feat: slug normalizer + conflict resolver"
```

---

## Task 3: Templates dos 4 estagios

**Files:**
- Create: `scripts/pendencia/templates/spec.md.tpl`
- Create: `scripts/pendencia/templates/task.md.tpl`
- Create: `scripts/pendencia/templates/tests.md.tpl`
- Create: `scripts/pendencia/templates/resultado.md.tpl`

Templates usam placeholders no formato `{{VAR}}`. A skill substitui antes de escrever.

- [ ] **Step 1: Create spec.md.tpl**

Create `scripts/pendencia/templates/spec.md.tpl`:

```markdown
---
type: pendencia-spec
project: {{PROJECT}}
slug: {{SLUG}}
stage: spec
created: {{DATE}}
updated: {{DATE}}
tags: [pendencia, {{PROJECT}}]
---

# {{TITLE}}

## Contexto
{{CONTEXT}}

## Problema
Descreva o problema em 1-3 frases. O que esta acontecendo (ou nao acontecendo) que precisa mudar?

## Criterios de aceitacao
- [ ] Criterio 1
- [ ] Criterio 2

## Fora de escopo
- O que NAO sera feito nesta pendencia (evita scope creep)

## Notas
{{NOTES}}
```

- [ ] **Step 2: Create task.md.tpl**

Create `scripts/pendencia/templates/task.md.tpl`:

```markdown
---
type: pendencia-task
project: {{PROJECT}}
slug: {{SLUG}}
stage: task
created: {{DATE}}
updated: {{DATE}}
spec: "[[spec]]"
---

# Task: {{TITLE}}

## Passos concretos
1. Passo 1 (arquivo/area especifica)
2. Passo 2
3. Passo 3

## Dependencias
- Libs, APIs, contas externas, decisoes upstream

## Riscos
- Risco 1 e como mitigar
- Risco 2

## Estimativa
{{ESTIMATE}}

## Decisoes tomadas
- (preencher conforme planejamento avanca)
```

- [ ] **Step 3: Create tests.md.tpl**

Create `scripts/pendencia/templates/tests.md.tpl`:

```markdown
---
type: pendencia-tests
project: {{PROJECT}}
slug: {{SLUG}}
stage: tests
created: {{DATE}}
updated: {{DATE}}
spec: "[[spec]]"
task: "[[task]]"
---

# Spec de testes: {{TITLE}}

## Fluxo feliz
1. Setup
2. Acao
3. Verificacao
4. Resultado esperado

## Edge cases
- Caso 1: descricao + esperado
- Caso 2: descricao + esperado

## Falhas esperadas
- Quando X falha, esperar Y

## Nao testar (escopo)
- O que esta fora desta pendencia

## Notas para implementacao
- Hints sobre stack, libs, frameworks de teste a usar
```

- [ ] **Step 4: Create resultado.md.tpl**

Create `scripts/pendencia/templates/resultado.md.tpl`:

```markdown
---
type: pendencia-resultado
project: {{PROJECT}}
slug: {{SLUG}}
stage: resultado
created: {{DATE}}
updated: {{DATE}}
spec: "[[spec]]"
task: "[[task]]"
tests: "[[tests]]"
session: "{{SESSION_LINK}}"
---

# Resultado: {{TITLE}}

## O que foi feito
{{SUMMARY}}

## Commits
{{COMMITS}}

## Arquivos alterados
{{FILES}}

## Decisoes durante implementacao
- Decisao 1 (por que)
- Decisao 2

## Follow-ups
- Pendencia futura: [[outro-slug]]
- TODOs deixados no codigo

## Como testar manualmente
1. Passo
2. Passo
```

- [ ] **Step 5: Commit**

```bash
git add scripts/pendencia/templates/
git commit -m "feat: templates dos 4 estagios da cascata"
```

---

## Task 4: Migration script (legado .md -> pasta/spec.md)

**Files:**
- Create: `scripts/pendencia/migrate.py`
- Test: `tests/test_pendencia_migrate.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pendencia_migrate.py`:

```python
"""Tests for scripts/pendencia/migrate.py — convert legacy .md to folder/spec.md."""

import tempfile
import unittest
from pathlib import Path

from tests._helpers import load_pendencia_module

migrate = load_pendencia_module("migrate", "migrate")


class TestMigrate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pendencias = Path(self.tmp.name) / "Pendencias"
        self.pendencias.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_plan_lists_legado_files(self):
        (self.pendencias / "login-google.md").write_text("conteudo")
        (self.pendencias / "fix-bug.md").write_text("outro")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        slugs = sorted(item["slug"] for item in plan)
        self.assertEqual(slugs, ["fix-bug", "login-google"])

    def test_plan_normalizes_slug(self):
        (self.pendencias / "Login Google.md").write_text("x")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        self.assertEqual(plan[0]["slug"], "login-google")

    def test_plan_ignores_existing_folders(self):
        (self.pendencias / "already-migrated").mkdir()
        (self.pendencias / "already-migrated" / "spec.md").write_text("x")
        (self.pendencias / "loose.md").write_text("y")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["slug"], "loose")

    def test_plan_resolves_conflicts(self):
        (self.pendencias / "dup").mkdir()
        (self.pendencias / "dup.md").write_text("x")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        self.assertEqual(plan[0]["slug"], "dup-2")

    def test_apply_moves_content_into_spec(self):
        (self.pendencias / "fix.md").write_text("conteudo original\n")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan, self.pendencias)
        spec_path = self.pendencias / "fix" / "spec.md"
        self.assertTrue(spec_path.is_file())
        content = spec_path.read_text()
        self.assertIn("conteudo original", content)
        self.assertIn("type: pendencia-spec", content)
        self.assertIn("project: HMA", content)
        self.assertIn("slug: fix", content)

    def test_apply_removes_original_after_move(self):
        (self.pendencias / "fix.md").write_text("x")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan, self.pendencias)
        self.assertFalse((self.pendencias / "fix.md").exists())

    def test_apply_preserves_existing_frontmatter_body(self):
        original = "---\nstatus: pendente\ntags: [old]\n---\n\n# Old title\n\nbody text\n"
        (self.pendencias / "old.md").write_text(original)
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan, self.pendencias)
        spec = (self.pendencias / "old" / "spec.md").read_text()
        # New frontmatter present
        self.assertIn("type: pendencia-spec", spec)
        # Old body preserved (incl old title)
        self.assertIn("# Old title", spec)
        self.assertIn("body text", spec)
        # Old frontmatter dropped — we replace it, not nest it
        self.assertNotIn("status: pendente", spec)

    def test_apply_is_idempotent_skipping_existing(self):
        (self.pendencias / "a.md").write_text("x")
        plan1 = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan1, self.pendencias)
        # Second run: no .md left, plan empty
        plan2 = migrate.plan_migration(self.pendencias, project="HMA")
        self.assertEqual(plan2, [])

    def test_apply_dry_run_writes_nothing(self):
        (self.pendencias / "x.md").write_text("body")
        plan = migrate.plan_migration(self.pendencias, project="HMA")
        migrate.apply(plan, self.pendencias, dry_run=True)
        self.assertTrue((self.pendencias / "x.md").exists())
        self.assertFalse((self.pendencias / "x").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/PROJETOS/claude-brain && python -m unittest tests.test_pendencia_migrate -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement migrate.py**

Create `scripts/pendencia/migrate.py`:

```python
"""Migrate legacy <Projeto>/Pendencias/*.md (flat) to <slug>/spec.md (cascade).

Two-phase:
    plan_migration(pendencias_dir, project) -> list of dicts
    apply(plan, pendencias_dir, dry_run=False)

Idempotent: only flat .md files (not subfolders) are considered.
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import TypedDict

from . import slug as slug_mod  # type: ignore[import-not-found]


class Migration(TypedDict):
    source: str
    slug: str
    target_dir: str
    target_file: str


def plan_migration(pendencias_dir: Path, project: str) -> list[Migration]:
    """List flat .md files in pendencias_dir and propose a migration plan.

    Returns sorted by source filename. Slugs are normalized + conflict-resolved
    against the current pendencias_dir state.
    """
    if not pendencias_dir.is_dir():
        return []

    plan: list[Migration] = []
    used_slugs: set[str] = set()

    for entry in sorted(pendencias_dir.iterdir()):
        if not entry.is_file() or entry.suffix != ".md":
            continue
        stem = entry.stem
        try:
            base_slug = slug_mod.normalize(stem)
        except ValueError:
            continue

        # Resolve against disk + slugs already chosen in this plan
        candidate = base_slug
        i = 2
        while (pendencias_dir / candidate).exists() or candidate in used_slugs:
            candidate = f"{base_slug}-{i}"
            i += 1
        used_slugs.add(candidate)

        plan.append(Migration(
            source=str(entry),
            slug=candidate,
            target_dir=str(pendencias_dir / candidate),
            target_file=str(pendencias_dir / candidate / "spec.md"),
        ))
    return plan


_FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n\r?\n?", re.DOTALL)


def _strip_existing_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _new_frontmatter(project: str, slug: str, date: str) -> str:
    return (
        "---\n"
        f"type: pendencia-spec\n"
        f"project: {project}\n"
        f"slug: {slug}\n"
        f"stage: spec\n"
        f"created: {date}\n"
        f"updated: {date}\n"
        f"tags: [pendencia, {project}, migrated]\n"
        "---\n\n"
    )


def apply(plan: list[Migration], pendencias_dir: Path, dry_run: bool = False) -> None:
    """Execute the migration plan. Reads each source, writes target_file, deletes source.

    Skips entries whose target already exists (idempotent re-run safety).
    """
    project = _infer_project_from_plan(plan, pendencias_dir)
    today = _dt.date.today().isoformat()

    for item in plan:
        src = Path(item["source"])
        target_dir = Path(item["target_dir"])
        target_file = Path(item["target_file"])

        if target_file.exists():
            continue  # already migrated

        body = src.read_text(encoding="utf-8")
        body_no_fm = _strip_existing_frontmatter(body).lstrip("\n")
        new_text = _new_frontmatter(project, item["slug"], today) + body_no_fm

        if dry_run:
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(new_text, encoding="utf-8")
        src.unlink()


def _infer_project_from_plan(plan: list[Migration], pendencias_dir: Path) -> str:
    """Project name = parent folder of pendencias_dir."""
    if not plan:
        return pendencias_dir.parent.name
    return pendencias_dir.parent.name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/PROJETOS/claude-brain && python -m unittest tests.test_pendencia_migrate -v`
Expected: PASS on all 9 tests.

Note: tests pass `project="HMA"` explicitly because the helper folder structure is `<tmp>/Pendencias/`. The function uses `pendencias_dir.parent.name` (which is the temp dir name) but accepts an explicit override path in tests via the param signature.

Wait — re-read: tests call `migrate.plan_migration(self.pendencias, project="HMA")` and `migrate.apply(plan, self.pendencias)`. The `project` param is on `plan_migration` but the spec data is written by `apply`. Adjust:

Modify `apply()` signature to accept project explicitly so tests work:

```python
def apply(plan: list[Migration], pendencias_dir: Path, project: str | None = None, dry_run: bool = False) -> None:
    if project is None:
        project = pendencias_dir.parent.name
    today = _dt.date.today().isoformat()
    for item in plan:
        ...
```

And adjust `plan_migration` to embed project into each Migration dict so `apply` can recover it:

```python
class Migration(TypedDict):
    source: str
    slug: str
    target_dir: str
    target_file: str
    project: str

# in plan_migration:
plan.append(Migration(
    source=str(entry),
    slug=candidate,
    target_dir=str(pendencias_dir / candidate),
    target_file=str(pendencias_dir / candidate / "spec.md"),
    project=project,
))
```

And update `apply()` to use `item["project"]` instead of inferring. Drop `_infer_project_from_plan`.

After this adjustment, re-run tests. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/pendencia/migrate.py tests/test_pendencia_migrate.py
git commit -m "feat: migracao de Pendencias .md soltos pra cascata"
```

---

## Task 5: Install scripts for both skills

**Files:**
- Create: `scripts/install-pendencia.sh`
- Create: `scripts/install-project-new.sh`

Esses scripts seguem o padrao de `scripts/install-skill.sh` (symlink + `.repo-path`).

- [ ] **Step 1: Create install-pendencia.sh**

Create `scripts/install-pendencia.sh`:

```bash
#!/usr/bin/env bash
# Installs the /pendencia skill into ~/.claude/skills/.
#
# Usage: bash scripts/install-pendencia.sh
#
# What it does:
#   1. Symlinks <repo>/skills/pendencia/SKILL.md -> ~/.claude/skills/pendencia/SKILL.md
#   2. Writes <repo> absolute path into ~/.claude/skills/pendencia/.repo-path
#      (the skill reads this to find scripts/pendencia/ helpers)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SRC="$REPO_ROOT/skills/pendencia/SKILL.md"
SKILL_DST_DIR="$HOME/.claude/skills/pendencia"
SKILL_DST="$SKILL_DST_DIR/SKILL.md"
REPO_PATH_FILE="$SKILL_DST_DIR/.repo-path"

if [ ! -f "$SKILL_SRC" ]; then
    echo "ERRO: SKILL.md nao encontrado em $SKILL_SRC" >&2
    exit 1
fi

mkdir -p "$SKILL_DST_DIR"

if [ -e "$SKILL_DST" ] || [ -L "$SKILL_DST" ]; then
    if [ -d "$SKILL_DST" ] && [ ! -L "$SKILL_DST" ]; then
        echo "ERRO: $SKILL_DST e diretorio real (nao symlink). Remova manualmente." >&2
        exit 1
    fi
    echo "Removendo install anterior: $SKILL_DST"
    rm -f "$SKILL_DST"
fi

ln -s "$SKILL_SRC" "$SKILL_DST"
echo "$REPO_ROOT" > "$REPO_PATH_FILE"

echo
echo "OK Skill /pendencia instalado."
echo "   Skill:     $SKILL_DST -> $SKILL_SRC"
echo "   Repo path: $REPO_PATH_FILE ($REPO_ROOT)"
```

Make executable: `chmod +x scripts/install-pendencia.sh`

- [ ] **Step 2: Create install-project-new.sh**

Create `scripts/install-project-new.sh` (identical to install-pendencia.sh but for `project-new`):

```bash
#!/usr/bin/env bash
# Installs the /project-new skill into ~/.claude/skills/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SRC="$REPO_ROOT/skills/project-new/SKILL.md"
SKILL_DST_DIR="$HOME/.claude/skills/project-new"
SKILL_DST="$SKILL_DST_DIR/SKILL.md"
REPO_PATH_FILE="$SKILL_DST_DIR/.repo-path"

if [ ! -f "$SKILL_SRC" ]; then
    echo "ERRO: SKILL.md nao encontrado em $SKILL_SRC" >&2
    exit 1
fi

mkdir -p "$SKILL_DST_DIR"

if [ -e "$SKILL_DST" ] || [ -L "$SKILL_DST" ]; then
    if [ -d "$SKILL_DST" ] && [ ! -L "$SKILL_DST" ]; then
        echo "ERRO: $SKILL_DST e diretorio real (nao symlink). Remova manualmente." >&2
        exit 1
    fi
    echo "Removendo install anterior: $SKILL_DST"
    rm -f "$SKILL_DST"
fi

ln -s "$SKILL_SRC" "$SKILL_DST"
echo "$REPO_ROOT" > "$REPO_PATH_FILE"

echo
echo "OK Skill /project-new instalado."
echo "   Skill:     $SKILL_DST -> $SKILL_SRC"
echo "   Repo path: $REPO_PATH_FILE ($REPO_ROOT)"
```

Make executable: `chmod +x scripts/install-project-new.sh`

- [ ] **Step 3: Verify scripts are syntactically valid**

Run: `bash -n scripts/install-pendencia.sh && bash -n scripts/install-project-new.sh && echo OK`
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add scripts/install-pendencia.sh scripts/install-project-new.sh
git commit -m "feat: install scripts pras skills /pendencia e /project-new"
```

---

## Task 6: Skill `/pendencia` definition

**Files:**
- Create: `skills/pendencia/SKILL.md`

A skill define o comportamento. Nao tem teste de unidade tradicional (e prompt pro modelo), mas o conteudo precisa ser parseavel (frontmatter YAML valido) e referenciar os scripts/templates corretos.

- [ ] **Step 1: Write SKILL.md**

Create `skills/pendencia/SKILL.md`:

````markdown
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
````

- [ ] **Step 2: Validate frontmatter YAML**

Run: `python3 -c "import yaml; print(yaml.safe_load(open('skills/pendencia/SKILL.md').read().split('---')[1]))"`
Expected: prints a dict containing `name`, `description`, `trigger` keys without raising.

- [ ] **Step 3: Commit**

```bash
git add skills/pendencia/SKILL.md
git commit -m "feat: skill /pendencia com 5 subcomandos"
```

---

## Task 7: Skill `/project-new` definition

**Files:**
- Create: `skills/project-new/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `skills/project-new/SKILL.md`:

````markdown
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
````

- [ ] **Step 2: Validate frontmatter YAML**

Run: `python3 -c "import yaml; print(yaml.safe_load(open('skills/project-new/SKILL.md').read().split('---')[1]))"`
Expected: dict containing name/description/trigger keys.

- [ ] **Step 3: Commit**

```bash
git add skills/project-new/SKILL.md
git commit -m "feat: skill /project-new bootstrap vault-only"
```

---

## Task 8: Update Captura.md (Modal Form) pra escrever em Pendencias/<slug>/spec.md

**Files:**
- Modify: `vault/Templates/Captura.md`

A captura mobile passa a criar `<Projeto>/Pendencias/<slug>/spec.md` em vez de `Notas Pendentes/`. Adiciona campo `slug` no form.

- [ ] **Step 1: Read current Captura.md**

Already shown in plan context. Current form fields: `projeto`, `titulo`, `conteudo`, `tags`. Need to add `slug`.

- [ ] **Step 2: Replace Captura.md content**

Replace `vault/Templates/Captura.md` with:

```javascript
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

// Normalize slug client-side: lowercase, ASCII, dashes for non-alnum
const stripAccents = s => s.normalize("NFKD").replace(/[̀-ͯ]/g, "");
let slug = stripAccents(slugRaw).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
if (!slug) {
    new Notice("Captura abortada: slug invalido.");
    return;
}

// Resolve conflict: append -2, -3 if folder exists
let candidate = slug;
let i = 2;
while (app.vault.getAbstractFileByPath(`${projeto}/Pendencias/${candidate}`)) {
    candidate = `${slug}-${i}`;
    i += 1;
}
slug = candidate;

const date = tp.date.now("YYYY-MM-DD");
const time = tp.date.now("HH:mm");
const folderpath = `${projeto}/Pendencias/${slug}`;
const filepath = `${folderpath}/spec.md`;

// Ensure folder exists
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
```

- [ ] **Step 3: Check the Modal Form definition includes `slug` field**

Read `vault/.obsidian/plugins-config/modalforms.json.example` (or wherever the form schema lives). Look for the `capturar-nota` form definition.

```bash
grep -l "capturar-nota" vault/.obsidian/plugins-config/ 2>/dev/null || find vault/.obsidian -name "*.json*"
```

If the form definition exists in this repo and lacks a `slug` field, add one. If the form is config that the user maintains manually, leave a note in README about the new field.

For this plan: add a `slug` field to the form schema if a schema file exists in the repo. If not, document in README.

```bash
# Run the grep above and look at the file. Add a field block like:
# {
#   "name": "slug",
#   "label": "Slug (opcional — derivado do titulo se vazio)",
#   "input": {"type": "text"}
# }
```

- [ ] **Step 4: Manual verification (cannot fully test in CLI)**

Since this is a Templater + Modal Forms script that runs inside Obsidian, syntax-check via Node:

```bash
node -e "const s = require('fs').readFileSync('vault/Templates/Captura.md', 'utf8'); const js = s.replace(/<%\*|\%>/g, ''); new Function('app','tp','Notice', js); console.log('OK')"
```

Expected: `OK` (parses as valid JS function body).

End-to-end verification (manual, documented for the user, not automated): open Obsidian, run Templater Captura, check that a file is created at the new path.

- [ ] **Step 5: Commit**

```bash
git add vault/Templates/Captura.md vault/.obsidian/plugins-config/  # if schema modified
git commit -m "feat: Captura escreve em Pendencias/<slug>/spec.md"
```

---

## Task 9: Update Index.md (dataviewjs com tabela de pendencias)

**Files:**
- Modify: `vault/Index.md` (replace dataviewjs section)

- [ ] **Step 1: Read current Index.md fully**

Run: `wc -l vault/Index.md` to know the size. The dataviewjs block starts at line 23 (`\`\`\`dataviewjs`) and goes until the closing backticks. Need to replace the "tab projetos / pendentes" logic with "projetos / pendencias-por-estagio".

Read the file fully before editing:

```bash
cat vault/Index.md
```

Identify the existing dataviewjs block (it builds a `state.tab` switch between `projetos` and `pendentes`).

- [ ] **Step 2: Replace the dataviewjs block**

The replacement keeps the projetos tab as-is but renames "pendentes" -> "pendencias" and changes the logic to:
1. Walk every `<Projeto>/Pendencias/*` folder.
2. Use the file paths exposed in `dv.pages('')` to detect which of `spec.md/task.md/tests.md/resultado.md` exist per slug.
3. Build a table `Projeto | aberta | planejamento | pronta | realizada`.
4. Show banner with legado count (file directly under `<Projeto>/Pendencias/`).

Replace the existing dataviewjs block with this (keep buttons block above unchanged):

```dataviewjs
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

const projects = dv.pages('#projecthub').sort(p => p.file.name).array();
const allPages = dv.pages('').array();

// Build pendencias index: { projeto: { slug: { spec, task, tests, resultado } } }
const pendIndex = {};
let legadoTotal = 0;
for (const p of allPages) {
  const path = p.file.path; // e.g. HMA/Pendencias/oauth-apple/spec.md
  const parts = path.split('/');
  if (parts.length < 3) continue;
  const idxPend = parts.indexOf('Pendencias');
  if (idxPend === -1) continue;
  const projeto = parts[idxPend - 1];
  // Pendencias/<slug>/<file>.md
  if (parts.length === idxPend + 2) {
    // <Projeto>/Pendencias/<file>.md  -> legado
    legadoTotal += 1;
    continue;
  }
  if (parts.length !== idxPend + 3) continue;
  const slug = parts[idxPend + 1];
  const fname = parts[idxPend + 2];
  if (!['spec.md','task.md','tests.md','resultado.md'].includes(fname)) continue;
  pendIndex[projeto] = pendIndex[projeto] || {};
  pendIndex[projeto][slug] = pendIndex[projeto][slug] || {};
  pendIndex[projeto][slug][fname.replace('.md','')] = true;
}

function classify(files) {
  const has = k => !!files[k];
  if (!has('spec')) return 'invalid';
  if (!has('task')) return (has('tests') || has('resultado')) ? 'invalid' : 'aberta';
  if (!has('tests')) return has('resultado') ? 'invalid' : 'planejamento';
  if (!has('resultado')) return 'pronta';
  return 'realizada';
}

// Aggregate counts per projeto and globally
const stages = ['aberta','planejamento','pronta','realizada'];
const byProjeto = {};
const globalCounts = { aberta:0, planejamento:0, pronta:0, realizada:0 };
for (const projeto of Object.keys(pendIndex)) {
  byProjeto[projeto] = { aberta:0, planejamento:0, pronta:0, realizada:0 };
  for (const slug of Object.keys(pendIndex[projeto])) {
    const s = classify(pendIndex[projeto][slug]);
    if (stages.includes(s)) {
      byProjeto[projeto][s] += 1;
      globalCounts[s] += 1;
    }
  }
}

const root = dv.container.createEl('div', { cls: 'ts-root' });
root.createEl('p', { text: `${projects.length} projetos · ClaudeBrain`, cls: 'ts-status' });

// KPIs
const kpisHost = root.createEl('div', { cls: 'kpis' });
const kpiCard = (v, l) => {
  const wrap = kpisHost.createEl('div', { cls: 'kpi' });
  wrap.createEl('div', { cls: 'v', text: String(v) });
  wrap.createEl('div', { cls: 'l', text: l });
};
kpiCard(projects.length, 'projetos');
for (const s of stages) kpiCard(globalCounts[s], s);

// Legado banner
if (legadoTotal > 0) {
  const banner = root.createEl('div', { cls: 'legado-banner' });
  banner.createEl('strong', { text: `${legadoTotal} pendencia(s) em formato legado.` });
  banner.createEl('span', { text: ' Rode `/pendencia migrate <projeto>` pra converter.' });
}

// Tabs (projetos / pendencias)
const tabsHost = root.createEl('div', { cls: 'tabs' });
const tabProjetos = tabsHost.createEl('button', { text: `Projetos (${projects.length})`, cls: 'tab' });
const tabPendencias = tabsHost.createEl('button', { text: `Pendencias`, cls: 'tab' });

const body = root.createEl('div', { cls: 'tab-body' });

function renderProjetos() {
  body.empty();
  const list = body.createEl('div', { cls: 'projeto-list' });
  for (const p of projects) {
    const item = list.createEl('div', { cls: 'projeto-item' });
    item.createEl('a', { text: p.file.name, href: p.file.path });
  }
}

function renderPendencias() {
  body.empty();
  const table = body.createEl('table', { cls: 'pendencias-table' });
  const head = table.createEl('thead').createEl('tr');
  ['Projeto', ...stages].forEach(h => head.createEl('th', { text: h }));
  const tbody = table.createEl('tbody');
  const projs = Object.keys(byProjeto).sort();
  for (const proj of projs) {
    const row = tbody.createEl('tr');
    row.createEl('td', { text: proj });
    for (const s of stages) {
      row.createEl('td', { text: String(byProjeto[proj][s]) });
    }
  }
}

tabProjetos.onclick = () => { state.tab = 'projetos'; renderProjetos(); };
tabPendencias.onclick = () => { state.tab = 'pendencias'; renderPendencias(); };

renderProjetos();
```

- [ ] **Step 3: Verify Dataview block parses**

Cannot test inside Obsidian via CLI. Static syntax check:

```bash
node -e "const fs=require('fs'); const s=fs.readFileSync('vault/Index.md','utf8'); const m=s.match(/\`\`\`dataviewjs\n([\s\S]*?)\n\`\`\`/); if(!m) throw new Error('no dataviewjs block'); new Function('dv', m[1]); console.log('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add vault/Index.md
git commit -m "feat: Index.md mostra pendencias por estagio + banner de legado"
```

---

## Task 10: Adicionar fase 9 ao `/claudebrain-init`

**Files:**
- Modify: `skills/claudebrain-init/SKILL.md` (add Phase 9 + Phase 10)

- [ ] **Step 1: Read claudebrain-init SKILL.md fully**

```bash
cat skills/claudebrain-init/SKILL.md
```

Identify last phase (Phase 8). Add Phases 9 and 10 after it.

- [ ] **Step 2: Append Phase 9 + 10**

Add at the appropriate place in the file (after Phase 8, before any closing footer):

```markdown
---

## Phase 9 — Install /pendencia skill

**Quando pular**: se `~/.claude/skills/pendencia/SKILL.md` ja existir e for symlink pra `$REPO/skills/pendencia/SKILL.md`.

**Pergunta**: "Instalar a skill `/pendencia` (gerencia cascata de pendencias)?"

Aplicar:
```bash
bash "$REPO/scripts/install-pendencia.sh"
```

Verificar:
```bash
test -L "$HOME/.claude/skills/pendencia/SKILL.md" && echo OK
```

---

## Phase 10 — Install /project-new skill

**Quando pular**: se `~/.claude/skills/project-new/SKILL.md` ja existir e for symlink pra `$REPO/skills/project-new/SKILL.md`.

**Pergunta**: "Instalar a skill `/project-new` (bootstrap vault de projetos novos)?"

Aplicar:
```bash
bash "$REPO/scripts/install-project-new.sh"
```

Verificar:
```bash
test -L "$HOME/.claude/skills/project-new/SKILL.md" && echo OK
```
```

If the existing SKILL.md mentions "8 phases" or "1..8" anywhere, update those references to "10 phases" / "1..10".

- [ ] **Step 3: Validate frontmatter still parses**

Run: `python3 -c "import yaml; print(yaml.safe_load(open('skills/claudebrain-init/SKILL.md').read().split('---')[1]))"`
Expected: no error.

- [ ] **Step 4: Commit**

```bash
git add skills/claudebrain-init/SKILL.md
git commit -m "feat: /claudebrain-init fases 9 e 10 instalam /pendencia e /project-new"
```

---

## Task 11: Update README.md com secao da cascata

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add section after the existing 'Filosofia da organizacao de pastas' but before 'Setup'**

Read the current README. Locate the heading `## Setup` (line 105 in current state). Insert a new section just before it:

```markdown
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

```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: secao da cascata de pendencias no README"
```

---

## Task 12: Final verification (suite completa)

**Files:** (no changes — just run everything)

- [ ] **Step 1: Run full test suite**

```bash
cd ~/PROJETOS/claude-brain && python -m unittest discover tests -v
```

Expected: PASS on all tests (existing + new).

- [ ] **Step 2: Verify all shell scripts pass syntax check**

```bash
bash -n scripts/install-skill.sh && \
bash -n scripts/install-save-session.sh && \
bash -n scripts/install-pendencia.sh && \
bash -n scripts/install-project-new.sh && \
bash -n scripts/claudebrain-update.sh && \
echo "All scripts OK"
```

Expected: `All scripts OK`.

- [ ] **Step 3: Verify skill frontmatters parse**

```bash
for f in skills/*/SKILL.md; do
  python3 -c "import yaml; yaml.safe_load(open('$f').read().split('---')[1])" && echo "$f OK"
done
```

Expected: each `SKILL.md OK` line.

- [ ] **Step 4: Verify dataviewjs in Index.md still parses as JS**

```bash
node -e "const fs=require('fs'); const s=fs.readFileSync('vault/Index.md','utf8'); const m=s.match(/\`\`\`dataviewjs\n([\s\S]*?)\n\`\`\`/); new Function('dv', m[1]); console.log('OK')"
```

Expected: `OK`.

- [ ] **Step 5: Manual install in dev environment**

```bash
bash scripts/install-pendencia.sh
bash scripts/install-project-new.sh
ls -la ~/.claude/skills/pendencia/ ~/.claude/skills/project-new/
```

Expected: both directories show `SKILL.md` as symlink + `.repo-path` as file.

- [ ] **Step 6: Smoke test via Claude Code**

Open a fresh Claude Code session. Run:
```
/pendencia status
```
Expected: skill loads, executes `classify_project_pendencias` per projeto in vault, shows table.

Run:
```
/pendencia new TestProject/exemplo-cascata
```
Expected: creates folder + spec.md.

Run:
```
/pendencia migrate <projeto-com-legado>
```
Expected: shows plan, asks confirmation, applies.

- [ ] **Step 7: Commit final tag**

```bash
git tag cascade-v1
echo "Cascade v1 implemented. All checkpoints green."
```

---

## Self-Review

**Spec coverage check:**
- Cascata `spec/task/tests/resultado` — Tasks 1-4 (logic), 6 (skill orchestration).
- Forma no disco (pasta por pendencia) — Task 1 classifier, Task 8 Captura write target.
- Claude gera em cascata, usuario revisa — Task 6 (skill steps anuncia antes de agir).
- Captura cria spec.md direto, Notas Pendentes deprecated — Tasks 8, 9 (banner).
- Estado por presenca de arquivos — Task 1.
- Implementacao integra TDD — Task 6 `/pendencia next` subcomando.
- Project init vault-only — Task 7.
- `/pendencia status` — Task 6.
- `/pendencia migrate` — Tasks 4 (logic) + 6 (orchestration).
- `/pendencia from-geral` — Task 6.
- Index.md atualizado — Task 9.
- Modal Form atualizado — Task 8.
- `/claudebrain-init` fase nova — Task 10.
- Testes — Tasks 1, 2, 4 (cover all pure logic).
- README — Task 11.

**Placeholder scan:** none — every step has concrete code, paths, expected outputs.

**Type consistency:**
- `classify_pendencia()` returns same string set used by `next_stage()` keys and Dataview JS `classify()` function. Both produce: `aberta | planejamento | pronta | realizada | invalid`.
- `Migration` TypedDict has `source/slug/target_dir/target_file/project` — Task 4 step 3 corrected this inline.
- Slug normalization rules identical in Python (`scripts/pendencia/slug.py`) and JS (`vault/Templates/Captura.md`) — both: NFKD strip → lowercase → `[^a-z0-9]+` → dash → strip outer dashes.
