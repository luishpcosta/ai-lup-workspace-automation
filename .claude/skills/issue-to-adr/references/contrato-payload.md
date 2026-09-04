# Elicitação do contrato de payload (REST vs. mensageria)

Referência da **Fase 3.5** do fluxo principal. Existe porque "descrever o
contrato explicitamente" na AC (Fase 4) não acontece por conta própria —
alguém precisa ter perguntado os campos, tipos e regras de erro **antes**
de escrever a AC. Essa elicitação é diferente para REST e para mensageria
porque o risco é diferente:

- **REST (síncrono)**: quem sofre o erro é quem chama, na hora. O contrato
  importa, sobretudo, para o chamador imediato.
- **Mensageria (assíncrono)**: quem sofre não é quem publica — são os
  consumidores desacoplados, que podem nem ter sido mencionados na demanda
  atual. Um campo removido ou um tipo trocado quebra alguém de outro time,
  possivelmente sem aviso nenhum no momento da mudança.

Aplique esta fase a toda conexão que troca payload estruturado como parte
da arquitetura proposta. Pule conexões que não trocam payload estruturado
(ex.: leitura direta de banco).

## Como decidir o tipo

Olhe o tipo de conexão definido na Fase 2 (`rest-sync` → roteiro REST
abaixo; `evento-async`, `fila-async`, ou qualquer conexão que tenha na
ponta um componente do tipo fila/tópico → roteiro de mensageria). Se não
estiver claro, pergunte ao usuário antes de seguir — não assuma.

## Roteiro REST

Pergunte e registre, antes de escrever a AC:

1. **Campos do payload de request** — nome de cada campo.
2. **Campos do payload de response** (sucesso) — nome de cada campo.
3. **Tipo de cada campo** (string, number, boolean, objeto, array, data,
   enum...).
4. **Obrigatoriedade** — quais campos são obrigatórios vs. opcionais, e o
   que acontece se um opcional não vier (default? omitido na resposta?).
5. **Contrato de erro** — quais status codes existem (400/404/409/422/500…),
   formato do corpo de erro (ex.: `{ "error": { "code", "message" } }`), e
   quais cenários de erro de *negócio* (não só infraestrutura) precisam de
   código próprio (ex.: "cupom expirado" vs. "cupom não encontrado").
6. **Idempotência em escrita** — se a operação cria ou altera estado
   (POST/PUT/PATCH/DELETE), como uma repetição (retry por timeout, duplo
   clique) é tratada: existe chave de idempotência (ex.: header
   `Idempotency-Key`)? A operação já é naturalmente idempotente (ex.: PUT
   por ID)? O que o chamador recebe ao repetir uma operação já concluída —
   sucesso de novo, ou erro de conflito?

### Exemplo de pergunta em lote (REST)

> "Para o `POST /pedidos/{id}/cupom`: o payload tem só `codigo_cupom`
> (string, obrigatório), ou também `valor_esperado` para validação cruzada?
> Se essa chamada for repetida porque o cliente teve timeout (cupom já
> aplicado antes), a segunda chamada deve devolver sucesso de novo ou erro
> de conflito?"

## Roteiro mensageria

Pergunte e registre, antes de escrever a AC:

1. **Versionamento** — como o consumidor identifica a versão do schema do
   evento (campo `version` no payload? nome do tópico contém a versão?)?
2. **Compatibilidade** — regra fixa: **campo novo é sempre opcional**, com
   comportamento definido para quem ainda não souber dele. Remover ou
   renomear um campo existente, ou tornar um campo opcional em obrigatório,
   é **breaking change** e exige estratégia de migração explícita (versão
   nova do tópico, período de transição) — não só "avisar no Slack".
3. **Idempotência do consumidor** — a entrega é at-least-once (o evento
   pode chegar duplicado)? Qual é a chave de deduplicação (id do evento?
   id do pedido + tipo de evento?) e o consumidor já lida com isso, ou isso
   é parte do que está sendo desenhado agora?
4. **DLQ** — depois de quantas falhas de processamento a mensagem vai para
   a dead-letter queue? Existe DLQ configurada para esse tópico/fila? Quem
   monitora e reprocessa?
5. **Pergunte diretamente ao usuário** — antes de propor qualquer mudança
   de payload em um evento/tópico já existente, pergunte quem já consome
   esse tópico/fila hoje. Mostre a lista que o usuário informar **mesmo
   que nenhum desses consumidores apareça no PRD/demanda atual** e
   pergunte explicitamente: "Esse tópico já é consumido por: \<lista\>. O
   campo que está sendo alterado é usado por algum deles? A mudança é
   compatível (campo novo opcional) ou é breaking change?"

### Exemplo de pergunta em lote (mensageria)

> "O tópico `pedido-cancelado` já é consumido por `billing-service` e
> `notification-service` (conforme você indicou). A proposta é adicionar o
> campo `motivo_cancelamento` — ele vem opcional, então os dois
> consumidores atuais continuam funcionando sem mudança. Confirma que
> nenhum deles *precisa* ler esse campo para funcionar corretamente hoje
> (ou seja, que é aditivo e não uma mudança de comportamento esperado)?"

## O que fazer com o resultado

O que for elicitado aqui alimenta diretamente a AC de contrato na Fase 4 —
ver os blocos REST e mensageria em `ac-template.md`. Se alguma resposta
ficar pendente após uma rodada de perguntas, registre como assunção
explícita (mesmo critério das demais fases) e deixe marcado no ADR que o
contrato ainda precisa de validação antes da implementação.
