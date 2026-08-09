from __future__ import annotations

import re
from dataclasses import replace

from ontology.catalog import Fragment, matching_fragments
from ontology.schema import (
    Branch,
    Compilation,
    CompilerState,
    Diagnostic,
    Edge,
    Evidence,
    GraphIR,
    Node,
    Projection,
    ProjectionLoss,
)

PROJECTION_SAFETY_INVARIANT = (
    "Every projection records what it omitted or merged and why that was safe."
)


class SemanticCompiler:
    """Compiler for the three-example vertical slice.

    Sentence-shape parsers are generic. Semantic expansions live in contextual
    catalog fragments and are always emitted as unresolved candidates.
    """

    def compile(self, sentence: str, context: dict[str, str] | None = None) -> Compilation:
        context = dict(context or {})
        parsed = self._parse(sentence)
        resolved = self._resolve(sentence, parsed)
        factorized = self._factorize(sentence, resolved)
        validated = self._validate(sentence, factorized)
        states = (
            CompilerState(
                "parsed",
                parsed,
                "Parsing preserves source claims and introduces no catalog semantics.",
            ),
            CompilerState(
                "resolved",
                resolved,
                "Resolution binds local symbols to candidate fragments without selecting one.",
            ),
            CompilerState(
                "factorized",
                factorized,
                "Factorization adds candidates with provenance; alternatives remain unresolved.",
            ),
            CompilerState(
                "validated",
                validated,
                "Unsupported inferred edges are marked, never silently promoted or discarded.",
            ),
        )
        projections = tuple(
            self.project(validated, view)
            for view in ("factor", "implementation", "compression_loss")
        )
        return Compilation(sentence, context, states, projections)

    def project(self, graph: GraphIR, name: str) -> Projection:
        relations_by_view = {
            "factor": {
                "needs",
                "knows",
                "factors_into",
                "uses_evaluator",
                "evaluates",
                "yields",
                "sensitive_to",
                "has_property",
            },
            "implementation": {
                "implemented_by",
                "affects",
                "uses_evaluator",
                "evaluates",
                "yields",
            },
            "compression_loss": {
                "factors_into",
                "implemented_by",
                "affects",
                "sensitive_to",
                "has_property",
                "treated_as_equivalent_to",
                "distinct_from",
            },
        }
        if name not in relations_by_view:
            raise ValueError(f"Unknown projection: {name}")

        kept_edges = tuple(edge for edge in graph.edges if edge.relation in relations_by_view[name])
        kept_edge_ids = {edge.id for edge in kept_edges}
        kept_node_ids = {item for edge in kept_edges for item in (edge.source, edge.target)}
        kept_nodes = tuple(node for node in graph.nodes if node.id in kept_node_ids)
        kept_branches = tuple(
            replace(branch, edge_ids=tuple(edge for edge in branch.edge_ids if edge in kept_edge_ids))
            for branch in graph.branches
            if any(edge in kept_edge_ids for edge in branch.edge_ids)
        )
        omitted_edges = tuple(edge.id for edge in graph.edges if edge.id not in kept_edge_ids)
        omitted_nodes = tuple(node.id for node in graph.nodes if node.id not in kept_node_ids)
        loss = ProjectionLoss(
            action="omitted",
            item_ids=(*omitted_edges, *omitted_nodes),
            reason=f"Items are outside the {name} operation.",
            safe_because=(
                "The validated graph remains unchanged and addressable; this view omits only "
                "operation-irrelevant items and records their ids."
            ),
        )
        projected = GraphIR(
            nodes=kept_nodes,
            edges=kept_edges,
            branches=kept_branches,
            diagnostics=graph.diagnostics,
        )
        return Projection(name, projected, (loss,))

    def _parse(self, sentence: str) -> GraphIR:
        for parser in (self._parse_need, self._parse_importance, self._parse_good_group):
            graph = parser(sentence)
            if graph is not None:
                return graph
        return GraphIR(
            diagnostics=(
                Diagnostic("unsupported_sentence_shape", "No vertical-slice parser matched."),
            )
        )

    def _parse_need(self, sentence: str) -> GraphIR | None:
        match = re.fullmatch(
            r"\s*(?P<agent>I)\s+need\s+(?P<theme>[A-Za-z][\w -]*?)[.!?]?\s*",
            sentence,
            re.IGNORECASE,
        )
        if not match:
            return None
        theme = _slug(match.group("theme"))
        evidence = (_source_evidence(sentence, match.span()),)
        return GraphIR(
            nodes=(Node("speaker", "speaker"), Node(theme, match.group("theme").lower())),
            edges=(Edge("claim.need", "speaker", "needs", theme, "asserted", evidence),),
        )

    def _parse_importance(self, sentence: str) -> GraphIR | None:
        match = re.fullmatch(
            r"\s*(?P<target>[A-Za-z][\w -]*?)\s+is\s+(?P<evaluator>important)[.!?]?\s*",
            sentence,
            re.IGNORECASE,
        )
        if not match:
            return None
        target = _slug(match.group("target"))
        evidence = (_source_evidence(sentence, match.span()),)
        return GraphIR(
            nodes=(
                Node(target, match.group("target").lower()),
                Node("important_evaluator", "important"),
                Node("importance_evaluation", "importance evaluation"),
                Node("positive_importance", "positive importance judgment"),
            ),
            edges=(
                Edge(
                    "importance.uses",
                    "importance_evaluation",
                    "uses_evaluator",
                    "important_evaluator",
                    "asserted",
                    evidence,
                ),
                Edge(
                    "importance.target",
                    "importance_evaluation",
                    "evaluates",
                    target,
                    "asserted",
                    evidence,
                ),
                Edge(
                    "importance.result",
                    "importance_evaluation",
                    "yields",
                    "positive_importance",
                    "asserted",
                    evidence,
                ),
            ),
        )

    def _parse_good_group(self, sentence: str) -> GraphIR | None:
        match = re.fullmatch(
            r"\s*(?P<evaluator>good)\s+(?P<group>[A-Za-z]+)\s+"
            r"(?P<predicate>know)\s+(?P<object>[A-Za-z][\w -]*?)[.!?]?\s*",
            sentence,
            re.IGNORECASE,
        )
        if not match:
            return None
        group = _singular(match.group("group"))
        subject_id = f"good_{group}"
        object_id = _slug(match.group("object"))
        evidence = (_source_evidence(sentence, match.span()),)
        return GraphIR(
            nodes=(
                Node(subject_id, f"good {group}"),
                Node(object_id, match.group("object").lower()),
                Node("good_evaluator", "good"),
                Node(f"{group}_configuration", f"{group} configuration"),
            ),
            edges=(
                Edge(
                    "claim.good_group_knows",
                    subject_id,
                    "knows",
                    object_id,
                    "asserted",
                    evidence,
                    (("modality", "generic"),),
                ),
            ),
        )

    def _resolve(self, sentence: str, graph: GraphIR) -> GraphIR:
        labels = {node.label for node in graph.nodes}
        additions_nodes: list[Node] = []
        additions_edges: list[Edge] = []
        for fragment in matching_fragments(labels):
            trigger_node = next(node for node in graph.nodes if node.label == fragment.trigger)
            fragment_node_id = f"fragment.{_slug(fragment.id)}"
            additions_nodes.append(Node(fragment_node_id, fragment.id))
            additions_edges.append(
                Edge(
                    f"match.{_slug(fragment.id)}",
                    trigger_node.id,
                    "lexically_matches",
                    fragment_node_id,
                    "inferred",
                    (
                        _source_evidence(sentence, _label_span(sentence, trigger_node.label)),
                        Evidence("catalog_fragment", fragment.id),
                        Evidence("inference_rule", "exact_local_trigger_match"),
                    ),
                )
            )

        resolved = graph.with_items(nodes=tuple(additions_nodes), edges=tuple(additions_edges))
        good_claims = [edge for edge in graph.edges if edge.id == "claim.good_group_knows"]
        if good_claims:
            claim = good_claims[0]
            source = _source_evidence(sentence, (0, len(sentence)))
            provenance = (source, Evidence("inference_rule", "good_group_reading_split"))
            evaluation = "good_engineer_evaluation"
            configuration = next(
                node.id for node in graph.nodes if node.label.endswith(" configuration")
            )
            branch_edges = (
                Edge(
                    "good.reading.uses",
                    evaluation,
                    "uses_evaluator",
                    "good_evaluator",
                    "unresolved",
                    provenance,
                ),
                Edge(
                    "good.reading.evaluates",
                    evaluation,
                    "evaluates",
                    configuration,
                    "unresolved",
                    provenance,
                ),
                Edge(
                    "good.reading.normative",
                    "good_evaluator",
                    "sensitive_to",
                    claim.target,
                    "unresolved",
                    provenance,
                ),
                Edge(
                    "good.reading.descriptive",
                    claim.source,
                    "has_property",
                    claim.target,
                    "unresolved",
                    provenance,
                ),
            )
            branches = (
                Branch(
                    "good.normative_branch",
                    "normative evaluator criterion",
                    (
                        "good.reading.uses",
                        "good.reading.evaluates",
                        "good.reading.normative",
                    ),
                    "exclusive",
                    "unresolved",
                    provenance,
                ),
                Branch(
                    "good.descriptive_branch",
                    "descriptive generalization",
                    ("good.reading.descriptive",),
                    "exclusive",
                    "unresolved",
                    provenance,
                ),
            )
            resolved = resolved.with_items(
                nodes=(Node(evaluation, "good engineer evaluation"),),
                edges=branch_edges,
                branches=branches,
            )
        return resolved

    def _factorize(self, sentence: str, graph: GraphIR) -> GraphIR:
        matches = [edge for edge in graph.edges if edge.relation == "lexically_matches"]
        result = graph
        fragments_by_id = {fragment.id: fragment for fragment in matching_fragments({n.label for n in graph.nodes})}
        for match in matches:
            fragment_id = graph.node(match.target).label
            fragment = fragments_by_id[fragment_id]
            result = self._instantiate_fragment(sentence, result, fragment, match.source)
        return result

    def _instantiate_fragment(
        self,
        sentence: str,
        graph: GraphIR,
        fragment: Fragment,
        trigger_node_id: str,
    ) -> GraphIR:
        source = _source_evidence(sentence, _label_span(sentence, graph.node(trigger_node_id).label))
        provenance = (
            source,
            Evidence("catalog_fragment", fragment.id),
            Evidence("inference_rule", "instantiate_candidate_fragment"),
        )
        nodes = tuple(Node(node_id, label) for node_id, label in fragment.node_labels)
        edges = tuple(
            Edge(
                template.id,
                trigger_node_id if template.source == "$trigger" else template.source,
                template.relation,
                template.target,
                "unresolved",
                provenance,
                template.qualifiers,
            )
            for template in fragment.edges
        )
        branches = tuple(
            Branch(
                template.id,
                template.label,
                template.edge_ids,
                template.mode,
                "unresolved",
                provenance,
            )
            for template in fragment.branches
        )
        return graph.with_items(nodes=nodes, edges=edges, branches=branches)

    def _validate(self, sentence: str, graph: GraphIR) -> GraphIR:
        diagnostics: list[Diagnostic] = []
        validated_edges: list[Edge] = []
        for edge in graph.edges:
            if edge.status == "asserted":
                validated_edges.append(edge)
                continue
            kinds = {item.kind for item in edge.provenance}
            has_source = "source_text" in kinds
            has_derivation = bool(
                kinds & {"catalog_fragment", "inference_rule", "model_hypothesis"}
            )
            if not (has_source and has_derivation):
                validated_edges.append(replace(edge, status="unsupported"))
                diagnostics.append(
                    Diagnostic(
                        "missing_provenance",
                        "Inferred edge lacks source or derivation provenance.",
                        (edge.id,),
                    )
                )
                continue
            if edge.relation == "treated_as_equivalent_to" and not re.search(
                r"\b(same as|equivalent to|equals?)\b|=", sentence, re.IGNORECASE
            ):
                validated_edges.append(replace(edge, status="unsupported"))
                diagnostics.append(
                    Diagnostic(
                        "unsupported_equivalence",
                        "The source does not assert equivalence; nodes remain distinct.",
                        (edge.id,),
                    )
                )
                continue
            validated_edges.append(edge)

        for branch in graph.branches:
            kinds = {item.kind for item in branch.provenance}
            if "source_text" not in kinds or not kinds.intersection(
                {"catalog_fragment", "inference_rule", "model_hypothesis"}
            ):
                diagnostics.append(
                    Diagnostic(
                        "missing_branch_provenance",
                        "Unresolved branch lacks source or derivation provenance.",
                        (branch.id,),
                    )
                )
        if graph.branches:
            diagnostics.append(
                Diagnostic(
                    "unresolved_alternatives",
                    "Candidate branches were intentionally preserved.",
                    tuple(branch.id for branch in graph.branches),
                )
            )
        return graph.replace_edges(tuple(validated_edges)).with_items(
            diagnostics=tuple(diagnostics)
        )


