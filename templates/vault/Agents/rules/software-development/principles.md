---
title: Software Development Principles
description: Practical constraints for choosing and delivering software changes.
kind: rule
scope: shared
lifecycle_status: active
updated: {{DATE}}
---
# Software Development Principles

Prefer the smallest complete, maintainable solution that meets the owner's current requirements. Grow changes in working, verified layers; keep responsibilities separated and use existing, well-supported dependencies when they fit. Avoid speculative compatibility machinery, duplicated sources of truth, and hidden fallbacks.

Preserve user data, unrelated edits, and established authority boundaries. Test observable behavior and failure paths proportionately to risk. Complete work at the requested delivery target and report limitations; a successful command or submitted pull request is not proof of a healthy deployment.
