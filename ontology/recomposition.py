from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, NewType

from ontology.schema import Edge, Evidence, GraphIR

OperationId = NewType("OperationId", str)
ItemId = NewType("ItemId", str)


class GuardPredicate(str, Enum):
    UNKNOWN_ITEM_REFERENCE = "unknown_item_reference"
    REQUIRED_EDGE_MISSING = "required_edge_missing"
    REQUIRED_EDGE_UNLICENSED = "required_edge_unlicensed"
    UNRESOLVED_BLOCKER = "unresolved_blocker"
    MERGES_UNRESOLVED_BRANCHES = "merges_unresolved_branches"
    INVENTS_EQUIVALENCE = "invents_equivalence"
    PROMOTES_IMPLEMENTATION = "promotes_implementation_to_definition"
    STRENGTHENS_RELATION = "strengthens_relation"
    DROPS_QUALIFIER = "drops_relation_qualifier"
    ADDS_SENSITIVE_RELATION = "adds_sensitive_relation"
    TURNS_JUDGMENT_INTRINSIC = "turns_evaluator_output_into_intrinsic_property"
    ERASES_PROVENANCE_DISAGREEMENT = "erases_provenance_disagreement"
    DROPS_OPERATION_RELEVANT_DIMENSION = "drops_operation_relevant_dimension"
    COMPLETES_FROM_DEFAULT_PRIOR = "completes_from_default_prior"


class RecompositionOutcome(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    RETAIN_HIGH_DIMENSIONAL = "retain_high_dimensional"


@dataclass(frozen=True)
class EdgeRequirement:
    source: str
    relation: str
    target: str
    qualifiers: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
        }
        if self.qualifiers:
            payload["qualifiers"] = dict(self.qualifiers)
        return payload


@dataclass(frozen=True)
class CandidateRecomposition:
    id: str
    label: str
    operation: OperationId
    required_edges: tuple[EdgeRequirement, ...]
    forbidden_if: tuple[GuardPredicate, ...] = ()
    unresolved_blockers: tuple[ItemId, ...] = ()
    omitted_dimensions: tuple[ItemId, ...] = ()
    safe_for: tuple[OperationId, ...] = ()
    unsafe_for: tuple[OperationId, ...] = ()
    provenance: tuple[Evidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "operation": self.operation,
            "required_edges": [edge.to_dict() for edge in self.required_edges],
            "forbidden_if": [predicate.value for predicate in self.forbidden_if],
            "unresolved_blockers": list(self.unresolved_blockers),
            "omitted_dimensions": list(self.omitted_dimensions),
            "safe_for": list(self.safe_for),
            "unsafe_for": list(self.unsafe_for),
            "provenance": [item.to_dict() for item in self.provenance],
        }


@dataclass(frozen=True)
class FalsificationFinding:
    predicate: GuardPredicate
    item_ids: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicate": self.predicate.value,
            "item_ids": list(self.item_ids),
            "message": self.message,
        }


@dataclass(frozen=True)
class ProjectionDecision:
    candidate_id: str | None
    outcome: RecompositionOutcome
    licensed_edge_ids: tuple[str, ...]
    falsification_findings: tuple[FalsificationFinding, ...]
    retained_edge_ids: tuple[str, ...]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "outcome": self.outcome.value,
            "licensed_edge_ids": list(self.licensed_edge_ids),
            "falsification_findings": [
                finding.to_dict() for finding in self.falsification_findings
            ],
            "retained_edge_ids": list(self.retained_edge_ids),
            "explanation": self.explanation,
        }


