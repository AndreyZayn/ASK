---
title: Software Execution Loop
description: Authorized implementation, fix, or accepted-plan execution.
kind: loop
scope: shared
loop_status: active
updated: {{DATE}}
---
# Software Execution Loop

## Purpose and entry

Authorized implementation, fix, or accepted-plan execution. Read the existing project context and the current task checkpoint. A missing material criterion returns that specific gap to planning; ordinary implementation choices stay within execution.

## Primary hat

[[Agents/hats/software-developer]]. A hat does not require a separate agent. Independent review requires a distinct reviewer when warranted; renaming the author's role is not independence.

## Iteration and feedback

Read live source and the project repository contract. Prepare the documented local environment, implement a focused change, and exercise relevant behavior and failures with synthetic fixtures. Inspect the complete diff. Obtain independent review for consequential permission, persistence, migration, or deployment changes when required by the project. Repair acceptance failures, rerun affected checks, and deliver only to the authorized target. Iterate on acceptance failures within scope. After two failed repairs of one problem, change the approach under [[Agents/rules/task-completion]].

## Done and stopping points

A verified change at the requested local, commit, branch, or PR boundary, with exact evidence and remaining limitations. Stop at that boundary, report dependent blockers precisely, and continue independent authorized work. Reading this definition does not start another loop, invoke an agent, grant deployment authority, or schedule work.

Procedure: [[Agents/rules/software-development/execution]]. Up: [[Agents/loops/INDEX]].
