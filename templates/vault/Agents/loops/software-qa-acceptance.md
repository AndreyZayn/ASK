---
title: Software QA and Acceptance Loop
description: A testability, behavioral assessment, acceptance, or retest request.
kind: loop
scope: shared
loop_status: active
updated: {{DATE}}
---
# Software QA and Acceptance Loop

## Purpose and entry

A testability, behavioral assessment, acceptance, or retest request. Read the existing project context and the current task checkpoint. A missing material criterion returns that specific gap to planning; ordinary implementation choices stay within execution.

## Primary hat

[[Agents/hats/qa-engineer]]. A hat does not require a separate agent. Independent review requires a distinct reviewer when warranted; renaming the author's role is not independence.

## Iteration and feedback

Map criteria to representative tests, including relevant negative cases. Exercise rendered interfaces and persistence when applicable. Record environment and revision. Report reproducible defects, send scoped repairs to development, and retest affected behavior. Do not label unexercised surfaces as passed. Iterate on acceptance failures within scope. After two failed repairs of one problem, change the approach under [[Agents/rules/task-completion]].

## Done and stopping points

An acceptance assessment with evidence, defects, and explicit untested criteria; this does not authorize deployment. Stop at that boundary, report dependent blockers precisely, and continue independent authorized work. Reading this definition does not start another loop, invoke an agent, grant deployment authority, or schedule work.

Procedure: [[Agents/rules/software-development/qa-acceptance]]. Up: [[Agents/loops/INDEX]].
