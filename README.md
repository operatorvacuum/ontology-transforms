# Semantic Factorization Engine

For AI-assisted development, start with:

- [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md)
- [`docs/SEMANTIC_INVARIANTS.md`](docs/SEMANTIC_INVARIANTS.md)
- [`docs/NEXT.md`](docs/NEXT.md)

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
- An edge is shared across alternatives only when its id is explicitly present in every branch.
- Unsupported inferred edges are marked rather than promoted or silently discarded.
- **Every projection records what it omitted or merged and why that was safe.**
- Preserving the full graph does not make every projection semantically sufficient.
- Factorization is fundamental; recomposition is an optional task-scoped projection.
- No lexical handle is required when the graph has no semantically safe compression.

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
- unresolved branch groups with explicit group identity and cardinality
- first-class provenance
- diagnostics
- operation-specific projections whose loss records name semantic role, safe use, and unsafe use

Provenance distinguishes:

- `source_text`
- `catalog_fragment`
- `inference_rule`
- `model_hypothesis`

The last kind is supported by the IR but is not currently emitted by the vertical
slice.

Recursive candidate expansions are hidden at projection depth `0` and recorded as
operation-relative projection loss. `--depth 1` exposes the current evaluator
expansion without treating it as another interpretation of the source sentence.

## Human views

```powershell
python -m ontology.cli "I need belonging." --view factor
python -m ontology.cli "Harmony is important." --view implementation
python -m ontology.cli "Good engineers know heap internals." --view factor
python -m ontology.cli "Good engineers know heap internals." --view factor --depth 1
```

### Example: belonging factor view

Input:

```powershell
python -m ontology.cli "I need belonging." --view factor
```

Output:

```text
INPUT
  I need belonging.

ASSERTED — source text
  speaker
    needs → belonging

CANDIDATE BRANCHES
  belonging configurations
  cardinality: one or more branches may apply

  candidate present in every explicitly listed branch
    belonging
      factors into → recognition
    explicit membership: social-recognition configuration, place-attachment configuration
    [catalog candidate · unresolved]

  A. social-recognition configuration
    belonging
      factors into → access
    belonging
      factors into → recurrence (optional)
    belonging
      factors into → identity coupling (optional)
    belonging
      factors into → obligation (optional)
    belonging
      factors into → exit cost (optional)
    [catalog candidate · unresolved]

  B. place-attachment configuration
    belonging
      factors into → place attachment
    [catalog candidate · unresolved]

UNRESOLVED
  - No configuration has been selected.

PROJECTION LOSS
  - omitted: belonging lexically matches belonging.candidates.v1
    semantic role: resolution provenance
    reason: factor view omits the trigger link because it inspects the activated candidate factors and readings
    safe for: inspecting retained candidate decompositions and evaluator readings
    unsafe for: auditing why a catalog fragment was activated
```

### Example: harmony implementation view

Input:

```powershell
python -m ontology.cli "Harmony is important." --view implementation
```

Output:

```text
INPUT
  Harmony is important.

ASSERTED — source text
  importance evaluation
    uses evaluator → important
  importance evaluation
    evaluates → harmony
  importance evaluation
    yields → positive importance judgment

CANDIDATE BRANCHES
  harmony implementations
  cardinality: one or more branches may apply

  A. conflict resolution
    harmony
      implemented by → conflict resolution
    conflict resolution
      increases → signal preservation
    [catalog candidate · unresolved]

  B. conflict suppression
    harmony
      implemented by → conflict suppression
    conflict suppression
      decreases → signal preservation
      decreases → private dissent visibility
    [catalog candidate · unresolved]

UNRESOLVED
  - No implementation has been selected.

PROJECTION LOSS
  - omitted: harmony lexically matches harmony.implementations.v1
    semantic role: resolution provenance
    reason: implementation view omits the trigger link because it compares activated realizations and their effects
    safe for: comparing retained candidate implementations and their effects
    unsafe for: auditing why a catalog fragment was activated
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
print(render_projection(factor_view, compilation.sentence))
```

## Guarded recomposition

Recomposition is not inverse factorization and does not reconstruct the original
noun. `RecompositionGuard` evaluates a task-scoped `CandidateRecomposition`
against the validated graph and returns one of:

- `accept`: every implied edge is licensed for the operation.
- `reject`: the candidate adds unsupported semantics or loses relevant distinctions.
- `retain_high_dimensional`: no candidate is safely useful, so the graph remains.

The deterministic falsifier checks required-edge licensing, unresolved branch
merges, invented equivalence, implementation promotion, relation strengthening,
qualifier loss, sensitive edges, evaluator/property confusion, provenance
disagreement, operation-relevant omission, and default-prior completion.

Operations and candidate projections are separate CLI inputs:

```powershell
python -m ontology.cli "Respect is important." `
  --operation define_respect `
  --recompose "respect means deference"
```

An operation may select an explicit candidate branch without mutating the graph:

```powershell
python -m ontology.cli "Good engineers know heap internals." `
  --operation summarize_sentence_meaning `
  --recompose "the good-engineer evaluator is sensitive to heap-internals knowledge" `
  --select-branch good.normative_branch
```

Selection licenses that branch's explicit edges only for the current operation.
The edges retain their candidate status and provenance; selected does not mean
asserted. Use `--retain-if-none` without `--recompose` to try the registered
fixture-scoped proposals and retain the graph when no compact candidate is safe.

## Project shape

- `ontology/schema.py`: immutable graph IR, provenance, states, and projections.
- `ontology/compiler.py`: parser, resolver, factorizer, validator, projector, renderer.
- `ontology/catalog.py`: contextual candidate fragments for the current fixtures.
- `ontology/recomposition.py`: optional candidate records and deterministic falsifier.
- `ontology/recomposition_cases.py`: fixture-scoped proposals used to exercise the guard.
- `examples/fixtures/*.yaml`: the three approved sentence fixtures.
- `tests/test_semantic_compiler.py`: relational behavior regressions.

## Tests

```powershell
python tests/test_semantic_compiler.py
python tests/test_recomposition.py
```

The tests assert graph relationships and invariants, not exact human prose.
