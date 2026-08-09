from __future__ import annotations

import argparse
import json
import sys

from ontology import SemanticCompiler, render_projection


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Compile language into a candidate semantic graph.")
    parser.add_argument("sentence")
    parser.add_argument(
        "--view",
        choices=("factor", "implementation", "compression_loss"),
        default="factor",
    )
    parser.add_argument("--ir", action="store_true", help="Emit all machine IR states as JSON.")
    parser.add_argument(
        "--depth",
        type=int,
        default=0,
        help="Recursive candidate-expansion depth for projections.",
    )
    args = parser.parse_args()

    compilation = SemanticCompiler().compile(args.sentence, projection_depth=args.depth)
    if args.ir:
        print(json.dumps(compilation.to_dict(), indent=2))
    else:
        print(render_projection(compilation.projection(args.view), compilation.sentence))


if __name__ == "__main__":
    main()
