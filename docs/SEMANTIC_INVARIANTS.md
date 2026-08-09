# Semantic Invariants

This is the operational semantic contract. Current items correspond to code or
regression behavior unless explicitly marked otherwise.

## Assertion and licensing

- Asserted edge != candidate edge.
- Selected for operation != asserted by source.
- Candidate existence != licensed fact.
- Unresolved branch existence != selected branch.
- Branch selection licenses only explicit member edge IDs for that operation.
- Selecting a primary branch does not license recursive candidate expansions.
- Unsupported edges are never licensed.
- Missing coordinates remain missing.
- Do not complete missing edges from lexical stereotypes, cultural defaults, or
  the original noun.
- Rejected candidate != rejected or mutated graph.

## Relation strength

- `implemented_by` != `treated_as_equivalent_to` or definition.
- `factors_into` != equivalence or exhaustive definition.
- `requires` != `causes`.
- `affects` != `causes`.
- Directional `affects` qualifiers cannot be dropped.
- Generic modality cannot be silently strengthened to a universal statement.
- Optional factor != required factor.
- Shared target or lexical match does not license equivalence.
- Correlation != causation. **Recognized by the falsifier, but no current fixture
  emits a correlation edge.**

## Evaluators

- Evaluator output != intrinsic object property.
- Positive evaluation of a handle != selection of one implementation.
- Normative evaluation of an action != automatic obligation-bearer assignment.
- `good-X` evaluator != `X` configuration.
- Modifier decomposition != head-noun/category decomposition.
- Broader evaluator sensitivities remain unlicensed unless their recursive branch
  is separately selected.

## Roles, jurisdiction, and action arguments

- Role != jurisdiction.
- Guidance != authority.
- Normative guidance != obligation to obey.
- Descriptive edge != demand edge.
- Demand != jurisdiction.
- Grammatical direct object != semantic action target.
- Role/category does not automatically imply authority, jurisdiction, access,
  recurrence, obligation, identity coupling, or persistence.
- Expertise != universal authority. **PLANNED / NOT YET FIXTURE-ENFORCED.**
- Care != authority. **PLANNED / NOT YET FIXTURE-ENFORCED.**

## Branching and recursion

- Alternatives remain alternatives until an operation selects them.
- Mutually exclusive branches cannot be silently merged.
- `one_or_more` does not imply that every enumerated branch applies.
- Optional branch members remain optional.
- Horizontal ambiguity != vertical recursive expansion.
- Shared rendering requires explicit membership of the same edge ID in every
  rendered branch.
- Present in every currently enumerated branch != universal truth of the handle.
- Selecting a branch for one operation does not mutate `GraphIR`, branch status,
  edge status, or provenance.

## Projection and recomposition

- Full graph preserved != projection semantically sufficient.
- Every lossy projection records what it omitted or merged and why that is safe
  for the current operation.
- Omitted operation-relevant dimensions block `ACCEPT` without a valid safety
  declaration.
- Recomposition is task-scoped, not global normalization.
- Recomposition is not inverse factorization.
- Operation != candidate compact statement.
- Lexical return is optional.
- `RETAIN_HIGH_DIMENSIONAL` is a successful first-class outcome.
- `ACCEPT` may preserve unrelated unresolved dimensions.
- `REJECT` falsifies one candidate; it does not invalidate the underlying graph.
- Provenance disagreement blocks recomposition only when the operation declares
  provenance sensitivity.

## Source and handles

- Lexical handle != resolved ontology class.
- Catalog fragment != dictionary definition.
- Rule reading != source assertion.
- Culturally common implementation != licensed implementation.
- Surface equality syntax is required before validation may support an explicit
  equivalence edge; current fixtures emit no equivalence edges.

## Deterministic falsifier categories

Stable current `GuardPredicate` codes:

- `unknown_item_reference`
- `required_edge_missing`
- `required_edge_unlicensed`
- `unresolved_blocker`
- `merges_unresolved_branches`
- `invents_equivalence`
- `promotes_implementation_to_definition`
- `strengthens_relation`
- `drops_relation_qualifier`
- `adds_sensitive_relation`
- `turns_evaluator_output_into_intrinsic_property`
- `erases_provenance_disagreement`
- `drops_operation_relevant_dimension`
- `completes_from_default_prior`
- `invalid_branch_selection`

The falsifier is deliberately finite and deterministic. It is not a theorem
prover and must not infer absent supporting coordinates.
