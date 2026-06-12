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

## Example Outputs

### Collapsed Hiring Signal

```powershell
python -m ontology.cli expand "Good engineers know heap internals."
```

```json
{
  "sentence": "Good engineers know heap internals.",
  "objects": [],
  "operators": ["compression", "prediction"],
  "compressions": [],
  "collapsed_variables": [
    {
      "collapse": "trivia_knowledge = engineering_value",
      "missing_variables": [
        "judgment",
        "debugging",
        "system_modeling",
        "AI_navigation",
        "curiosity"
      ],
      "evidence": "trivia_hiring"
    }
  ],
  "hidden_variables": [
    "judgment",
    "debugging",
    "system_modeling",
    "AI_navigation",
    "curiosity"
  ],
  "complements": ["signal_preservation", "adaptation"],
  "competing_implementations": [],
  "warnings": ["complement not represented"]
}
```

### Harmony Collapse

```powershell
python -m ontology.cli expand "Harmony is important."
```

```json
{
  "sentence": "Harmony is important.",
  "objects": ["harmony"],
  "operators": ["coordination", "prediction", "compression"],
  "compressions": ["Harmony is important", "keep the peace"],
  "collapsed_variables": [
    {
      "collapse": "harmony = truth",
      "missing_variables": [
        "contradiction",
        "signal_preservation",
        "disagreement_as_information"
      ],
      "evidence": "harmony_truth_collapse"
    },
    {
      "collapse": "harmony = health",
      "missing_variables": [
        "contradiction",
        "signal_preservation",
        "disagreement_as_information"
      ],
      "evidence": "harmony_truth_collapse"
    }
  ],
  "hidden_variables": [
    "harmony_is_single_object",
    "coordination_can_be_obtained_without_signal_loss",
    "unresolved disagreement",
    "power difference",
    "private dissent",
    "cost of silence",
    "contradiction",
    "signal_preservation",
    "disagreement_as_information"
  ],
  "complements": ["signal_preservation", "exit", "adaptation"],
  "competing_implementations": [
    "conflict suppression",
    "conflict resolution",
    "prediction reduction",
    "explicit negotiation"
  ],
  "warnings": ["complement not represented"]
}
```

### Identity Compression

```powershell
python -m ontology.cli expand "I am a teacher."
```

```json
{
  "sentence": "I am a teacher.",
  "objects": ["identity"],
  "operators": ["compression", "coordination"],
  "compressions": ["I am X", "we are X"],
  "collapsed_variables": [
    {
      "collapse": "identity = behavior",
      "missing_variables": [
        "frequency",
        "context",
        "competence",
        "role",
        "obligation"
      ],
      "evidence": "identity_behavior_collapse"
    }
  ],
  "hidden_variables": [
    "identity_is_single_object",
    "compressed_label_is_real_self",
    "individual differences",
    "local context",
    "temporal change",
    "frequency",
    "context",
    "competence",
    "role",
    "obligation"
  ],
  "complements": ["signal_preservation", "exit"],
  "competing_implementations": [
    "role",
    "current preference",
    "relationship-specific behavior",
    "history",
    "chosen commitment"
  ],
  "warnings": ["complement not represented"]
}
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
