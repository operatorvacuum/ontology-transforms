# AI Context

## Project goal

Semantic Factorization Engine is a small compiler experiment that turns supported
natural-language inputs into an inspectable relational graph. Its purpose is to
preserve distinctions that ordinary lexical handles compress, expose the source
and derivation of candidate semantics, and prevent unsupported implicit casts
during task-specific summarization.

- Factorization is fundamental.
- Recomposition is optional and scoped to an explicit operation.
- A high-dimensional graph is a valid final result.
- Words do not receive one globally canonical decomposition.
- Catalog and rule expansions remain candidates until an operation licenses them.
- The implementation is a narrow seven-fixture vertical slice, not a general NLP
  parser or universal ontology generator.

`GraphIR` is the semantic source of truth. CLI text is a projection over it.

## Actual compiler pipeline

```text
source text
-> parse
-> resolve
-> factorize
-> validate
-> validated GraphIR
-> operation-specific projection + loss ledger
-> human rendering or machine JSON
-> optional guarded recomposition
```

`SemanticCompiler.compile()` exposes immutable `parsed`, `resolved`,
`factorized`, and `validated` `CompilerState` values.

### Parse

Input is a supported sentence shape. Output is local nodes plus source-asserted
edges carrying `source_text` evidence. Parsing introduces no catalog semantics
and must preserve the source claim rather than replace it with an interpretation.

### Resolve

Resolution matches local node labels to contextual catalog fragments using
`lexically_matches` edges. It also creates rule-derived candidate readings for
the supported modifier and requirement sentence shapes. Matches and readings
remain inferred or unresolved; resolution does not select them.

### Factorize

Factorization instantiates matched catalog fragments as nodes, unresolved edges,
and branch groups. Every instantiated edge and branch retains source evidence,
the catalog fragment, and the instantiation rule. Competing alternatives and
recursive depth remain explicit.

### Validate

Validation checks that every non-asserted edge and branch has source plus
derivation provenance, rejects unsupported equivalence edges, checks consistent
branch cardinality, and emits diagnostics. Unsupported edges are marked
`unsupported`; they are not promoted or silently deleted.

### Project and render

The validated graph is projected into `factor`, `implementation`, or
`compression_loss` views using relation filters and a requested recursive depth.
Every omitted or merged semantic item must receive an operation-relative
`ProjectionLoss`. Rendering groups assertions, branches, recursive expansions,
unresolved state, and projection loss; it does not redefine the machine IR.

At every lossy step ask: **What distinction disappeared here, and why was it
safe to erase for this operation?**

The `context` argument is currently copied into `Compilation` but is not yet used
by parser, resolution, or factorization logic.

## GraphIR

The immutable types live in `ontology/schema.py`.

- `Node(id, label)`: a locally identified symbol. Nodes intentionally have no
  global type taxonomy; semantic roles are expressed by incident edges.
- `Edge`: `id`, source node, relation, target node, status, provenance, and
  optional key/value qualifiers.
- `Branch`: an explicitly identified candidate bundle with `group_id`, label,
  explicit `edge_ids`, mode, status, provenance, and recursive `depth`.
- `Diagnostic`: a validation or unresolved-state message tied to item IDs.
- `GraphIR`: tuples of nodes, edges, branches, and diagnostics.
- `CompilerState`: a named pass result plus its pass invariant.
- `Projection`: a named, depth-specific projected graph plus loss records.
- `ProjectionLoss`: omitted/merged item IDs, semantic role, reason, `safe_for`,
  and `unsafe_for`.
- `Compilation`: source input, stored context, pass states, and projections.

Current edge statuses are `asserted`, `inferred`, `unresolved`, and
`unsupported`. Branch status supports `unresolved`, `selected`, and `rejected`,
although compiler-generated alternatives currently remain unresolved and
recomposition selection is an external operation overlay.

Current qualifiers are:

