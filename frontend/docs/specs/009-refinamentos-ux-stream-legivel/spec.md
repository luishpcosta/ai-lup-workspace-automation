# Spec: Refinamentos de UX — Tema, Knowledge Bases e Stream Legível

**Feature ID:** 009-refinamentos-ux-stream-legivel
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-07

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those para `plan.md`.

## Problem / Motivation

Três atritos de uso do painel, relatados pelo usuário em conversa (sem PRD, elicitado
via skill `issue-to-adr`), registrados em `adr/ADR-010-refinamentos-ux-knowledge-bases-stream-legivel.md`:

1. O alternador de tema claro/escuro fica intercalado entre os botões de ação da
   topbar, em vez de separado deles.
2. O campo de referência de conhecimento do formulário de disparo é uma lista de
   checkboxes rotulada "Specs de referência" — nem o widget (sem busca, altura fixa)
   nem o rótulo (nome técnico da origem do dado) refletem a intenção de uso.
3. O stream ao vivo de uma execução mostra JSON bruto do `claude` CLI linha a linha —
   o usuário não consegue acompanhar o que o agente está fazendo sem interpretar o
   formato `stream-json` manualmente, e o painel não indica qual plataforma agêntica
   gerou aquele stream.

## User Stories

- Como usuário olhando a topbar, quero que o alternador de tema seja lido como uma
  preferência à parte, não como mais um botão de ação entre os outros.
- Como usuário disparando uma execução, quero escolher as bases de conhecimento
  relevantes num combobox com busca, não numa lista de checkboxes que ocupa espaço
  fixo mesmo vazia.
- Como usuário acompanhando um run, quero saber qual agente está rodando e ler o que
  ele está fazendo (texto + ferramentas usadas) sem decifrar JSON, mantendo a opção de
  ver o log bruto quando eu precisar investigar algo específico.

## Functional Requirements

- FR-1: O alternador de tema aparece à direita de todos os botões da topbar, separado
  visualmente do grupo.
- FR-2: O campo de referência de conhecimento é um combobox de multi-seleção com busca
  (padrão `react-select`), rotulado "Knowledge Bases".
- FR-3: O painel identifica, a partir do step em execução do run, qual plugin
  (plataforma agêntica) foi acionado.
- FR-4: Por padrão, o stream ao vivo de um step `claude_code_runner` é renderizado como
  leitura formatada (texto da IA como prosa; cada uso de ferramenta como um rastro com
  nome, status e detalhe expansível) — não como JSON bruto por linha.
- FR-5: O usuário pode alternar, a qualquer momento, para ver o log bruto (linha a
  linha, como hoje) e voltar à leitura formatada, sem perder conteúdo já recebido.

## Non-Functional Requirements

- NFR-1 (herdado de `006`/`007`/`009` anteriores): sem autenticação nesta versão.
- NFR-2: a mudança de contrato do backend (`GET /runs/{chain_name}` ganhando `plugin`
  por etapa) é aditiva e retrocompatível — um cliente que ignora campos desconhecidos
  não é afetado.
- NFR-3: uma linha de stream não reconhecida, ou um `plugin` sem formatador dedicado,
  nunca quebra a tela — degrada para exibição em log bruto daquele conteúdo.
- NFR-4: o payload enviado ao motor pelo campo de Knowledge Bases não muda de forma —
  só o widget e o rótulo mudam, o parâmetro (`docs_referenced`, array de ids) é
  idêntico ao de antes.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-010-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given o painel com a listagem de execuções aberta, when a topbar é
  renderizada, then o alternador de tema aparece à direita de todos os botões de ação,
  com separação visual do grupo. _(FR-1)_
- **AC-02** — Given o backend de specs remotas retornando itens, when o campo
  "Knowledge Bases" é renderizado, then ele é um combobox em barra com busca, com
  múltiplos itens selecionáveis e removíveis individualmente. _(FR-2)_
- **AC-03** — Given o valor atual do campo, when o usuário seleciona ou remove um
  item, then `onChange` recebe o novo array de ids, na mesma forma que o contrato
  anterior. _(FR-2, NFR-4)_
