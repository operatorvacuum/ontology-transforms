from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology import TransformAPI, load_default_ontology


api = TransformAPI(load_default_ontology())

for sentence in [
    "I need belonging.",
    "Harmony is important.",
    "I am X.",
    "Harmony is important with signal preservation.",
]:
    print(json.dumps(api.expand(sentence).to_dict(), indent=2))
