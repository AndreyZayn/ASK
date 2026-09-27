# Capability productization

New functionality may first appear in the private reference instance. Review each addition so the public product and private instance stay connected without treating Andrey's setup as a universal default.

## Review loop

1. **Describe the outcome.** Record the user problem and intended result. Define the target user before writing capability stories.
2. **Set the boundary.** Classify the capability as reusable core, optional module, installation adapter or configuration, private-instance operation, or experiment. Record the reason.
3. **Find installation-specific values.** Paths, identities, storage, credentials, runtime, hosting, and policies should be configuration or adapters when they vary by installation.
4. **Define safety and operations.** Document authority, inputs, outputs, validation, failure behavior, and recovery.
5. **Prove the portable path.** Reusable work needs documented defaults, a sanitized example, and acceptance evidence from a clean installation.
6. **Update the records.** Update the product documentation for durable behavior and this repository's docs when reusable software is implemented here. Keep private decisions and data in the private instance.
7. **State evidence-based status.** Distinguish proposed, implemented, and verified. Generic tests do not prove a specific installation's integration works.

## Inclusion rules

- Do not copy private knowledge, real identities, machine paths, credentials, or operational data into public code, fixtures, examples, or history.
- Do not publish a private repository or push its Git history into this repository.
- Extract or implement only the reviewed portable portion of a capability.
- Keep configuration discoverable, validated, and independent of Andrey's personal values.
- If a capability stays private, record why in the private project documentation so it is not assumed to be part of the public product.
