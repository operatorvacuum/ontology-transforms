from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology import SemanticCompiler, render_projection
from ontology.recomposition import (
    CandidateRecomposition,
    EdgeRequirement,
    OperationId,
    RecompositionGuard,
    RecompositionOutcome,
)


def edge_keys(compilation):
    return {
        (edge.source, edge.relation, edge.target): edge
        for edge in compilation.graph.edges
    }


def test_healthy_relationships_preserve_necessity_without_causal_strengthening():
    compilation = SemanticCompiler().compile("Healthy relationships require honesty.")
    edges = edge_keys(compilation)

    source = edges[("healthy_relationships", "requires", "honesty")]
    assert source.status == "asserted"
    assert sum(edge.id == source.id for edge in compilation.graph.edges) == 1
    assert ("healthy_relationship_evaluator", "sensitive_to", "honesty") in edges
    assert ("relationship_configuration", "requires", "honesty") in edges

    direct = [
        branch
        for branch in compilation.graph.branches
        if branch.group_id == "requirement.direct_readings"
    ]
    assert len(direct) == 2
    assert all(branch.mode == "one_or_more" for branch in direct)
    assert all(compilation.graph.edge(edge_id).status == "unresolved" for branch in direct for edge_id in branch.edge_ids)

    assert not any(edge.relation == "causes" for edge in compilation.graph.edges)
    assert (
        "healthy_relationships",
        "treated_as_equivalent_to",
        "honesty_required_configuration",
    ) not in edges
    assert not any(
        edge.source == "honesty" and edge.relation == "causes"
        for edge in compilation.graph.edges
    )

    depth_zero = compilation.projection("factor")
    assert not any(branch.depth == 1 for branch in depth_zero.graph.branches)
    recursive_losses = [
        loss for loss in depth_zero.losses
        if loss.semantic_role == "recursive candidate expansion"
    ]
    assert len(recursive_losses) == 1
    assert "healthy_relationship.evaluator_expansion" in recursive_losses[0].item_ids
    assert "relationship.configuration_expansion" in recursive_losses[0].item_ids

    expanded = SemanticCompiler().compile(
        "Healthy relationships require honesty.", projection_depth=1
    )
    recursive_groups = {
        branch.group_id for branch in expanded.projection("factor").graph.branches
        if branch.depth == 1
    }
    assert recursive_groups == {
        "healthy_relationship.evaluator_recursive_expansion",
        "relationship.configuration_recursive_expansion",
    }

    candidate = CandidateRecomposition(
        "unresolved.requirement",
        "honesty-required relationship configuration",
        OperationId("describe_relationship_configuration"),
        (EdgeRequirement("relationship_configuration", "requires", "honesty"),),
    )
    decision = RecompositionGuard().evaluate_candidate(
        compilation.graph,
        candidate,
        OperationId("describe_relationship_configuration"),
    )
    assert decision.outcome == RecompositionOutcome.REJECT


def test_mentor_keeps_normative_evaluation_separate_from_obligation_and_jurisdiction():
    compilation = SemanticCompiler().compile("A mentor should guide you.")
    edges = edge_keys(compilation)

    expected = {
        ("guide_action", "has_agent", "mentor_role"),
        ("guide_action", "has_target", "addressee"),
        ("should_evaluation", "uses_evaluator", "should_evaluator"),
        ("should_evaluation", "evaluates", "guide_action"),
        ("should_evaluation", "yields", "positive_normative_evaluation"),
    }
    assert expected <= set(edges)
    assert all(edges[key].status == "asserted" for key in expected)
    forbidden = {
        "authority",
        "has_jurisdiction_over",
        "obligated_to",
        "obligation",
        "recurrence",
        "access",
        "identity_coupling",
        "obedience",
    }
    assert not any(edge.relation in forbidden for edge in compilation.graph.edges)
    assert any(
        diagnostic.code == "unresolved_normative_bearer"
        for diagnostic in compilation.graph.diagnostics
    )
    rendered = render_projection(compilation.projection("factor"), compilation.sentence)
    assert "does not assign an obligation bearer" in rendered
    assert "normative demand" not in rendered


