# Engineering Standards

## Test-driven development

Every feature and bug fix follows red, green, refactor:

1. Add a focused test that fails for the intended reason.
2. Implement the smallest complete and correct solution.
3. Refactor only while the full suite remains green.

A test that already passes before the production change does not prove the new behavior. Never skip, weaken, or delete tests to make a change pass.

## Design quality

- Do not ship temporary, brittle, or “hacky” solutions. Fix the underlying design problem.
- Keep modules, functions, and classes focused on one responsibility.
- Remove real duplication, but do not create abstractions without a clear shared contract.
- Use typed interfaces or protocols at replaceable boundaries. Prefer a function when a class adds no useful state or contract.
- Keep security controls centralized and deny access by default in production.
- Handle expected failures explicitly. Log unexpected failures with enough context to diagnose them.
- Add unit tests at module boundaries and integration tests for security-sensitive flows.