- **AC-04** — Given o template `claude-implementar-local` carregado, when o formulário
  de disparo é renderizado, then o rótulo do campo é "Knowledge Bases". _(FR-2)_
- **AC-05** — Given um step em execução cujo plugin é `claude_code_runner`, when o
  stream ao vivo é aberto, then por padrão o painel mostra texto da IA como prosa e
  cada uso de ferramenta como um rastro com nome + status + detalhe expansível.
  _(FR-3, FR-4)_
- **AC-06** — Given o painel em modo de leitura formatada, when o usuário aciona "Ver
  log bruto", then o painel troca para a exibição linha-a-linha já existente,
  preservando o conteúdo recebido; acionar de volta retorna à leitura formatada.
  _(FR-5)_
- **AC-07** — Given uma linha de stream que não é JSON válido, ou um `plugin` sem
  formatador dedicado, when o painel tenta a leitura formatada, then aquele conteúdo
  aparece em modo bruto, sem erro não tratado. _(NFR-3)_
- **AC-08** — Given o frontend chamando `GET /runs/{chain_name}`, when a resposta é
  montada, then cada item de `steps` inclui `plugin` (nome do plugin do step, ou
  `null` se o YAML da chain não puder ser recarregado); todo campo existente antes
  desta feature permanece com o mesmo nome/tipo. _(FR-3, NFR-2)_

## Edge Cases

- Nenhuma Knowledge Base disponível no repositório remoto de specs → combobox mostra
  estado vazio explícito, sem quebrar o formulário (comportamento herdado de `007`).
- Step em execução cujo `plugin` não é `claude_code_runner` (ex.: `git_pr`,
  `shell_script_runner`) → sem formatador dedicado, `StreamPanel` usa o log bruto
  diretamente, sem alternador de "leitura formatada" (não há o que alternar).
- `config_path` do run apontando para um YAML que não existe mais no disco → `plugin`
  vem `null` para os steps daquele run; frontend trata como "plugin desconhecido"
  (mesmo caminho de AC-07).
- Linha de stream truncada/parcial no momento da leitura → tratada como não-JSON para
  aquela linha específica (AC-07), sem interromper as linhas seguintes.

## Out of Scope (Non-Goals)

- Suporte a qualquer plataforma agêntica além de `claude_code_runner` — o desenho
  nomeia a plataforma via `plugin`, mas só há um formatador dedicado hoje; outra
  plataforma exigiria seu próprio formatador em feature futura.
- Renomear identificadores internos do parâmetro (`docs_referenced`, `spec_multiselect`,
  arquivo/componente `SpecPicker.jsx`) — a mudança é de rótulo visível, não de
  contrato interno (decisão registrada na ADR-010, Contexto).
- Editar/reenviar instruções a partir da leitura formatada do stream — `InstructionBox`
  (ADR-005) continua sendo o único caminho de envio de instrução, inalterado.
- Citações, feedback (thumbs up/down) ou ações de copiar/regenerar sobre o conteúdo do
  stream — fora do pedido original, não há necessidade de negócio identificada.

## Open Questions

Nenhuma pendente e bloqueante.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-07 | A renomeação para "Knowledge Bases" troca só o rótulo visível ou também os identificadores internos (`docs_referenced`, `spec_multiselect`, nome de arquivo)? | Só o rótulo visível (label do template + textos do picker) — identificadores internos ficam como estão, sem ganho funcional em renomeá-los agora |
| 2026-09-07 | Como o frontend sabe qual plataforma agêntica gerou o stream, antes de abri-lo? | `GET /runs/{chain_name}` passa a incluir `plugin` por step (aditivo) — resolvido no backend a partir do YAML da chain, mesma técnica já usada para decidir se um step é "streamável" (ADR-005) |
| 2026-09-07 | A leitura formatada deve tentar suportar outras plataformas agênticas hipotéticas? | Não — só `claude_code_runner` tem formatador dedicado agora; um `plugin` sem formatador cai no log bruto (RNF-02), o registro fica pronto para extensão futura sem redesenho |