class RecompositionGuard:
    """Deterministically falsify task-scoped lexical projections.

    Factorization remains fundamental. This guard never edits the graph, invents
    missing coordinates, or requires that any candidate label be accepted.
    """

    _SENSITIVE_RELATIONS = {
        "causes",
        "coupling",
        "demands",
        "has_jurisdiction_over",
        "identity_coupling",
        "obligation",
        "recurrence",
        "requires",
        "temporal_after",
        "temporal_before",
        "urgency",
    }

    def evaluate_candidate(
        self,
        graph: GraphIR,
        candidate: CandidateRecomposition,
        operation: OperationId,
    ) -> ProjectionDecision:
        if candidate.operation != operation:
            raise ValueError(
                f"Candidate operation {candidate.operation!r} does not match {operation!r}"
            )
        findings: list[FalsificationFinding] = []
        licensed_edge_ids: list[str] = []
        matched_edges: list[Edge] = []

        for requirement in candidate.required_edges:
            exact = tuple(
                edge for edge in graph.edges if _edge_matches(edge, requirement)
            )
            if exact:
                matched_edges.extend(exact)
                licensed = tuple(edge for edge in exact if _edge_is_licensed(graph, edge))
                if licensed:
                    licensed_edge_ids.append(licensed[0].id)
                else:
                    findings.append(
                        FalsificationFinding(
                            GuardPredicate.REQUIRED_EDGE_UNLICENSED,
                            tuple(edge.id for edge in exact),
                            "A required edge exists only as an unresolved or unsupported candidate.",
                        )
                    )
                continue

            findings.append(
                FalsificationFinding(
                    GuardPredicate.REQUIRED_EDGE_MISSING,
                    (),
                    (
                        f"Required edge {requirement.source} {requirement.relation} "
                        f"{requirement.target} is absent."
                    ),
                )
            )
            findings.append(
                FalsificationFinding(
                    GuardPredicate.COMPLETES_FROM_DEFAULT_PRIOR,
                    (),
                    "The guard will not reconstruct the missing edge from lexical defaults.",
                )
            )
            findings.extend(self._strengthening_findings(graph, requirement))

        findings.extend(self._branch_findings(graph, matched_edges))
        findings.extend(self._provenance_findings(matched_edges))

        for blocker in candidate.unresolved_blockers:
            if not _item_exists(graph, blocker):
                findings.append(
                    FalsificationFinding(
                        GuardPredicate.UNKNOWN_ITEM_REFERENCE,
                        (blocker,),
                        "An unresolved blocker id does not exist in the current graph.",
                    )
                )
            elif _item_is_unresolved(graph, blocker):
                findings.append(
                    FalsificationFinding(
                        GuardPredicate.UNRESOLVED_BLOCKER,
                        (blocker,),
                        "The candidate names an unresolved blocker that has not been selected.",
                    )
                )

        unknown_dimensions = tuple(
            item_id
            for item_id in candidate.omitted_dimensions
            if not _item_exists(graph, item_id)
        )
        if unknown_dimensions:
            findings.append(
                FalsificationFinding(
                    GuardPredicate.UNKNOWN_ITEM_REFERENCE,
                    unknown_dimensions,
                    "An omitted dimension id does not exist in the current graph.",
                )
            )
        if candidate.omitted_dimensions and not unknown_dimensions and (
            operation in candidate.unsafe_for or operation not in candidate.safe_for
        ):
            findings.append(
                FalsificationFinding(
                    GuardPredicate.DROPS_OPERATION_RELEVANT_DIMENSION,
                    candidate.omitted_dimensions,
                    "The candidate omits dimensions not declared safe to omit for this operation.",
                )
            )

        findings = list(_unique_findings(findings))
        outcome = RecompositionOutcome.REJECT if findings else RecompositionOutcome.ACCEPT
        explanation = (
            "Candidate rejected by deterministic falsification."
            if findings
            else "All required edges are licensed for the requested operation."
        )
        return ProjectionDecision(
            candidate_id=candidate.id,
            outcome=outcome,
            licensed_edge_ids=tuple(dict.fromkeys(licensed_edge_ids)),
            falsification_findings=tuple(findings),
            retained_edge_ids=tuple(edge.id for edge in graph.edges),
            explanation=explanation,
        )

    def decide(
        self,
        graph: GraphIR,
        candidates: tuple[CandidateRecomposition, ...],
        operation: OperationId,
    ) -> ProjectionDecision:
        rejected: list[ProjectionDecision] = []
        for candidate in candidates:
            decision = self.evaluate_candidate(graph, candidate, operation)
            if decision.outcome == RecompositionOutcome.ACCEPT:
                return decision
            rejected.append(decision)

        findings = _unique_findings(
            finding
            for decision in rejected
            for finding in decision.falsification_findings
        )
        return ProjectionDecision(
            candidate_id=None,
            outcome=RecompositionOutcome.RETAIN_HIGH_DIMENSIONAL,
            licensed_edge_ids=(),
            falsification_findings=tuple(findings),
            retained_edge_ids=tuple(edge.id for edge in graph.edges),
            explanation=(
                "No semantically safe useful compression was licensed; retain the graph."
            ),
        )

    def _strengthening_findings(
        self,
        graph: GraphIR,
        requirement: EdgeRequirement,
    ) -> tuple[FalsificationFinding, ...]:
        same_endpoints = tuple(
            edge
            for edge in graph.edges
            if edge.source == requirement.source and edge.target == requirement.target
        )
        findings: list[FalsificationFinding] = []
        relations = {edge.relation for edge in same_endpoints}
        item_ids = tuple(edge.id for edge in same_endpoints)
        if requirement.relation == "treated_as_equivalent_to":
            findings.append(
                FalsificationFinding(
                    GuardPredicate.INVENTS_EQUIVALENCE,
                    item_ids,
                    "No licensed equivalence edge supports this candidate.",
                )
            )
            if "implemented_by" in relations:
                findings.append(
                    FalsificationFinding(
                        GuardPredicate.PROMOTES_IMPLEMENTATION,
                        item_ids,
                        "An implementation edge cannot be promoted to a definition.",
                    )
                )
        if requirement.relation == "causes" and relations.intersection(
            {"affects", "correlates_with"}
        ):
            findings.append(
                FalsificationFinding(
                    GuardPredicate.STRENGTHENS_RELATION,
                    item_ids,
                    "An affects edge does not license causal direction.",
                )
            )
        same_relation = tuple(
            edge for edge in same_endpoints if edge.relation == requirement.relation
        )
        if same_relation and all(
            dict(edge.qualifiers) != dict(requirement.qualifiers) for edge in same_relation
        ):
            findings.append(
                FalsificationFinding(
                    GuardPredicate.DROPS_QUALIFIER,
                    tuple(edge.id for edge in same_relation),
                    "The candidate does not preserve the licensed edge qualifiers exactly.",
                )
            )
        if requirement.relation in self._SENSITIVE_RELATIONS:
            findings.append(
                FalsificationFinding(
                    GuardPredicate.ADDS_SENSITIVE_RELATION,
                    item_ids,
                    "The candidate would add a sensitive relation without an exact licensed edge.",
                )
            )
        if requirement.relation == "has_property" and _would_intrinsify_judgment(
            graph, requirement
        ):
            findings.append(
                FalsificationFinding(
                    GuardPredicate.TURNS_JUDGMENT_INTRINSIC,
                    item_ids,
                    "Evaluator output cannot be converted into an intrinsic object property.",
                )
            )
        return tuple(findings)

    def _branch_findings(
        self,
        graph: GraphIR,
        matched_edges: list[Edge],
    ) -> tuple[FalsificationFinding, ...]:
        matched_ids = {edge.id for edge in matched_edges}
        groups: dict[str, list] = {}
        for branch in graph.branches:
            if branch.status == "unresolved":
                groups.setdefault(branch.group_id, []).append(branch)
        findings: list[FalsificationFinding] = []
        for branches in groups.values():
            shared_ids = set(branches[0].edge_ids)
            for branch in branches[1:]:
                shared_ids.intersection_update(branch.edge_ids)
            used_branches = tuple(
                branch.id
                for branch in branches
                if matched_ids.intersection(set(branch.edge_ids) - shared_ids)
            )
            if len(used_branches) > 1:
                findings.append(
                    FalsificationFinding(
                        GuardPredicate.MERGES_UNRESOLVED_BRANCHES,
                        used_branches,
                        "The candidate draws from multiple distinct unresolved branches.",
                    )
                )
        return tuple(findings)

    def _provenance_findings(
        self,
        matched_edges: list[Edge],
    ) -> tuple[FalsificationFinding, ...]:
        provenance_classes = {
            tuple(sorted(item.kind for item in edge.provenance)) for edge in matched_edges
        }
        if len(provenance_classes) <= 1:
            return ()
        return (
            FalsificationFinding(
                GuardPredicate.ERASES_PROVENANCE_DISAGREEMENT,
                tuple(edge.id for edge in matched_edges),
                "The candidate would flatten materially different provenance classes.",
            ),
        )


