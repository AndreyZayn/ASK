---
title: Software Work Rules
description: Task-specific gates for software plans, changes, and review.
kind: rule
scope: shared
lifecycle_status: stable
updated: {{DATE}}
tags: ["agents", "software"]
governed_by:
  - "[[Agents/rules/knowledge-work]]"
---
# Software Work Rules

Plan from the request and nearby project context, identify affected files and validation, then implement only authorized changes. Preserve unrelated edits, verify behavior with relevant tests, and review the diff for scope and secrets before handoff. Report failures and untested paths honestly; do not claim a review or deployment you did not perform. Record durable design decisions in [[Projects/INDEX]] rather than an ephemeral transcript. Publication, runtime setup, and destructive changes require explicit authority.
