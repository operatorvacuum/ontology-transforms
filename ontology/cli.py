from __future__ import annotations

import argparse
import json

from ontology import TransformAPI, load_default_ontology


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform language into an operator ontology.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    expand_parser = subparsers.add_parser("expand")
    expand_parser.add_argument("sentence")

    graph_parser = subparsers.add_parser("graph")
    graph_parser.add_argument("sentence")

    collapsed_parser = subparsers.add_parser("collapsed")
    collapsed_parser.add_argument("sentence")

    args = parser.parse_args()
    api = TransformAPI(load_default_ontology())

    if args.command == "expand":
        payload = api.expand(args.sentence).to_dict()
    elif args.command == "graph":
        payload = api.extract_operator_graph(args.sentence).to_dict()
    else:
        payload = [item.to_dict() for item in api.detect_collapsed_variables(args.sentence)]

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