def test_respect_keeps_minimal_implementations_unselected_and_distinct():
    compilation = SemanticCompiler().compile("Respect is important.")
    edges = edge_keys(compilation)

    assert edges[("importance_evaluation", "evaluates", "respect")].status == "asserted"
    implementations = {
        edge.target
        for edge in compilation.graph.edges
        if edge.source == "respect" and edge.relation == "implemented_by"
    }
    assert implementations == {
        "accurate_recognition",
        "boundary_observance",
        "politeness",
        "deference",
    }
    assert all(
        edge.status == "unresolved"
        for edge in compilation.graph.edges
        if edge.source == "respect" and edge.relation == "implemented_by"
    )
    assert not any(edge.relation == "treated_as_equivalent_to" for edge in compilation.graph.edges)
    assert not any(node.label == "obedience" for node in compilation.graph.nodes)
    implementation_losses = compilation.projection("implementation").losses
    assert any(
        loss.semantic_role == "resolution provenance"
        and "respect.implementations.v1" in loss.description
        for loss in implementation_losses
    )

    candidate = CandidateRecomposition(
        "respect.as.deference",
        "respect as deference",
        OperationId("select_respect_implementation"),
        (EdgeRequirement("respect", "implemented_by", "deference"),),
    )
    decision = RecompositionGuard().evaluate_candidate(
        compilation.graph,
        candidate,
        OperationId("select_respect_implementation"),
    )
    assert decision.outcome == RecompositionOutcome.REJECT


def test_good_parents_split_lexical_handle_modifier_and_head_noun():
    compilation = SemanticCompiler().compile("Good parents set boundaries.")
    edges = edge_keys(compilation)

    asserted = [edge for edge in compilation.graph.edges if edge.status == "asserted"]
    assert {(edge.source, edge.relation, edge.target) for edge in asserted} == {
        ("good_parents", "set", "boundaries"),
    }
    assert ("good_parent_evaluation", "evaluates", "parent_configuration") in edges
    assert (
        "good_parent_evaluator",
        "sensitive_to",
        "boundaries_setting_action",
    ) in edges
    assert (
        "parents_judged_good",
        "tend_to_have",
        "boundaries_setting_action",
    ) in edges
    assert len({"good_parents", "good_parent_evaluator", "parent_configuration"}) == 3

    primary = [
        branch for branch in compilation.graph.branches
        if branch.group_id == "good_parent.primary_readings"
    ]
    assert len(primary) == 2
    assert all(branch.mode == "exclusive" for branch in primary)
    recursive_groups = {
        branch.group_id for branch in compilation.graph.branches if branch.depth == 1
    }
    assert recursive_groups == {
        "good_parent.evaluator_recursive_expansion",
        "parent.configuration_recursive_expansion",
    }

    forbidden = {
        "authority",
        "has_jurisdiction_over",
        "obligated_to",
        "recurrence",
        "access",
        "identity_coupling",
        "causes",
    }
    assert not any(edge.relation in forbidden for edge in compilation.graph.edges)
    assert not any(
        edge.source == "good_parents" and edge.relation in {"evaluates", "factors_into"}
        for edge in compilation.graph.edges
    )

    depth_zero = compilation.projection("factor")
    assert not any(branch.depth == 1 for branch in depth_zero.graph.branches)
    recursive_losses = [
        loss for loss in depth_zero.losses
        if loss.semantic_role == "recursive candidate expansion"
    ]
    assert len(recursive_losses) == 1
    assert "good_parent.evaluator_expansion" in recursive_losses[0].item_ids
    assert "parent.configuration_expansion" in recursive_losses[0].item_ids
    expanded = SemanticCompiler().compile(
        "Good parents set boundaries.", projection_depth=1
    ).projection("factor")
    assert {
        branch.group_id for branch in expanded.graph.branches if branch.depth == 1
    } == recursive_groups


def test_adversarial_outputs_are_deterministic():
    fixtures = (
        ("Healthy relationships require honesty.", "factor"),
        ("A mentor should guide you.", "factor"),
        ("Respect is important.", "implementation"),
        ("Good parents set boundaries.", "factor"),
    )
    for sentence, view in fixtures:
        first = SemanticCompiler().compile(sentence)
        second = SemanticCompiler().compile(sentence)
        assert first.to_dict() == second.to_dict()
        assert render_projection(first.projection(view), sentence) == render_projection(
            second.projection(view), sentence
        )


if __name__ == "__main__":
    test_healthy_relationships_preserve_necessity_without_causal_strengthening()
    test_mentor_keeps_normative_evaluation_separate_from_obligation_and_jurisdiction()
    test_respect_keeps_minimal_implementations_unselected_and_distinct()
    test_good_parents_split_lexical_handle_modifier_and_head_noun()
    test_adversarial_outputs_are_deterministic()
