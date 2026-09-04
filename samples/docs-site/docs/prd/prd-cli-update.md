---
id: prd-cli-update
title: "PRD: comando update"
sidebar_label: PRD — comando update
---

# PRD: CLI — Comando `update`

> Reproduzido de `~/developer/ai-tools/ai-lup-skills/specs/003-cli-update/spec.md`
> (feature `003-cli-update`, fase `verified`, origem `spec-first`).

## Problema / Contexto

Quando uma skill do repositório central evolui, o usuário precisa propagar a nova
versão para os projetos onde a usa. Antes do `update`, isso exigia `remove` seguido de
`add`, manualmente. O comando `update` automatiza a troca: para cada agente
selecionado, garante que a skill fique na versão atual do repositório central —
substituindo a versão antiga (removendo arquivos obsoletos) ou instalando do zero se
ainda não existir naquele agente.

## Escopo

- Novo comando `lup-skills update <skill-name>`.
- Oferece **todos** os agentes suportados na seleção (instalados ou não).
- Por agente selecionado, a operação é uma troca limpa: apaga o diretório de destino
  (se existir) e copia a versão atual de forma plana e recursiva (mesma semântica do
  `add`), garantindo que arquivos que não existem mais na nova versão sejam removidos.
- Mensagem distingue "atualizada" (já existia) de "instalada" (não existia).

## Fora de escopo (não-objetivos)

- Comparação de versões / detecção de "já está atualizado" (a troca é sempre
  incondicional).
- Atualizar todas as skills de uma vez (`update --all`).

## Edge cases

- Skill inexistente no repositório central → erro.
- Arquivos que existiam só na versão antiga devem desaparecer após o update.
- Agente selecionado sem a skill → instalação limpa, sem erro.

Critérios de aceite completos: [AC — CLI Update](/ac/ac-cli-update).
