from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology import SemanticCompiler, render_projection


compiler = SemanticCompiler()
examples = (
    ("I need belonging.", "factor"),
    ("Harmony is important.", "implementation"),
    ("Good engineers know heap internals.", "factor"),
)

for sentence, view in examples:
    compilation = compiler.compile(sentence)
    print(sentence)
    print(render_projection(compilation.projection(view)))
    print()
