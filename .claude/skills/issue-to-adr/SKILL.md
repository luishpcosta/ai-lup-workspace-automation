---
name: issue-to-adr
description: "Use quando o usuário descrever uma necessidade técnica de forma informal (mensagem de chat, ideia verbal, ticket curto, comentário em reunião) — não um PRD escrito — e quiser a arquitetura, ADR e atividades/AC correspondentes. Acione especialmente quando a informação dada for insuficiente para decidir a arquitetura (faltam requisitos não-funcionais, escopo, volume, criticidade): a skill deve perguntar o que falta antes de propor algo, em vez de assumir. Gera o mesmo par ADR+ACs da skill de PRD, com checkpoint humano. Use mesmo sem o usuário citar 'PRD', 'ADR' ou 'arquitetura' explicitamente — se a intenção é 'preciso resolver X tecnicamente e não tenho um documento formal', esta skill se aplica."
metadata:
  language: agnostic
  tags: [meta, sdd, spec-driven, adr]
---

# Demanda informal → Arquitetura → ADR + ACs (com elicitação ativa)

Mesma espinha dorsal da skill `prd-to-arquitetura-adr` (ADR, atividades/AC,
checkpoint humano), mas para o caso em que **não existe um PRD escrito** —
a demanda chega como uma frase, um ticket curto, ou uma ideia falada em
reunião. A diferença está toda na Fase 1: em vez de extrair de um
documento, a skill **elicita ativamente** o que falta antes de propor
qualquer arquitetura.

## Quando usar

- O usuário descreve uma necessidade em 1-3 frases, sem documento formal.
- A demanda chega faltando informação relevante para decidir arquitetura
  (ex.: não diz se é síncrono, não diz volume esperado, não diz criticidade).
- O usuário pede algo como "como eu resolveria isso tecnicamente?" a partir
  de uma ideia, não de um PRD.

Se o usuário já tem um PRD escrito e completo, prefira a skill
`prd-to-arquitetura-adr` — ela pula a elicitação e vai direto pra extração.

## Fluxo

### Fase 1 — Elicitação ativa (o coração desta skill)

1. **Extraia o que já está explícito** na mensagem do usuário — não
   pergunte de novo o que ele já disse.
2. **Rode a checklist de lacunas** (`references/checklist-elicitacao.md`)
   contra o que foi dito. Identifique o que falta e **priorize por impacto
   na decisão arquitetural** — não pergunte tudo de uma vez. Ordem de
   prioridade:
   1. Objetivo/problema de negócio (se não estiver claro, nada mais segue)
   2. Síncrono vs. assíncrono / criticidade (afeta o desenho mais que
      qualquer outra coisa)
   3. Volume/escala esperado e requisitos de latência
   4. Escopo (o que está fora) e restrições (prazo, stack obrigatória)
3. **Pergunte só o necessário**, em lotes pequenos (use `ask_user_input_v0`
   para perguntas binárias/fechadas — ex. "Isso precisa responder na hora
   ou pode ser processado depois?"; pergunta aberta em texto para o que não
   tem opções claras, ex. volume esperado).
4. **Sintetize um RF/RNF mínimo** com o que foi coletado e **mostre ao
   usuário antes de seguir** — mesma lógica de "mostrar antes de continuar"
   da skill de PRD, mas aqui é a skill quem redige a partir das respostas,
   não quem extrai de um texto:
   ```
   Resumo do que entendi:
   RF-01: ...
   RNF-01: ...
   Fora de escopo: ...
   Confirma que está certo antes de eu propor a arquitetura?
   ```
