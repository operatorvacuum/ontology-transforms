from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeTemplate:
    id: str
    source: str
    relation: str
    target: str
    qualifiers: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class BranchTemplate:
    id: str
    label: str
    edge_ids: tuple[str, ...]
    mode: str = "one_or_more"


@dataclass(frozen=True)
class Fragment:
    """A contextual candidate graph, never a canonical word definition."""

    id: str
    trigger: str
    node_labels: tuple[tuple[str, str], ...]
    edges: tuple[EdgeTemplate, ...]
    branches: tuple[BranchTemplate, ...]


VERTICAL_SLICE_FRAGMENTS = (
    Fragment(
        id="belonging.candidates.v1",
        trigger="belonging",
        node_labels=(
            ("recognition", "recognition"),
            ("access", "access"),
            ("recurrence", "recurrence"),
            ("identity_coupling", "identity coupling"),
            ("obligation", "obligation"),
            ("exit_cost", "exit cost"),
            ("place_attachment", "place attachment"),
        ),
        edges=(
            EdgeTemplate("belonging.recognition", "$trigger", "factors_into", "recognition"),
            EdgeTemplate("belonging.access", "$trigger", "factors_into", "access"),
            EdgeTemplate("belonging.recurrence", "$trigger", "factors_into", "recurrence"),
            EdgeTemplate("belonging.identity", "$trigger", "factors_into", "identity_coupling"),
            EdgeTemplate("belonging.obligation", "$trigger", "factors_into", "obligation"),
            EdgeTemplate("belonging.exit_cost", "$trigger", "factors_into", "exit_cost"),
            EdgeTemplate("belonging.place", "$trigger", "factors_into", "place_attachment"),
        ),
        branches=(
            BranchTemplate(
                "belonging.social",
                "social-recognition configuration",
                (
                    "belonging.recognition",
                    "belonging.access",
                    "belonging.recurrence",
                    "belonging.identity",
                    "belonging.obligation",
                    "belonging.exit_cost",
                ),
            ),
            BranchTemplate(
                "belonging.place",
                "place-attachment configuration",
                ("belonging.recognition", "belonging.place"),
            ),
        ),
    ),
    Fragment(
        id="harmony.implementations.v1",
        trigger="harmony",
        node_labels=(
            ("conflict_resolution", "conflict resolution"),
            ("conflict_suppression", "conflict suppression"),
            ("signal_preservation", "signal preservation"),
            ("private_dissent_visibility", "private dissent visibility"),
        ),
        edges=(
            EdgeTemplate("harmony.resolution", "$trigger", "implemented_by", "conflict_resolution"),
            EdgeTemplate("harmony.suppression", "$trigger", "implemented_by", "conflict_suppression"),
            EdgeTemplate(
                "resolution.signal",
                "conflict_resolution",
                "affects",
                "signal_preservation",
                (("direction", "increase"),),
            ),
            EdgeTemplate(
                "suppression.signal",
                "conflict_suppression",
                "affects",
                "signal_preservation",
                (("direction", "decrease"),),
            ),
            EdgeTemplate(
                "suppression.dissent",
                "conflict_suppression",
                "affects",
                "private_dissent_visibility",
                (("direction", "decrease"),),
            ),
        ),
        branches=(
            BranchTemplate(
                "harmony.resolution_branch",
                "conflict resolution",
                ("harmony.resolution", "resolution.signal"),
            ),
            BranchTemplate(
                "harmony.suppression_branch",
                "conflict suppression",
                ("harmony.suppression", "suppression.signal", "suppression.dissent"),
            ),
        ),
    ),
    Fragment(
        id="good_engineer.sensitivities.v1",
        trigger="good engineer",
        node_labels=(
            ("judgment", "judgment"),
            ("debugging", "debugging"),
            ("system_modeling", "system modeling"),
            ("ai_navigation", "AI navigation"),
            ("curiosity", "curiosity"),
        ),
        edges=(
            EdgeTemplate("good.sensitivity.judgment", "good_evaluator", "sensitive_to", "judgment"),
            EdgeTemplate("good.sensitivity.debugging", "good_evaluator", "sensitive_to", "debugging"),
            EdgeTemplate("good.sensitivity.system", "good_evaluator", "sensitive_to", "system_modeling"),
            EdgeTemplate("good.sensitivity.ai", "good_evaluator", "sensitive_to", "ai_navigation"),
            EdgeTemplate("good.sensitivity.curiosity", "good_evaluator", "sensitive_to", "curiosity"),
        ),
        branches=(
            BranchTemplate(
                "good.broader_model",
                "broader evaluator sensitivities",
                (
                    "good.sensitivity.judgment",
                    "good.sensitivity.debugging",
                    "good.sensitivity.system",
                    "good.sensitivity.ai",
                    "good.sensitivity.curiosity",
                ),
            ),
        ),
    ),
)


def matching_fragments(labels: set[str]) -> tuple[Fragment, ...]:
    return tuple(fragment for fragment in VERTICAL_SLICE_FRAGMENTS if fragment.trigger in labels)
