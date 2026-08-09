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
    group_id: str
    label: str
    edge_ids: tuple[str, ...]
    mode: str = "one_or_more"
    depth: int = 0


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
            EdgeTemplate(
                "belonging.recurrence",
                "$trigger",
                "factors_into",
                "recurrence",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "belonging.identity",
                "$trigger",
                "factors_into",
                "identity_coupling",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "belonging.obligation",
                "$trigger",
                "factors_into",
                "obligation",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "belonging.exit_cost",
                "$trigger",
                "factors_into",
                "exit_cost",
                (("necessity", "optional"),),
            ),
            EdgeTemplate("belonging.place", "$trigger", "factors_into", "place_attachment"),
        ),
        branches=(
            BranchTemplate(
                "belonging.social",
                "belonging.configurations",
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
                "belonging.configurations",
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
                "harmony.implementations",
                "conflict resolution",
                ("harmony.resolution", "resolution.signal"),
            ),
            BranchTemplate(
                "harmony.suppression_branch",
                "harmony.implementations",
                "conflict suppression",
                ("harmony.suppression", "suppression.signal", "suppression.dissent"),
            ),
        ),
    ),
    Fragment(
        id="good_engineer.sensitivities.v1",
        trigger="good engineers",
        node_labels=(
            ("judgment", "judgment"),
            ("debugging", "debugging"),
            ("system_modeling", "system modeling"),
            ("ai_navigation", "AI navigation"),
            ("curiosity", "curiosity"),
        ),
        edges=(
            EdgeTemplate(
                "good.sensitivity.judgment",
                "good_evaluator",
                "sensitive_to",
                "judgment",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "good.sensitivity.debugging",
                "good_evaluator",
                "sensitive_to",
                "debugging",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "good.sensitivity.system",
                "good_evaluator",
                "sensitive_to",
                "system_modeling",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "good.sensitivity.ai",
                "good_evaluator",
                "sensitive_to",
                "ai_navigation",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "good.sensitivity.curiosity",
                "good_evaluator",
                "sensitive_to",
                "curiosity",
                (("necessity", "optional"),),
            ),
        ),
        branches=(
            BranchTemplate(
                "good.broader_model",
                "good.recursive_candidate_expansion",
                "broader evaluator sensitivities",
                (
                    "good.sensitivity.judgment",
                    "good.sensitivity.debugging",
                    "good.sensitivity.system",
                    "good.sensitivity.ai",
                    "good.sensitivity.curiosity",
                ),
                depth=1,
            ),
        ),
    ),
    Fragment(
        id="respect.implementations.v1",
        trigger="respect",
        node_labels=(
            ("accurate_recognition", "accurate recognition"),
            ("boundary_observance", "boundary observance"),
            ("politeness", "politeness"),
            ("deference", "deference"),
        ),
        edges=(
            EdgeTemplate("respect.recognition", "$trigger", "implemented_by", "accurate_recognition"),
            EdgeTemplate("respect.boundaries", "$trigger", "implemented_by", "boundary_observance"),
            EdgeTemplate("respect.politeness", "$trigger", "implemented_by", "politeness"),
            EdgeTemplate("respect.deference", "$trigger", "implemented_by", "deference"),
        ),
        branches=(
            BranchTemplate(
                "respect.recognition_branch",
                "respect.implementations",
                "accurate recognition",
                ("respect.recognition",),
            ),
            BranchTemplate(
                "respect.boundaries_branch",
                "respect.implementations",
                "boundary observance",
                ("respect.boundaries",),
            ),
            BranchTemplate(
                "respect.politeness_branch",
                "respect.implementations",
                "politeness",
                ("respect.politeness",),
            ),
            BranchTemplate(
                "respect.deference_branch",
                "respect.implementations",
                "deference",
                ("respect.deference",),
            ),
        ),
    ),
    Fragment(
        id="healthy_relationship.evaluator_candidates.v1",
        trigger="healthy-relationship evaluator",
        node_labels=(
            ("signal_preservation", "signal preservation"),
            ("reversibility", "reversibility"),
        ),
        edges=(
            EdgeTemplate(
                "healthy_relationship.sensitivity.signal",
                "$trigger",
                "sensitive_to",
                "signal_preservation",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "healthy_relationship.sensitivity.reversibility",
                "$trigger",
                "sensitive_to",
                "reversibility",
                (("necessity", "optional"),),
            ),
        ),
        branches=(
            BranchTemplate(
                "healthy_relationship.evaluator_expansion",
                "healthy_relationship.evaluator_recursive_expansion",
                "relationship-health evaluator candidates",
                (
                    "healthy_relationship.sensitivity.signal",
                    "healthy_relationship.sensitivity.reversibility",
                ),
                depth=1,
            ),
        ),
    ),
    Fragment(
        id="relationship.configuration_candidates.v1",
        trigger="relationship configuration",
        node_labels=(
            ("participant_configuration", "participant configuration"),
            ("scope", "scope"),
        ),
        edges=(
            EdgeTemplate(
                "relationship.configuration.participants",
                "$trigger",
                "factors_into",
                "participant_configuration",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "relationship.configuration.scope",
                "$trigger",
                "factors_into",
                "scope",
                (("necessity", "optional"),),
            ),
        ),
        branches=(
            BranchTemplate(
                "relationship.configuration_expansion",
                "relationship.configuration_recursive_expansion",
                "relationship configuration candidates",
                (
                    "relationship.configuration.participants",
                    "relationship.configuration.scope",
                ),
                depth=1,
            ),
        ),
    ),
    Fragment(
        id="good_parent.evaluator_candidates.v1",
        trigger="good-parent evaluator",
        node_labels=(
            ("consistency", "consistency"),
            ("proportionality", "proportionality"),
        ),
        edges=(
            EdgeTemplate(
                "good_parent.sensitivity.consistency",
                "$trigger",
                "sensitive_to",
                "consistency",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "good_parent.sensitivity.proportionality",
                "$trigger",
                "sensitive_to",
                "proportionality",
                (("necessity", "optional"),),
            ),
        ),
        branches=(
            BranchTemplate(
                "good_parent.evaluator_expansion",
                "good_parent.evaluator_recursive_expansion",
                "good-parent evaluator candidates",
                (
                    "good_parent.sensitivity.consistency",
                    "good_parent.sensitivity.proportionality",
                ),
                depth=1,
            ),
        ),
    ),
    Fragment(
        id="parent.configuration_candidates.v1",
        trigger="parent configuration",
        node_labels=(
            ("role_context", "role context"),
            ("household_context", "household context"),
        ),
        edges=(
            EdgeTemplate(
                "parent.configuration.role_context",
                "$trigger",
                "factors_into",
                "role_context",
                (("necessity", "optional"),),
            ),
            EdgeTemplate(
                "parent.configuration.household_context",
                "$trigger",
                "factors_into",
                "household_context",
                (("necessity", "optional"),),
            ),
        ),
        branches=(
            BranchTemplate(
                "parent.configuration_expansion",
                "parent.configuration_recursive_expansion",
                "parent configuration candidates",
                (
                    "parent.configuration.role_context",
                    "parent.configuration.household_context",
                ),
                depth=1,
            ),
        ),
    ),
)


def matching_fragments(labels: set[str]) -> tuple[Fragment, ...]:
    return tuple(fragment for fragment in VERTICAL_SLICE_FRAGMENTS if fragment.trigger in labels)
