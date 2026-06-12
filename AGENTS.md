# Agent Guidance

Treat this as a transform engine, not a philosophy document.

Use the README as the product spec. Keep outputs structured, boring, and stable:

```json
{
  "sentence": "...",
  "objects": [],
  "operators": [],
  "compressions": [],
  "collapsed_variables": [],
  "hidden_variables": [],
  "complements": [],
  "competing_implementations": [],
  "warnings": []
}
```

Working rules:

- Objects are inputs to transforms, not final explanations.
- Do not make concepts sacred.
- Add regression tests for behavior, not tests that define concepts.
- Put reusable sentence examples in `examples/fixtures/*.yaml`.
- Keep implementation small and inspectable.
- Prefer dependency-free code unless a dependency removes real complexity.
- Run tests after each meaningful change.