- `direction`: currently `increase` or `decrease` on `affects` edges.
- `modality`: currently `generic` on generic source assertions.
- `necessity`: currently `optional` on optional candidate members.

## Branch semantics

- `exclusive`: at most one interpretation may be selected for an operation.
- `one_or_more`: multiple configurations or implementations may apply.
- Optional members are edges qualified with `necessity=optional`; they are not
  silently promoted to required factors.
- Branch membership is only the explicit `edge_ids` stored on the branch.
- The renderer treats an edge as shared only when the same edge ID is explicitly
  present in every rendered branch in that group.
- An edge present in every currently enumerated branch is not thereby a universal
  truth about the lexical handle.

## Provenance

`Evidence.kind` supports exactly:

- `source_text`: text/span evidence from the input.
- `catalog_fragment`: the contextual fragment that proposed an expansion.
- `inference_rule`: the parser, resolver, or instantiation rule.
- `model_hypothesis`: supported by the IR, but not currently emitted by this
  vertical slice.

Human views classify edges as source assertions, parser/resolution inferences,
rule candidates, catalog candidates, or model hypotheses. Recomposition may add
the display state `selected for operation`.

**Selected for operation is not asserted by source.** Selection permits an
edge's task-local use while preserving its unresolved status and original
provenance in `GraphIR`.

## Horizontal branching and vertical recursion

Horizontal branching represents competing or coexisting readings,
implementations, or configurations at the same semantic level. Vertical
recursion factorizes a candidate node at a greater projection depth.

- Good Engineers has exclusive normative/descriptive readings. Its evaluator
  has a depth-1 catalog expansion; the engineer configuration remains a separate
  node but has no recursive catalog expansion yet.
- Healthy Relationships independently expands the healthy-relationship evaluator
  and relationship configuration at depth 1.
- Good Parents independently expands the good-parent evaluator and parent
  configuration at depth 1.

Selecting a depth-0 branch does not recursively license depth-1 candidates.

## Projection loss

Projection loss is relative to the selected view and depth. A loss record must
state what was omitted or merged, its semantic role, why the omission is safe for
this view, and what downstream use would make it unsafe.

**Full graph preserved does not imply that a projection is semantically
sufficient.** The factor, implementation, and compression-loss views preserve
different relation sets. Hidden recursive branches and omitted catalog activation
edges are recorded rather than silently disappearing.

## Guarded recomposition

The recomposition layer lives in `ontology/recomposition.py`.

- `EdgeRequirement`: an exact required source/relation/target/qualifier tuple.
- `CandidateRecomposition`: a fixture-scoped compact proposal, operation ID,
  requirements, blockers, omissions, safety scope, and provenance.
- `RecompositionOperation`: operation ID, selected branch IDs, and whether
  provenance disagreement matters for this operation.
- `FalsificationFinding`: stable `GuardPredicate`, relevant item IDs, and a
  human message.
- `ProjectionDecision`: candidate ID, outcome, licensed evidence, findings,
  retained graph edge IDs, and explanation.

Outcomes are:

- `ACCEPT`: every required edge is licensed and no falsifier blocks the proposal.
- `REJECT`: this candidate performs an unsupported cast or unsafe omission.
- `RETAIN_HIGH_DIMENSIONAL`: no useful candidate is safe; retaining the graph is
  a successful result, not an error.

An edge is licensed only when it exists with exactly compatible qualifiers, is
not unsupported, and is either source-asserted or explicitly assigned to a branch
selected by the current `RecompositionOperation`. Candidate existence alone is
not a licensed fact.

Branch selection is an immutable operation-local overlay. Unknown selections and
multiple selections from an exclusive group are invalid. Selection licenses only
the branch's explicit edges; it neither changes edge status nor licenses recursive
descendants.

The deterministic falsifier checks missing/unlicensed edges, unresolved blockers,
exclusive-branch merges, invented equivalence, implementation promotion,
relation strengthening, qualifier loss, unsupported sensitive relations,
evaluator/property collapse, operation-sensitive provenance disagreement,
unsafe omission, default-prior completion, and invalid branch selection.

