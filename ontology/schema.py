from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

EvidenceKind = Literal[
    "source_text",
    "catalog_fragment",
    "inference_rule",
    "model_hypothesis",
]
EdgeStatus = Literal["asserted", "inferred", "unresolved", "unsupported"]
BranchStatus = Literal["unresolved", "selected", "rejected"]


@dataclass(frozen=True)
class Evidence:
    kind: EvidenceKind
    ref: str
    span: tuple[int, int] | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": self.kind, "ref": self.ref}
        if self.span is not None:
            payload["span"] = list(self.span)
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass(frozen=True)
class Node:
    """A locally identified symbol.

    Nodes intentionally have no global semantic class. Their roles are expressed
    by incident edges in the current graph.
    """

    id: str
    label: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "label": self.label}


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    relation: str
    target: str
    status: EdgeStatus
    provenance: tuple[Evidence, ...]
    qualifiers: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
            "status": self.status,
            "provenance": [item.to_dict() for item in self.provenance],
        }
        if self.qualifiers:
            payload["qualifiers"] = dict(self.qualifiers)
        return payload


@dataclass(frozen=True)
class Branch:
    id: str
    label: str
    edge_ids: tuple[str, ...]
    mode: Literal["exclusive", "one_or_more"]
    status: BranchStatus
    provenance: tuple[Evidence, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "edge_ids": list(self.edge_ids),
            "mode": self.mode,
            "status": self.status,
            "provenance": [item.to_dict() for item in self.provenance],
        }


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    item_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "item_ids": list(self.item_ids),
        }


@dataclass(frozen=True)
class GraphIR:
    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()
    branches: tuple[Branch, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def node(self, node_id: str) -> Node:
        return next(node for node in self.nodes if node.id == node_id)

    def edge(self, edge_id: str) -> Edge:
        return next(edge for edge in self.edges if edge.id == edge_id)

    def with_items(
        self,
        *,
        nodes: tuple[Node, ...] = (),
        edges: tuple[Edge, ...] = (),
        branches: tuple[Branch, ...] = (),
        diagnostics: tuple[Diagnostic, ...] = (),
    ) -> "GraphIR":
        return GraphIR(
            nodes=_unique_by_id((*self.nodes, *nodes)),
            edges=_unique_by_id((*self.edges, *edges)),
            branches=_unique_by_id((*self.branches, *branches)),
            diagnostics=(*self.diagnostics, *diagnostics),
        )

    def replace_edges(self, edges: tuple[Edge, ...]) -> "GraphIR":
        return replace(self, edges=edges)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "branches": [branch.to_dict() for branch in self.branches],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


@dataclass(frozen=True)
class CompilerState:
    pass_name: str
    graph: GraphIR
    invariant: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass": self.pass_name,
            "invariant": self.invariant,
            "graph": self.graph.to_dict(),
        }


@dataclass(frozen=True)
class ProjectionLoss:
    action: Literal["omitted", "merged"]
    item_ids: tuple[str, ...]
    reason: str
    safe_because: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "item_ids": list(self.item_ids),
            "reason": self.reason,
            "safe_because": self.safe_because,
        }


@dataclass(frozen=True)
class Projection:
    name: str
    graph: GraphIR
    losses: tuple[ProjectionLoss, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "graph": self.graph.to_dict(),
            "losses": [loss.to_dict() for loss in self.losses],
        }


@dataclass(frozen=True)
class Compilation:
    sentence: str
    context: dict[str, str]
    states: tuple[CompilerState, ...]
    projections: tuple[Projection, ...] = field(default_factory=tuple)

    @property
    def graph(self) -> GraphIR:
        return self.states[-1].graph

    def state(self, pass_name: str) -> CompilerState:
        return next(state for state in self.states if state.pass_name == pass_name)

    def projection(self, name: str) -> Projection:
        return next(item for item in self.projections if item.name == name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": {"text": self.sentence, "context": self.context},
            "states": [state.to_dict() for state in self.states],
            "projections": [item.to_dict() for item in self.projections],
        }


def _unique_by_id(items):
    by_id = {}
    for item in items:
        by_id.setdefault(item.id, item)
    return tuple(by_id.values())
