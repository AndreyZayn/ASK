---
title: Software Planning Loop
description: An exploration, scope, acceptance, or planning request.
kind: loop
scope: shared
loop_status: active
updated: {{DATE}}
---
# Software Planning Loop

## Purpose and entry

An exploration, scope, acceptance, or planning request. Read the existing project context and the current task checkpoint. A missing material criterion returns that specific gap to planning; ordinary implementation choices stay within execution.

## Primary hat

[[Agents/hats/head-of-product]]. A hat does not require a separate agent. Independent review requires a distinct reviewer when warranted; renaming the author's role is not independence.

## Iteration and feedback

Read the user outcome and relevant project evidence. For user-facing scope, describe the user, problem, evidence, non-goals, and acceptance before implementation choices. Inspect the actual repository only as needed to make scope feasible. Split independently verifiable slices, name assumptions and dependencies, and identify the delivery target. Iterate on acceptance failures within scope. After two failed repairs of one problem, change the approach under [[Agents/rules/task-completion]].

## Done and stopping points

An accepted or reviewable plan with concrete criteria and an execution handoff. Stop before implementation unless the owner also authorized it. Stop at that boundary, report dependent blockers precisely, and continue independent authorized work. Reading this definition does not start another loop, invoke an agent, grant deployment authority, or schedule work.

Procedure: [[Agents/rules/software-development/planning]]. Up: [[Agents/loops/INDEX]].
