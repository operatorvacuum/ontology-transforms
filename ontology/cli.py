from __future__ import annotations

import argparse
import json

from ontology import SemanticCompiler, render_projection


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile language into a candidate semantic graph.")
    parser.add_argument("sentence")
    parser.add_argument(
        "--view",
        choices=("factor", "implementation", "compression_loss"),
        default="factor",
    )
    parser.add_argument("--ir", action="store_true", help="Emit all machine IR states as JSON.")
    args = parser.parse_args()

    compilation = SemanticCompiler().compile(args.sentence)
    if args.ir:
        print(json.dumps(compilation.to_dict(), indent=2))
    else:
        print(render_projection(compilation.projection(args.view)))


if __name__ == "__main__":
    main()