5. **Limite de rodadas**: no máximo 2 rodadas de perguntas. Se depois disso
   ainda houver lacuna, **não bloqueie indefinidamente** — registre como
   **assunção explícita** (ex.: "Assumindo volume baixo, < 100 req/dia,
   já que não foi possível confirmar") e leve isso para o ADR na Fase 3,
   na seção de Contexto, deixando claro que é uma suposição a validar.

### Fase 2 — Propor arquitetura

Idêntica à skill de PRD: apresente a arquitetura proposta (componentes e
conexões) ao usuário antes de seguir para o ADR.

### Fase 3 — Escrever o ADR

Use `references/adr-template.md`. Diferença em relação à skill de PRD: como
não há PRD, a seção **Contexto** deve citar que a origem é uma demanda
informal (não um documento) e **listar as assunções registradas na Fase 1**
de forma destacada, para quem ler depois saber o que foi suposto e não
validado.

Como na skill de PRD, preencha o **front matter de relação** do template
(`id`/`titulo`/`status`/`contextos`/`afeta`/`supera`/`depende_de`), usando os nomes
exatos das entradas do `CONTEXT-MAP.md` quando ele existir — é o que registra a ADR no
grafo de dependências mantido pela skill `blueprintfy`. Se esta decisão substitui uma
anterior, declare `supera: [<ADR-id>]` na ADR **nova** (a antiga não é editada).

Também como na skill de PRD, se a skill `make-diagram` estiver disponível no
ambiente, acione-a logo após gravar o arquivo do ADR para gerar o diagrama
da arquitetura como imagem (`adr/ADR-<id>-diagrama.png`), referenciando-o
na seção **Decisão**; sem `make-diagram`, use Mermaid inline como fallback.

### Fase 3.5 — Elicitar o contrato de payload (antes das ACs)

Idêntica à skill de PRD: para toda conexão com payload estruturado
envolvida na arquitetura proposta, elicite o contrato antes de escrever a
AC na Fase 4 — não basta marcar que "precisa de AC de contrato" e inferir
depois. O risco é diferente para REST e mensageria:

- **REST**: campos do payload, tipo de cada campo, obrigatoriedade,
  contrato de erro (status codes + formato do corpo de erro) e idempotência
  em escrita.
- **Mensageria**: versionamento do schema, compatibilidade (campo novo é
  **sempre opcional**), idempotência do consumidor e DLQ — e, antes de
  propor mudança em evento/tópico já existente, **pergunte diretamente ao
  usuário** quem já consome aquele evento hoje, mesmo que não apareça na
  demanda atual.

Ver `references/contrato-payload.md` para o roteiro completo de perguntas.

### Fase 4 — Decompor em atividades por componente

Idêntica à skill de PRD: atividade = recorte completo por componente, pode
ser extensa, oferecer quebra em duas+ atividades quando parecer grande
demais (nunca quebrar sem perguntar).

### Fase 5 — Checkpoint humano (obrigatório)

Idêntico à skill de PRD: confirmar quebra de atividades em ADRs separados.

### Fase 6 — Entregáveis

- `adr/ADR-XXX-titulo.md` (com a seção de assunções, se houver)
- `adr/ADR-XXX-acs.md`
- `adr/ADR-XXX-diagrama.png` (somente se `make-diagram` estiver disponível — ver Fase 3)

**Gate do CONTEXT-MAP (se existir `CONTEXT-MAP.md` na raiz do projeto):** igual à
skill de PRD — depois de gravar os arquivos, verifique se cada um é alcançável a
partir do `CONTEXT-MAP.md`; se não for, adicione a referência na seção adequada
(tipicamente *Planejamento (to-be)* do contexto certo, perguntando ao usuário se for
ambíguo); e valide relendo o mapa e conferindo que o caminho existe, reportando o
resultado. Se a ADR declarou `supera:`, confira que o `<ADR-id>` alvo existe e avise o
usuário que aquela decisão passou a superada. Os entregáveis só estão completos depois
desse gate.

## Arquivos de referência

- `references/checklist-elicitacao.md` — o que sempre checar antes de
  propor arquitetura, e como priorizar/perguntar.
- `references/adr-template.md`, `references/ac-template.md`,
  `references/contrato-payload.md` — mesmos templates da skill
  `prd-to-arquitetura-adr`.
