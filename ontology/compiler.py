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

    def compile(
        self,
        sentence: str,
        context: dict[str, str] | None = None,
        projection_depth: int = 0,
    ) -> Compilation:
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
            self.project(validated, view, projection_depth)
            for view in ("factor", "implementation", "compression_loss")
        )
        return Compilation(sentence, context, states, projections)

    def project(self, graph: GraphIR, name: str, depth: int = 0) -> Projection:
        relations_by_view = {
            "factor": {
                "needs",
                "knows",
                "set",
                "requires",
                "has_agent",
                "has_target",
                "factors_into",
                "uses_evaluator",
                "evaluates",
                "yields",
                "sensitive_to",
                "tend_to_have",
            },
            "implementation": {
                "implemented_by",
                "affects",
                "uses_evaluator",
                "evaluates",
                "yields",
            },
            "compression_loss": {
                "set",
                "requires",
                "has_agent",
                "has_target",
                "factors_into",
                "implemented_by",
                "affects",
                "sensitive_to",
                "tend_to_have",
                "treated_as_equivalent_to",
                "distinct_from",
            },
        }
        if name not in relations_by_view:
            raise ValueError(f"Unknown projection: {name}")
        if depth < 0:
            raise ValueError("Projection depth must be non-negative")

        edge_depths: dict[str, int] = {}
        for branch in graph.branches:
            for edge_id in branch.edge_ids:
                edge_depths[edge_id] = min(edge_depths.get(edge_id, branch.depth), branch.depth)
        kept_edges = tuple(
            edge
            for edge in graph.edges
            if edge.relation in relations_by_view[name]
            and edge_depths.get(edge.id, 0) <= depth
        )
        kept_edge_ids = {edge.id for edge in kept_edges}
        kept_node_ids = {item for edge in kept_edges for item in (edge.source, edge.target)}
        kept_nodes = tuple(node for node in graph.nodes if node.id in kept_node_ids)
        active_group_ids = {
            branch.group_id
            for branch in graph.branches
            if any(edge in kept_edge_ids for edge in branch.edge_ids)
        }
        kept_branches = tuple(
            replace(branch, edge_ids=tuple(edge for edge in branch.edge_ids if edge in kept_edge_ids))
            for branch in graph.branches
            if branch.group_id in active_group_ids
        )
        losses = self._projection_losses(
            graph,
            name,
            depth,
            edge_depths,
            kept_edge_ids,
            kept_node_ids,
        )
        projected = GraphIR(
            nodes=kept_nodes,
            edges=kept_edges,
            branches=kept_branches,
            diagnostics=graph.diagnostics,
        )
        return Projection(name, projected, losses, depth)

    def _projection_losses(
        self,
        graph: GraphIR,
        view: str,
        depth: int,
        edge_depths: dict[str, int],
        kept_edge_ids: set[str],
        kept_node_ids: set[str],
    ) -> tuple[ProjectionLoss, ...]:
        safe_for = {
            "factor": "inspecting retained candidate decompositions and evaluator readings",
            "implementation": "comparing retained candidate implementations and their effects",
            "compression_loss": "inspecting distinctions retained by the compression-loss view",
        }[view]
        unsafe_by_role = {
            "resolution provenance": "auditing why a catalog fragment was activated",
            "source assertion": "recovering the complete claim made by the source text",
            "evaluator application": "inferring why or how a target received a judgment",
            "candidate decomposition": "inspecting the target's candidate factor structure",
            "candidate implementation": "comparing possible implementations and their effects",
            "candidate interpretation": "distinguishing competing readings of the source claim",
            "recursive candidate expansion": (
                "inspecting the recursively factorized candidate and its optional dimensions"
            ),
            "supporting symbol": "resolving relationships omitted from this projection",
        }
        resolution_reason = {
            "factor": (
                "factor view omits the trigger link because it inspects the activated "
                "candidate factors and readings"
            ),
            "implementation": (
                "implementation view omits the trigger link because it compares activated "
                "realizations and their effects"
            ),
            "compression_loss": (
                "compression-loss view omits the trigger link because it inspects semantic "
                "distinctions, not catalog activation"
            ),
        }[view]
        reason_by_role = {
            "resolution provenance": resolution_reason,
            "source assertion": f"{view} view excludes source relations outside its operation",
            "evaluator application": f"{view} view excludes judgment mechanics outside its operation",
            "candidate decomposition": f"{view} view excludes factor relations outside its operation",
            "candidate implementation": (
                f"{view} view excludes implementation relations outside its operation"
            ),
            "candidate interpretation": (
                f"{view} view excludes interpretation relations outside its operation"
            ),
            "recursive candidate expansion": (
                f"projection depth {depth} stops before recursively factorizing candidate nodes"
            ),
            "supporting symbol": f"{view} view excludes symbols left unreferenced by retained edges",
        }

        omitted_node_ids = {node.id for node in graph.nodes if node.id not in kept_node_ids}
        assigned_nodes: set[str] = set()
        losses: list[ProjectionLoss] = []
        recursive_edges = tuple(
            edge
            for edge in graph.edges
            if edge.id not in kept_edge_ids and edge_depths.get(edge.id, 0) > depth
        )
        recursive_edge_ids = {edge.id for edge in recursive_edges}
        if recursive_edges:
            recursive_node_ids = tuple(
                dict.fromkeys(
                    node_id
                    for edge in recursive_edges
                    for node_id in (edge.source, edge.target)
                    if node_id in omitted_node_ids
                )
            )
            assigned_nodes.update(recursive_node_ids)
            recursive_branch_ids = tuple(
                branch.id
                for branch in graph.branches
                if branch.depth > depth
                and any(edge_id in recursive_edge_ids for edge_id in branch.edge_ids)
            )
            source_labels = tuple(
                dict.fromkeys(graph.node(edge.source).label for edge in recursive_edges)
            )
            losses.append(
                ProjectionLoss(
                    action="omitted",
                    item_ids=(
                        *(edge.id for edge in recursive_edges),
                        *recursive_branch_ids,
                        *recursive_node_ids,
                    ),
                    description=(
                        f"recursive expansion of {', '.join(source_labels)}: "
                        f"{len(recursive_edges)} optional candidate members hidden at depth {depth}"
                    ),
                    semantic_role="recursive candidate expansion",
                    reason=reason_by_role["recursive candidate expansion"],
                    safe_for="comparing interpretations directly licensed at the current depth",
                    unsafe_for=unsafe_by_role["recursive candidate expansion"],
                )
            )
        recursive_branch_ids = {
            branch.id for branch in graph.branches if branch.depth > depth
        }
        for branch in graph.branches:
            if branch.id in recursive_branch_ids:
                continue
            if any(edge_id in kept_edge_ids for edge_id in branch.edge_ids):
                continue
            branch_edges = tuple(graph.edge(edge_id) for edge_id in branch.edge_ids)
            role = (
                _semantic_role(branch_edges[0].relation, branch_edges[0].status)
                if branch_edges
                else "candidate interpretation"
            )
            losses.append(
                ProjectionLoss(
                    action="omitted",
                    item_ids=(branch.id,),
                    description=f"candidate branch {branch.label}",
                    semantic_role=role,
                    reason=reason_by_role[role],
                    safe_for=safe_for,
                    unsafe_for=unsafe_by_role[role],
                )
            )
        for edge in graph.edges:
            if edge.id in kept_edge_ids or edge.id in recursive_edge_ids:
                continue
            role = _semantic_role(edge.relation, edge.status)
            endpoint_ids = tuple(
                node_id
                for node_id in (edge.source, edge.target)
                if node_id in omitted_node_ids and node_id not in assigned_nodes
            )
            assigned_nodes.update(endpoint_ids)
            losses.append(
                ProjectionLoss(
                    action="omitted",
                    item_ids=(edge.id, *endpoint_ids),
                    description=_edge_description(graph, edge),
                    semantic_role=role,
                    reason=reason_by_role[role],
                    safe_for=safe_for,
                    unsafe_for=unsafe_by_role[role],
                )
            )

        unassigned_nodes = tuple(node_id for node_id in omitted_node_ids if node_id not in assigned_nodes)
        if unassigned_nodes:
            labels = ", ".join(graph.node(node_id).label for node_id in unassigned_nodes)
            losses.append(
                ProjectionLoss(
                    action="omitted",
                    item_ids=unassigned_nodes,
                    description=labels,
                    semantic_role="supporting symbol",
                    reason=reason_by_role["supporting symbol"],
                    safe_for=safe_for,
                    unsafe_for=unsafe_by_role["supporting symbol"],
                )
            )
        return tuple(losses)

    def _parse(self, sentence: str) -> GraphIR:
        for parser in (
            self._parse_need,
            self._parse_importance,
            self._parse_evaluated_category_requirement,
            self._parse_role_should_action,
            self._parse_good_group,
            self._parse_good_group_action,
        ):
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

    def _parse_evaluated_category_requirement(self, sentence: str) -> GraphIR | None:
        match = re.fullmatch(
            r"\s*(?P<evaluator>[A-Za-z]+)\s+(?P<category>[A-Za-z]+)\s+"
            r"require\s+(?P<object>[A-Za-z][\w -]*?)[.!?]?\s*",
            sentence,
            re.IGNORECASE,
        )
        if not match:
            return None
        category = _singular(match.group("category"))
        lexical_handle = _slug(f"{match.group('evaluator')} {match.group('category')}")
        object_id = _slug(match.group("object"))
        evaluator_id = f"{_slug(match.group('evaluator'))}_{category}_evaluator"
        configuration_id = f"{category}_configuration"
        evidence = (_source_evidence(sentence, match.span()),)
        return GraphIR(
            nodes=(
                Node(
                    lexical_handle,
                    f"{match.group('evaluator').lower()} {match.group('category').lower()}",
                ),
                Node(object_id, match.group("object").lower()),
                Node(evaluator_id, f"{match.group('evaluator').lower()}-{category} evaluator"),
                Node(configuration_id, f"{category} configuration"),
            ),
            edges=(
                Edge(
                    "claim.evaluated_category_requires",
                    lexical_handle,
                    "requires",
                    object_id,
                    "asserted",
                    evidence,
                    (("modality", "generic"),),
                ),
            ),
        )

    def _parse_role_should_action(self, sentence: str) -> GraphIR | None:
        match = re.fullmatch(
            r"\s*(?:a|an)\s+(?P<role>[A-Za-z]+)\s+should\s+"
            r"(?P<action>[A-Za-z]+)\s+(?P<target>you)[.!?]?\s*",
            sentence,
            re.IGNORECASE,
        )
        if not match:
            return None
        role_id = f"{_slug(match.group('role'))}_role"
        action_id = f"{_slug(match.group('action'))}_action"
        target_id = "addressee"
        evidence = (_source_evidence(sentence, match.span()),)
        return GraphIR(
            nodes=(
                Node(role_id, f"{match.group('role').lower()} role"),
                Node(action_id, f"{match.group('action').lower()} action"),
                Node(target_id, "addressee"),
                Node("should_evaluator", "should evaluator"),
                Node("should_evaluation", "should evaluation"),
                Node("positive_normative_evaluation", "positive normative evaluation"),
            ),
            edges=(
                Edge("claim.action.agent", action_id, "has_agent", role_id, "asserted", evidence),
                Edge("claim.action.target", action_id, "has_target", target_id, "asserted", evidence),
                Edge(
                    "claim.should.uses",
                    "should_evaluation",
                    "uses_evaluator",
                    "should_evaluator",
                    "asserted",
                    evidence,
                ),
                Edge(
                    "claim.should.evaluates",
                    "should_evaluation",
                    "evaluates",
                    action_id,
                    "asserted",
                    evidence,
                ),
                Edge(
                    "claim.should.result",
                    "should_evaluation",
                    "yields",
                    "positive_normative_evaluation",
                    "asserted",
                    evidence,
                ),
            ),
            diagnostics=(
                Diagnostic(
                    "unresolved_normative_bearer",
                    "Normative evaluation of the action does not assign an obligation bearer.",
                    ("claim.should.evaluates",),
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
                Node(subject_id, match.group("evaluator").lower() + " " + match.group("group").lower()),
                Node(object_id, match.group("object").lower()),
                Node("good_evaluator", f"good-{group} evaluator"),
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

    def _parse_good_group_action(self, sentence: str) -> GraphIR | None:
        match = re.fullmatch(
            r"\s*(?P<evaluator>good)\s+(?P<group>[A-Za-z]+)\s+"
            r"(?P<predicate>set)\s+(?P<object>[A-Za-z][\w -]*?)[.!?]?\s*",
            sentence,
            re.IGNORECASE,
        )
        if not match:
            return None
        group = _singular(match.group("group"))
        source_handle = f"good_{group}s"
        object_id = _slug(match.group("object"))
        action_id = f"{_slug(match.group('object'))}_setting_action"
        evidence = (_source_evidence(sentence, match.span()),)
        return GraphIR(
            nodes=(
                Node(source_handle, f"good {match.group('group').lower()}"),
                Node(object_id, match.group("object").lower()),
                Node(action_id, f"{match.group('object').lower()} setting action"),
                Node("good_parent_evaluator", "good-parent evaluator"),
                Node(f"{group}_configuration", f"{group} configuration"),
                Node("parents_judged_good", "parents judged good"),
            ),
            edges=(
                Edge(
                    "claim.good_group_action",
                    source_handle,
                    "set",
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
        requirement_claims = [
            edge for edge in graph.edges if edge.id == "claim.evaluated_category_requires"
        ]
        if requirement_claims:
            claim = requirement_claims[0]
            source = _source_evidence(sentence, (0, len(sentence)))
            provenance = (
                source,
                Evidence("inference_rule", "evaluated_category_requirement_readings"),
            )
            category = next(
                node for node in graph.nodes if node.id.endswith("_configuration")
            )
            evaluator = next(
                node for node in graph.nodes if node.id.endswith("_evaluator")
            )
            evaluation_id = f"{category.id}_health_evaluation"
            candidate_edges = (
                Edge(
                    "requirement.evaluator.uses",
                    evaluation_id,
                    "uses_evaluator",
                    evaluator.id,
                    "unresolved",
                    provenance,
                ),
                Edge(
                    "requirement.evaluator.evaluates",
                    evaluation_id,
                    "evaluates",
                    category.id,
                    "unresolved",
                    provenance,
                ),
                Edge(
                    "requirement.evaluator.criterion",
                    evaluator.id,
                    "sensitive_to",
                    claim.target,
                    "unresolved",
                    provenance,
                ),
                Edge(
                    "requirement.configuration.necessity",
                    category.id,
                    "requires",
                    claim.target,
                    "unresolved",
                    provenance,
                ),
            )
            branches = (
                Branch(
                    "requirement.evaluator_reading",
                    "requirement.direct_readings",
                    "evaluator criterion",
                    (
                        "requirement.evaluator.uses",
                        "requirement.evaluator.evaluates",
                        "requirement.evaluator.criterion",
                    ),
                    "one_or_more",
                    "unresolved",
                    provenance,
                ),
                Branch(
                    "requirement.configuration_reading",
                    "requirement.direct_readings",
                    "configuration necessity",
                    ("requirement.configuration.necessity",),
                    "one_or_more",
                    "unresolved",
                    provenance,
                ),
            )
            resolved = resolved.with_items(
                nodes=(Node(evaluation_id, "relationship health evaluation"),),
                edges=candidate_edges,
                branches=branches,
            )

        good_action_claims = [
            edge for edge in graph.edges if edge.id == "claim.good_group_action"
        ]
        if good_action_claims:
            action_id = next(
                node.id for node in graph.nodes if node.id.endswith("_setting_action")
            )
            source = _source_evidence(sentence, (0, len(sentence)))
            provenance = (source, Evidence("inference_rule", "good_group_action_reading_split"))
            candidate_edges = (
                Edge(
                    "good_parent.reading.uses",
                    "good_parent_evaluation",
                    "uses_evaluator",
                    "good_parent_evaluator",
                    "unresolved",
                    provenance,
                ),
                Edge(
                    "good_parent.reading.evaluates",
                    "good_parent_evaluation",
                    "evaluates",
                    "parent_configuration",
                    "unresolved",
                    provenance,
                ),
                Edge(
                    "good_parent.reading.normative",
                    "good_parent_evaluator",
                    "sensitive_to",
                    action_id,
                    "unresolved",
                    provenance,
                ),
                Edge(
                    "good_parent.reading.descriptive",
                    "parents_judged_good",
                    "tend_to_have",
                    action_id,
                    "unresolved",
                    provenance,
                ),
            )
            resolved = resolved.with_items(
                nodes=(Node("good_parent_evaluation", "good parent evaluation"),),
                edges=candidate_edges,
                branches=(
                    Branch(
                        "good_parent.normative_branch",
                        "good_parent.primary_readings",
                        "normative evaluator criterion",
                        (
                            "good_parent.reading.uses",
                            "good_parent.reading.evaluates",
                            "good_parent.reading.normative",
                        ),
                        "exclusive",
                        "unresolved",
                        provenance,
                    ),
                    Branch(
                        "good_parent.descriptive_branch",
                        "good_parent.primary_readings",
                        "descriptive generalization",
                        ("good_parent.reading.descriptive",),
                        "exclusive",
                        "unresolved",
                        provenance,
                    ),
                ),
            )

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
                    "tend_to_have",
                    claim.target,
                    "unresolved",
                    provenance,
                ),
            )
            branches = (
                Branch(
                    "good.normative_branch",
                    "good.primary_readings",
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
                    "good.primary_readings",
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
                template.group_id,
                template.label,
                template.edge_ids,
                template.mode,
                "unresolved",
                provenance,
                template.depth,
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
        modes_by_group: dict[str, set[str]] = {}
        for branch in graph.branches:
            modes_by_group.setdefault(branch.group_id, set()).add(branch.mode)
        for group_id, modes in modes_by_group.items():
            if len(modes) > 1:
                diagnostics.append(
                    Diagnostic(
                        "inconsistent_branch_cardinality",
                        "Branches in one alternative group must use the same mode.",
                        tuple(
                            branch.id
                            for branch in graph.branches
                            if branch.group_id == group_id
                        ),
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


def render_projection(projection: Projection, sentence: str = "") -> str:
    graph = projection.graph
    labels = {node.id: node.label for node in graph.nodes}
    lines = ["INPUT", f"  {sentence or '(not supplied)'}", ""]

    branch_edge_ids = {edge_id for branch in graph.branches for edge_id in branch.edge_ids}
    asserted = tuple(
        edge for edge in graph.edges if edge.status == "asserted" and edge.id not in branch_edge_ids
    )
    lines.append("ASSERTED — source text")
    if asserted:
        for edge in asserted:
            lines.extend(_render_edge(edge, labels, "  "))
    else:
        lines.append("  none retained by this projection")

    all_groups: dict[str, list[Branch]] = {}
    for branch in graph.branches:
        all_groups.setdefault(branch.group_id, []).append(branch)
    groups = {
        group_id: branches
        for group_id, branches in all_groups.items()
        if branches[0].depth == 0
    }
    recursive_groups = {
        group_id: branches
        for group_id, branches in all_groups.items()
        if branches[0].depth > 0
    }
    if groups:
        lines.extend(("", "CANDIDATE BRANCHES"))
        _render_branch_groups(lines, groups, graph, labels)

    recursive_losses = tuple(
        loss
        for loss in projection.losses
        if loss.semantic_role == "recursive candidate expansion"
    )
    if recursive_groups:
        lines.extend(("", f"RECURSIVE CANDIDATE EXPANSION — depth {projection.depth}"))
        _render_branch_groups(lines, recursive_groups, graph, labels)
    elif recursive_losses:
        lines.extend(("", "RECURSIVE CANDIDATE EXPANSION"))
        for loss in recursive_losses:
            lines.append(f"  {loss.description}")
        lines.append(f"  inspect with: --depth {projection.depth + 1}")

    ungrouped = tuple(
        edge
        for edge in graph.edges
        if edge.id not in branch_edge_ids and edge.status != "asserted"
    )
    lines.extend(("", "UNRESOLVED"))
    if all_groups:
        for group_id, branches in all_groups.items():
            lines.append(f"  - {_unresolved_group_description(group_id, branches)}")
    if ungrouped:
        lines.append("  ungrouped candidates")
        for edge in ungrouped:
            lines.extend(_render_edge(edge, labels, "    "))
            lines.append(f"    [{_provenance_class(edge.provenance, edge.status)}]")
    unresolved_diagnostics = tuple(
        diagnostic
        for diagnostic in graph.diagnostics
        if diagnostic.code.startswith("unresolved_")
        and diagnostic.code != "unresolved_alternatives"
    )
    for diagnostic in unresolved_diagnostics:
        lines.append(f"  - {diagnostic.message}")
    if not all_groups and not ungrouped and not unresolved_diagnostics:
        lines.append("  none")

    lines.extend(("", "PROJECTION LOSS"))
    if not projection.losses:
        lines.append("  none")
    for loss in projection.losses:
        lines.append(f"  - {loss.action}: {loss.description}")
        lines.append(f"    semantic role: {loss.semantic_role}")
        lines.append(f"    reason: {loss.reason}")
        lines.append(f"    safe for: {loss.safe_for}")
        lines.append(f"    unsafe for: {loss.unsafe_for}")
    return "\n".join(lines)


def _render_branch_groups(
    lines: list[str],
    groups: dict[str, list[Branch]],
    graph: GraphIR,
    labels: dict[str, str],
) -> None:
    for group_index, (group_id, branches) in enumerate(groups.items()):
        if group_index:
            lines.append("")
        mode = branches[0].mode
        lines.append(f"  {_humanize(group_id)}")
        lines.append(f"  cardinality: {_mode_description(mode, len(branches))}")

        # An edge is shared only when the IR explicitly assigns its id to every
        # branch in this alternative group. Labels and renderer convenience play
        # no role in this decision.
        shared_edge_ids: set[str] = set()
        if len(branches) > 1:
            shared_edge_ids = set(branches[0].edge_ids)
            for branch in branches[1:]:
                shared_edge_ids.intersection_update(branch.edge_ids)
        ordered_shared_ids = tuple(
            edge_id for edge_id in branches[0].edge_ids if edge_id in shared_edge_ids
        )
        if ordered_shared_ids:
            lines.append("  candidate present in every explicitly listed branch")
            for edge_id in ordered_shared_ids:
                edge = graph.edge(edge_id)
                lines.extend(_render_edge(edge, labels, "    "))
            branch_labels = ", ".join(branch.label for branch in branches)
            lines.append(f"    explicit membership: {branch_labels}")
            shared_edges = tuple(graph.edge(edge_id) for edge_id in ordered_shared_ids)
            lines.append(f"    [{_common_provenance_class(shared_edges)}]")

        for index, branch in enumerate(branches):
            letter = chr(ord("A") + index)
            lines.append(f"  {letter}. {branch.label}")
            branch_only = tuple(
                edge_id for edge_id in branch.edge_ids if edge_id not in shared_edge_ids
            )
            if branch_only:
                for edge_id in branch_only:
                    lines.extend(_render_edge(graph.edge(edge_id), labels, "    "))
            else:
                lines.append("    no branch-local edges")
            lines.append(f"    [{_provenance_class(branch.provenance, branch.status)}]")


def _render_edge(edge: Edge, labels: dict[str, str], indent: str) -> list[str]:
    relation = _humanize(edge.relation)
    qualifiers = dict(edge.qualifiers)
    direction = qualifiers.pop("direction", "")
    optional = qualifiers.pop("necessity", "") == "optional"
    if edge.relation == "affects" and direction in {"increase", "decrease"}:
        relation = "increases" if direction == "increase" else "decreases"
    qualifier_text = ""
    if qualifiers:
        qualifier_text = " (" + ", ".join(f"{key}: {value}" for key, value in qualifiers.items()) + ")"
    if optional:
        qualifier_text += " (optional)"
    return [
        f"{indent}{labels[edge.source]}",
        f"{indent}  {relation} → {labels[edge.target]}{qualifier_text}",
    ]


def _common_provenance_class(edges: tuple[Edge, ...]) -> str:
    classes = {_provenance_class(edge.provenance, edge.status) for edge in edges}
    return next(iter(classes)) if len(classes) == 1 else "mixed candidate provenance"


def _provenance_class(provenance: tuple[Evidence, ...], status: str) -> str:
    kinds = {item.kind for item in provenance}
    if status == "asserted" and "source_text" in kinds:
        label = "source assertion"
    elif "model_hypothesis" in kinds:
        label = "model hypothesis"
    elif "catalog_fragment" in kinds:
        label = "catalog candidate"
    elif "inference_rule" in kinds and status == "inferred":
        label = "parser/resolution inference"
    elif "inference_rule" in kinds:
        label = "rule candidate"
    else:
        label = "unclassified hypothesis"
    if status == "unresolved":
        label += " · unresolved"
    if status == "unsupported":
        label += " · unsupported"
    return label


def _mode_description(mode: str, branch_count: int) -> str:
    if mode == "one_or_more" and branch_count == 1:
        return "candidate bundle; zero or more optional members may apply"
    return {
        "exclusive": "mutually exclusive interpretations",
        "one_or_more": "one or more branches may apply",
    }[mode]


def _unresolved_group_description(group_id: str, branches: list[Branch]) -> str:
    if len(branches) == 1:
        return f"{branches[0].label} remains unconfirmed"
    if branches[0].mode == "exclusive":
        return "No interpretation has been selected."
    noun = group_id.rsplit(".", 1)[-1].replace("_", " ")
    if noun.endswith("ies"):
        noun = noun[:-3] + "y"
    elif noun.endswith("s"):
        noun = noun[:-1]
    return f"No {noun} has been selected."


def _humanize(value: str) -> str:
    return value.replace(".", " ").replace("_", " ")


def _semantic_role(relation: str, status: str) -> str:
    if relation == "lexically_matches":
        return "resolution provenance"
    if status == "asserted":
        return "source assertion"
    if relation in {"uses_evaluator", "evaluates", "yields"}:
        return "evaluator application"
    if relation == "factors_into":
        return "candidate decomposition"
    if relation in {"implemented_by", "affects"}:
        return "candidate implementation"
    return "candidate interpretation"


def _edge_description(graph: GraphIR, edge: Edge) -> str:
    source = graph.node(edge.source).label
    target = graph.node(edge.target).label
    return f"{source} {_humanize(edge.relation)} {target}"


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
