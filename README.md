# Ontology Transform Engine

This repo is a small Python engine for decomposing sentences into structured
transform output:

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

Objects are inputs to transforms, not final explanations. The useful output is
the operator graph, hidden variables, collapsed variables, complements, and
competing implementations.

## Quick Start

Run commands from the repo root:

```powershell
python -m ontology.cli expand "I need belonging."
python -m ontology.cli expand "Good engineers know heap internals."
python -m ontology.cli collapsed "Harmony is important."
python -m ontology.cli graph "I am a teacher."
python examples/run_examples.py
```

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
