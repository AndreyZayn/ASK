---
title: Orchestration Rules
description: Bounded delegation and context access for authorized workers.
kind: rule
scope: shared
lifecycle_status: stable
updated: {{DATE}}
tags: ["agents", "delegation"]
governed_by:
  - "[[Agents/rules/knowledge-work]]"
---
# Orchestration Rules

Delegate only to configured, owner-authorized workers for a bounded task. Supply a capsule naming scope, allowed paths, `KB_ACCESS`, `DELEGATION_DEPTH`, deliverable, and checks. Default maximum delegation depth is 2; a narrower task limit wins. A `KB_ACCESS: none` worker receives no vault bootstrap and must not read private knowledge. The controller supplies minimum necessary context and owns integration and verification. Never infer model/vendor quotas or permission from a catalog. See [[Agents/ontology]].
