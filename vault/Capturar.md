---
type: form-launcher
tags: [hub, captura]
---

# Capturar nota

Pagina pra criar uma nota nova rapidamente sem precisar navegar. A nota e salva em `Notas Pendentes/` com data + hora no nome, frontmatter com projeto + status `pendente`.

## Como abrir o form

**Opcao 1 — Comando** (mais rapido, ate em mobile):
- Cmd+P (Mac) ou tap menu (mobile) → digite **`Templater: Captura`** → abre o form

**Opcao 2 — Hotkey** (so Mac, configura uma vez):
- Settings → Hotkeys → busca `Templater: Captura.md` → atribui `Cmd+Shift+N`

## Triagem depois

Quando voltar pro Mac, abre `Notas Pendentes/` no sidebar, processa nota por nota:

- Se vai virar acao no projeto → move (drag) pra `<projeto>/Pendencias/`
- Se e contexto/info → move pra `<projeto>/Geral/`
- Se nao serve mais → deleta

## Estrutura da nota gerada

```yaml
---
project: <projeto-selecionado>
created: 2026-05-09 16:00
status: pendente
tags: [pendente, captura, <projeto>, <suas-tags>]
---

# Titulo

Conteudo
```
