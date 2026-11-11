---
title: Model Resource Safety
description: Assess resource-intensive local model workloads before starting them.
kind: rule
scope: shared
lifecycle_status: active
updated: {{DATE}}
---
# Model Resource Safety

Before launching an authorized resource-intensive local model or job, check the workload's expected peak memory, hardware requirements, concurrency, current system pressure, and a reasonable reserve for the owner's existing applications. On shared-memory devices, account for all competing processes. If the working set or safe headroom is unknown, do not start the workload; report the missing evidence and continue independent work.

Use bounded workloads, observe resource use, and stop when the established limits are exceeded. Do not download model weights, incur new spending, change providers, or weaken safeguards without the owner's applicable authority.