`ontology/recomposition_cases.py` contains fixed proposals for current regression
fixtures. It is test scaffolding, not a candidate-generation system.

## Current relation vocabulary

Relations emitted by the seven current fixtures:

- `needs`: source agent expresses need for a handle.
- `knows`: preserved source knowledge predicate.
- `set`: preserved source predicate for setting boundaries; it avoids treating a
  grammatical object as an action target.
- `requires`: strong necessity claim; it does not imply causation.
- `has_agent`: action participant acting as agent.
- `has_target`: genuine action target/recipient, currently the guidance addressee.
- `uses_evaluator`: evaluation application references an evaluator.
- `evaluates`: evaluation application evaluates a handle/configuration/action.
- `yields`: evaluation application yields a judgment node.
- `sensitive_to`: evaluator criterion or candidate sensitivity.
- `tend_to_have`: candidate descriptive generalization.
- `lexically_matches`: resolution link from local symbol to catalog fragment.
- `factors_into`: candidate decomposition relation.
- `implemented_by`: candidate implementation relation, never a definition.
- `affects`: directional effect with a required `direction` qualifier.

`treated_as_equivalent_to` and `distinct_from` are recognized by projection or
validation code but no current fixture emits them. Relations such as `causes`,
`has_property`, `has_authority_over`, `has_jurisdiction_over`, and `obligated_to`
appear only in falsifier proposals/checks; they are not current graph outputs.

## Current fixture families

- `I need belonging.` — one-or-more social-recognition and place-attachment
  configurations; optional factors; explicitly shared recognition; high-dimensional
  retention when the needed configuration is unresolved.
- `Harmony is important.` — asserted evaluator application plus unresolved
  conflict-resolution/suppression implementations with opposite effects on signal
  preservation; implementation is not definition.
- `Good engineers know heap internals.` — one source assertion, exclusive
  normative/descriptive readings, evaluator recursion, branch-merge rejection,
  operation-local branch selection, and `RETAIN_HIGH_DIMENSIONAL`.
- `Healthy relationships require honesty.` — compatible evaluator-criterion and
  configuration-necessity readings; independent recursion; `requires != causes`.
- `A mentor should guide you.` — action agent/recipient and normative evaluation;
  role/guidance do not create authority, jurisdiction, or an obligation bearer.
- `Respect is important.` — positive evaluation plus unresolved, non-equivalent
  implementations; respect does not become deference or require obedience.
- `Good parents set boundaries.` — lexical source handle, direct `set` assertion,
  exclusive normative/descriptive readings, independent modifier/head recursion,
  and no jurisdiction inference.

Fixtures live in `examples/fixtures/`; relational and falsifier behavior is tested
in `tests/test_semantic_compiler.py`, `tests/test_adversarial_fixtures.py`, and
`tests/test_recomposition.py`.

## Explicit non-goals and deferred systems

Not implemented:

- interaction coordinates involving mirroring, tone, gaze, or a broader
  clock-capture family;
- temporal trajectories, prediction, urgency inference, or latent phase inference;
- long-horizon causal ancestry;
- broad medical modeling;
- automatic universal ontology or candidate generation;
- a large theorem prover;
- forced lexical recomposition;
- wholesale migration of a larger ontology dataset.

## Fresh-model startup protocol

1. Read this file.
2. Read `docs/SEMANTIC_INVARIANTS.md`.
3. Read `docs/NEXT.md`.
4. Inspect the relevant implementation, fixture, and regression tests before
   proposing changes.
5. Treat code and tests as source of truth if these docs become stale.
6. Prefer minimal fixture-driven extensions over redesign.
7. Do not introduce a relation until a fixture demonstrates an observable
   distinction the existing vocabulary cannot preserve.
8. Show proposed semantic output before large ontology or grammar changes.