def _edge_matches(edge: Edge, requirement: EdgeRequirement) -> bool:
    if (
        edge.source != requirement.source
        or edge.relation != requirement.relation
        or edge.target != requirement.target
    ):
        return False
    return dict(edge.qualifiers) == dict(requirement.qualifiers)


def _edge_is_licensed(graph: GraphIR, edge: Edge) -> bool:
    if edge.status == "asserted":
        return True
    if edge.status == "unsupported":
        return False
    return any(
        branch.status == "selected" and edge.id in branch.edge_ids
        for branch in graph.branches
    )


def _item_is_unresolved(graph: GraphIR, item_id: str) -> bool:
    return any(branch.id == item_id and branch.status == "unresolved" for branch in graph.branches) or any(
        edge.id == item_id and edge.status == "unresolved" for edge in graph.edges
    )


def _item_exists(graph: GraphIR, item_id: str) -> bool:
    return (
        any(node.id == item_id for node in graph.nodes)
        or any(edge.id == item_id for edge in graph.edges)
        or any(branch.id == item_id for branch in graph.branches)
    )


def _would_intrinsify_judgment(graph: GraphIR, requirement: EdgeRequirement) -> bool:
    evaluations = {
        edge.source
        for edge in graph.edges
        if edge.relation == "evaluates" and edge.target == requirement.source
    }
    return any(
        edge.source in evaluations
        and edge.relation == "yields"
        and edge.target == requirement.target
        for edge in graph.edges
    )


def _unique_findings(findings) -> tuple[FalsificationFinding, ...]:
    by_key = {}
    for finding in findings:
        key = (finding.predicate, finding.item_ids)
        by_key.setdefault(key, finding)
    return tuple(by_key.values())
