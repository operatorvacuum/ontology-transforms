# Ontology Transform Engine

This engine treats natural-language statements as compressed operators and
attempts to recover the hidden variables, assumptions, complements, and
competing implementations that were collapsed during abstraction.

Most statements compress many variables into a single object, such as
`harmony`, `belonging`, `identity`, or `good engineer`. The Ontology Transform
Engine reconstructs the hidden operator graph behind the statement: what
variables were collapsed, what assumptions became implicit, what competing
implementations exist, and what information disappeared during compression.

The core flow is:

```text
claim
-> find what got compressed away
-> recover lost degrees of freedom
```

Structured output stays boring:

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

Objects are inputs to transforms, not final explanations. Ontology is the
substrate; compression recovery is the purpose.

## Quick Start

Run commands from the repo root:

```powershell
python -m ontology.cli expand "I need belonging."
python -m ontology.cli expand "Good engineers know heap internals."
python -m ontology.cli collapsed "Harmony is important."
python -m ontology.cli graph "I am a teacher."
python examples/run_examples.py
```

## Examples

The engine does not decide whether a statement is good or bad. It detects when a
statement has collapsed a multidimensional process into a single object, then
returns the missing dimensions.

### Harmony

```powershell
python -m ontology.cli expand "Harmony is important."
```

May recover:

- collapsed variables: `harmony = truth`, `harmony = health`
- hidden variables: `conflict suppression`, `conflict resolution`, `power asymmetry`, `private dissent`
- missing complements: `signal_preservation`, `exit`, `adaptation`

### Good Engineer

```powershell
python -m ontology.cli expand "Good engineers know heap internals."
```

May recover:

- collapsed variable: `trivia_knowledge = engineering_value`
- hidden variables: `debugging`, `judgment`, `system_modeling`, `adaptation`, `AI_navigation`, `curiosity`
- missing complements: `signal_preservation`, `adaptation`

### Identity

```powershell
python -m ontology.cli expand "I am a teacher."
```

May recover:

- collapsed variable: `identity = behavior`
- hidden variables: `role`, `frequency`, `context`, `obligation`, `history`, `competence`
- competing implementations: `role`, `current preference`, `relationship-specific behavior`, `history`, `chosen commitment`

## API

```python
from ontology import TransformAPI, load_default_ontology

api = TransformAPI(load_default_ontology())
payload = api.expand("Good engineers know heap internals.").to_dict()
```

Core methods:

- `expand(sentence)`
- `detect_collapsed_variables(sentence)`
- `find_compressions(sentence)`
- `find_hidden_assumptions(sentence)`
- `find_complements(sentence)`
- `find_competing_implementations(sentence)`
- `decompose_identity(sentence)`
- `decompose_belonging(sentence)`
- `decompose_harmony(sentence)`
- `extract_operator_graph(sentence)`

## Project Shape

- `ontology/schema.py`: typed records and boring transform output.
- `ontology/store.py`: dependency-free loader for the ontology data subset.
- `ontology/transforms.py`: transform engine and collapse rules.
- `ontology/data/core.yaml`: seed operators, objects, complements, and transforms.
- `examples/fixtures/*.yaml`: regression fixtures for sentence behavior.
- `tests/test_transform_regressions.py`: behavior tests, not concept definitions.

## Regression Fixtures

Fixtures live in `examples/fixtures/` and declare the minimum expected output for
a sentence. Add a fixture when a sentence exposes a reusable decomposition shape.

Current fixtures:

- `trivia_hiring.yaml`
- `lake_walk_frequency.yaml`
- `college_best_years.yaml`
- `silence_as_loaded_object.yaml`
- `harmony_truth_collapse.yaml`
- `identity_graph_compression.yaml`

## Testing

This repo has no required runtime dependencies. If `pytest` is unavailable, run
the regression file directly:

```powershell
python tests/test_transform_regressions.py
```
