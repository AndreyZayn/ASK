---
title: Session Logs Index
description: Date routing for monthly append-only write-session history.
kind: index
scope: shared
lifecycle_status: active
updated: {{DATE}}
tags: ["memory", "logs"]
---
# Session Logs Index

Route an authorized vault-writing session by its local date to `YYYY-MM.md` in this folder, with `kind: log`, one concise line per session, and `by`/`upd` provenance using a locally enrolled ID. Create the month file on its first write and append thereafter. Include session-owned paths and outcome without sensitive content. Do not make a per-agent directory, index every log line, backdate, or replace the owning note with a log. Follow [[knowledge-continuity-loop]].
