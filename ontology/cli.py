from __future__ import annotations

import argparse
import json
import sys

from ontology import (
    ItemId,
    OperationId,
    RecompositionGuard,
    RecompositionOperation,
    SemanticCompiler,
    render_projection,
    render_recomposition_decision,
)
from ontology.recomposition_cases import proposal_for, proposals_for


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
    parser.add_argument(
        "--operation",
        help="Task-scoped recomposition operation id; distinct from candidate text.",
    )
    recomposition_mode = parser.add_mutually_exclusive_group()
    recomposition_mode.add_argument(
        "--recompose",
        metavar="STATEMENT",
        help="Evaluate one fixture-scoped candidate compact statement.",
    )
    recomposition_mode.add_argument(
        "--retain-if-none",
        action="store_true",
        help="Try registered fixture proposals and retain the graph if none is safe.",
    )
    parser.add_argument(
        "--select-branch",
        action="append",
        default=[],
        metavar="BRANCH_ID",
        help="License one explicit candidate branch for this operation only.",
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
    recomposition_requested = bool(args.recompose or args.retain_if_none)
    if recomposition_requested and not args.operation:
        parser.error("--operation is required with --recompose or --retain-if-none")
    if args.select_branch and not recomposition_requested:
        parser.error("--select-branch requires --recompose or --retain-if-none")
    if recomposition_requested:
        operation = RecompositionOperation(
            OperationId(args.operation),
            tuple(ItemId(branch_id) for branch_id in args.select_branch),
        )
        proposals = proposals_for(args.sentence, args.operation)
        if args.recompose:
            candidate = proposal_for(args.sentence, args.operation, args.recompose)
            if candidate is None:
                available = ", ".join(item.label for item in proposals) or "none"
                parser.error(
                    "no fixture-scoped proposal matches --recompose; "
                    f"available for this sentence/operation: {available}"
                )
            decision = RecompositionGuard().evaluate_candidate(
                compilation.graph, candidate, operation
            )
        else:
            if not proposals:
                parser.error("no fixture-scoped proposals exist for this sentence/operation")
            candidate = None
            decision = RecompositionGuard().decide(
                compilation.graph, proposals, operation
            )
        if args.ir:
            print(
                json.dumps(
                    {
                        "operation": operation.to_dict(),
                        "candidate": candidate.to_dict() if candidate else None,
                        "decision": decision.to_dict(),
                    },
                    indent=2,
                )
            )
        else:
            print(
                render_recomposition_decision(
                    compilation.graph, operation, decision, candidate
                )
            )
        return
    if args.ir:
        print(json.dumps(compilation.to_dict(), indent=2))
    else:
        print(render_projection(compilation.projection(args.view), compilation.sentence))


if __name__ == "__main__":
    main()
