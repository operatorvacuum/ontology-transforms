# Agent Guidance

Treat this repository as a semantic compiler experiment, not a taxonomy.

Working rules:

- Keep node taxonomy weak; prefer semantic roles expressed by edges.
- Preserve unresolved candidate branches.
- Put provenance on every inferred edge and branch.
- Distinguish source text, catalog fragments, inference rules, and model hypotheses.
- Do not globally normalize a word to one decomposition.
- Every projection records what it omitted or merged and why that was safe.
- Add regression tests for relational behavior, not exact prose or concept definitions.
- Put reusable sentences in `examples/fixtures/*.yaml`.
- Keep implementation small and inspectable.
- Do not expand the dataset beyond proven vertical slices.
- Run tests after each meaningful change.
