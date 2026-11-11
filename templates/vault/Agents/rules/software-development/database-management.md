---
title: Database Management
description: Review, rehearse, and apply authorized database changes safely.
kind: rule
scope: shared
lifecycle_status: active
updated: {{DATE}}
---
# Database Management

Use the project's version-controlled migrations and authoritative schema. Identify the actual environment, data, affected users, permissions, recovery path, and intended delivery target before changing a database. Rehearse a new installation and a representative existing-data upgrade using safe fixtures; check migrations, data preservation, and application behavior.

Apply only the reviewed change through the project's supported process and explicit authority for the target. Never infer production or destructive-operation permission from read access. If access, expected data, or recovery evidence is missing, report the specific blocker and continue independent work.
