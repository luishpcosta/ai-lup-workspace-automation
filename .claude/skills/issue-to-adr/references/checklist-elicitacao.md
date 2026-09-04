# Checklist de elicitação — o que checar antes de propor arquitetura

Rode esta checklist contra a mensagem do usuário. Marque o que já está
respondido implicitamente; pergunte só o que falta, na ordem de prioridade
abaixo (não despeje tudo de uma vez).

## 1. Objetivo / problema de negócio (bloqueante — sempre confirmar)
- Qual problema isso resolve? Para quem?
- Se a resposta for vaga ("melhorar a experiência"), peça um exemplo
  concreto de situação que motivou o pedido.

## 2. Padrão de execução (alto impacto na arquitetura)
- Isso precisa responder na hora (síncrono) ou pode ser processado depois
  (assíncrono)?
- Existe algum SLA já conhecido (mesmo informal, "o time de produto quer
  resposta em até X segundos")?
- Quão crítico é isso? Se falhar, o que acontece — bloqueia outra coisa,
  ou pode ser reprocessado depois sem problema?

## 3. Volume e escala (afeta escolha de tecnologia/padrão)
- Volume esperado (pedidos/dia, usuários simultâneos, registros)?
- Picos previstos (campanha, sazonalidade)?
- Se o usuário não souber, está OK assumir volume baixo/moderado
  explicitamente — não bloquear por isso.

## 4. Escopo e restrições
- O que está explicitamente fora dessa demanda?
- Existe prazo? Existe stack obrigatória (ex.: "tem que ser na AWS",
  "tem que reusar o serviço X")?
- Isso parece relacionado a algo que já existe no sistema? Se sim, pergunte
  se a intenção é estender algo existente em vez de criar do zero.

## Como perguntar

- Priorize por impacto: se o usuário só responder 2 perguntas, as que mais
  valem são as da seção 2 (síncrono/assíncrono/criticidade) — são as que
  mais mudam o desenho da arquitetura.
- Perguntas binárias/fechadas (síncrono vs assíncrono, crítico vs não) →
  `ask_user_input_v0`.
- Perguntas abertas (volume esperado, objetivo de negócio) → pergunta em
  texto livre, sem forçar opções artificiais.
- Máximo 2 rodadas. Depois disso, **registre assunção explícita** e siga —
  nunca trave o processo esperando uma resposta perfeita.

## Exemplo de priorização em uma rodada só

Mensagem do usuário: "Precisamos avisar o cliente quando o pedido for
cancelado."

Pergunta 1 (mais importante): "Esse aviso precisa ser instantâneo ou pode
levar alguns minutos? E se falhar o envio, é aceitável tentar de novo depois
ou precisa ser garantido na hora?"

Se a resposta já deixar claro que é assíncrono e não crítico, **não
pergunte volume** nesse caso — proponha algo simples (fila + worker) e só
valide volume se a resposta indicar algo fora do padrão (ex.: "isso vai
disparar pra milhões de clientes de uma vez").
