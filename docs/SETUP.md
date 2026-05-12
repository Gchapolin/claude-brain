# Setup passo-a-passo

Tempo estimado: ~30 minutos pra setup inicial.

## Pre-requisitos

- macOS (alguns scripts so rodam em desktop)
- Obsidian instalado (`brew install --cask obsidian`)
- Python 3.10+ (`brew install uv` e usa `uv tool install` pra ter Python isolado)
- iCloud Drive ativo (pra sync mobile, opcional)

## 1. Instalar Graphify

```bash
brew install uv
uv tool install graphifyy   # pacote PyPI tem 2 y; o binario CLI e `graphify` (1 y)
graphify install
```

Isso registra a skill `/graphify` globalmente no Claude Code.

## 2. Gerar grafo dos seus projetos

Pra cada projeto em `~/PROJETOS/<projeto>/`:

```
/graphify ~/PROJETOS/<projeto>
```

Isso roda dentro do Claude Code. Pra cada projeto, gera `graphify-out/` com `graph.json`, `GRAPH_REPORT.md`, e o vault Obsidian em `graphify-out/obsidian/`.

## 3. Criar vault unificado

```bash
mkdir -p ~/PROJETOS/Obsidian/ClaudeBrain
```

Pra cada projeto que voce graphificou:

```bash
ln -s ~/PROJETOS/<projeto>/graphify-out/obsidian ~/PROJETOS/Obsidian/ClaudeBrain/<projeto>
```

Resultado: o vault tem uma pasta por projeto, simbolicamente apontando pro graphify-out original.

## 4. Aplicar conteudo do template

Copie o conteudo de `vault/` deste repo pra raiz do seu novo vault:

```bash
cp -r vault/* ~/PROJETOS/Obsidian/ClaudeBrain/
cp -r vault/.obsidian ~/PROJETOS/Obsidian/ClaudeBrain/
```

## 5. Instalar plugins do Obsidian

Abra o vault no Obsidian, va em **Settings → Plugins da comunidade → Procurar** e instale:

- **Dataview** (queries dinamicas)
- **Templater** (templates com JS)
- **Modal Forms** (form de captura)
- **Buttons** (botoes clicaveis em notas)
- **Shell Commands** (so Mac, pra rodar `claudebrain-update.sh` via botao)
- **Meld Encrypt** (opcional, pra encriptar trechos sensiveis)

Habilite todos.

## 6. Aplicar configs dos plugins

Pra cada plugin, va em `~/PROJETOS/Obsidian/ClaudeBrain/.obsidian/plugins/<plugin-id>/data.json` e use os exemplos em `plugins-config/`.

Sobre cada um:

### Dataview

Renomeie `dataview-data.json.example` pra `data.json` no folder do plugin.

Importante: ativa **DataviewJS** e **Inline DataviewJS** — sao desligados por default.

### Templater

Configura o folder de templates como `Templates/`.

### Modal Forms

Carrega a definicao do form de captura. Voce precisa **editar `formDefinitions[0].fields[0].input.options`** pra adicionar os nomes dos seus projetos no dropdown.

### Buttons

Sem config necessaria.

### Shell Commands (Mac)

Aponta pro script `~/.local/bin/claudebrain-update.sh`.

## 7. Configurar atualizacao automatica

```bash
mkdir -p ~/.local/bin
cp scripts/claudebrain-update.sh ~/.local/bin/
chmod +x ~/.local/bin/claudebrain-update.sh
```

Edita o script pra ajustar caminhos (`PROJETOS=`, `ICLOUD=`, etc.) se voce tem layout diferente.

## 8. Mirror das pastas dos projetos

Pra cada projeto graphificado, transforme a pasta flat em estrutura espelhada do codigo:

```bash
python3 scripts/reorganize_vault.py ~/PROJETOS/<projeto>/graphify-out/obsidian/
```

## 9. (Opcional) Sync mobile via iCloud

```bash
mkdir -p ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile
```

Pra cada projeto, mova as pastas Pendencias/Geral pra iCloud e symlinka de volta:

```bash
for proj in <list-projetos>; do
    mkdir -p ~/PROJETOS/$proj/notes
    mkdir -p ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile/$proj/{Pendencias,Geral}
    ln -sfn ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile/$proj/Pendencias \
            ~/PROJETOS/$proj/notes/Pendencias
    ln -sfn ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/ClaudeBrain-Mobile/$proj/Geral \
            ~/PROJETOS/$proj/notes/Geral
done
```

No iPhone/iPad: instala Obsidian, abre, **"Open folder as vault"** → seleciona `iCloud Drive/Obsidian/ClaudeBrain-Mobile`.

## 10. Habilitar CSS snippet

`Settings → Aparencia → CSS snippets → toggle on "brain-hub"`.

## Verificacao

Abre o `Index.md` no Obsidian. Deve mostrar:
- KPI strip com numeros
- Botoes "Nova captura" e "Atualizar tudo"
- Tabs "Projetos" e "Notas Pendentes"
- Tabela com seus projetos listados, pills coloridas por stack

Se nao tiver:
- Verifica se o snippet `brain-hub` esta habilitado
- Verifica se DataviewJS esta habilitado
- Confere `cssclasses: [brain-hub]` no frontmatter do Index.md
