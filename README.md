# Semantic Factorization Engine

This repository is a small compiler experiment for recovering candidate relational
structure from compressed natural-language handles. It does not assign words a
single canonical decomposition.

The current implementation is intentionally one vertical slice for:

- `I need belonging.`
- `Harmony is important.`
- `Good engineers know heap internals.`

It is not yet a general natural-language parser or a migrated ontology dataset.

## Design invariants

- Nodes have local identity and labels, not strong global semantic classes.
- Semantic roles come primarily from typed edges.
- Every inferred edge and unresolved branch carries source and derivation provenance.
- Candidate catalog fragments are contextual hypotheses, not dictionary definitions.
- Surface equality never merges nodes automatically.
- Evaluators remain explicit applications over configurations or handles.
- Alternatives remain unresolved until context or an operation justifies selection.
- Unsupported inferred edges are marked rather than promoted or silently discarded.
- **Every projection records what it omitted or merged and why that was safe.**

## Pipeline

```text
text + context
-> parse source claims
-> resolve local fragment candidates
-> instantiate candidate factor graphs
-> validate provenance and unsupported inference
-> project for a specific operation with a loss ledger
-> render a human view or emit machine IR
```

Every compilation exposes immutable `parsed`, `resolved`, `factorized`, and
`validated` graph states.

## Minimal machine IR

The machine representation contains:

- nodes: local `id` and `label` only
- typed, status-bearing edges
- unresolved branch groups
- first-class provenance
- diagnostics
- operation-specific projections with explicit loss records

Provenance distinguishes:

- `source_text`
- `catalog_fragment`
- `inference_rule`
- `model_hypothesis`

The last kind is supported by the IR but is not currently emitted by the vertical
slice.

## Human views

```powershell
python -m ontology.cli "I need belonging." --view factor
python -m ontology.cli "Harmony is important." --view implementation
python -m ontology.cli "Good engineers know heap internals." --view factor
```

Use `--ir` to inspect all machine states and projections:

```powershell
python -m ontology.cli "Harmony is important." --ir
```

## API

```python
from ontology import SemanticCompiler, render_projection

compilation = SemanticCompiler().compile("I need belonging.")
factorized = compilation.state("factorized").graph
factor_view = compilation.projection("factor")
print(render_projection(factor_view))
```

## Project shape

- `ontology/schema.py`: immutable graph IR, provenance, states, and projections.
- `ontology/compiler.py`: parser, resolver, factorizer, validator, projector, renderer.
- `ontology/catalog.py`: only the three contextual candidate fragments.
- `examples/fixtures/*.yaml`: the three approved sentence fixtures.
- `tests/test_semantic_compiler.py`: relational behavior regressions.

## Tests

```powershell
python tests/test_semantic_compiler.py
```

The tests assert graph relationships and invariants, not exact human prose.