def render_projection(projection: Projection) -> str:
    graph = projection.graph
    labels = {node.id: node.label for node in graph.nodes}
    lines = [f"{projection.name.replace('_', ' ').title()} view"]
    for edge in graph.edges:
        qualifier = ""
        if edge.qualifiers:
            qualifier = " " + ", ".join(f"{key}={value}" for key, value in edge.qualifiers)
        lines.append(
            f"- {labels[edge.source]} --{edge.relation}{qualifier}--> "
            f"{labels[edge.target]} [{edge.status}]"
        )
    if graph.branches:
        lines.append("Unresolved branches:")
        for branch in graph.branches:
            lines.append(f"- {branch.label} ({branch.mode})")
    lines.append("Projection loss ledger:")
    for loss in projection.losses:
        lines.append(
            f"- {loss.action} {len(loss.item_ids)} item(s): {loss.reason} "
            f"Safe because: {loss.safe_because}"
        )
    return "\n".join(lines)


def _source_evidence(sentence: str, span: tuple[int, int]) -> Evidence:
    return Evidence("source_text", "input", span, sentence[span[0] : span[1]])


def _label_span(sentence: str, label: str) -> tuple[int, int]:
    match = re.search(re.escape(label), sentence, re.IGNORECASE)
    return match.span() if match else (0, len(sentence))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _singular(value: str) -> str:
    lowered = value.lower()
    return lowered[:-1] if lowered.endswith("s") else lowered
