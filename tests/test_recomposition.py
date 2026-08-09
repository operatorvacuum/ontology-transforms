from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology import (
    CandidateRecomposition,
    EdgeRequirement,
    Evidence,
    GuardPredicate,
    RecompositionGuard,
    RecompositionOperation,
    RecompositionOutcome,
    SemanticCompiler,
    render_recomposition_decision,
)
from ontology.recomposition_cases import proposal_for, proposals_for


def graph_for(sentence: str):
    return SemanticCompiler().compile(sentence).graph


def finding_codes(decision):
    return {finding.predicate for finding in decision.falsification_findings}


def fixture_candidate(sentence, operation, label):
    candidate = proposal_for(sentence, operation, label)
    assert candidate is not None
    return candidate


def test_accepts_fully_licensed_task_scoped_judgment_projection():
    graph = graph_for("Harmony is important.")
    operation = "report_asserted_judgment"
    candidate = CandidateRecomposition(
        id="important.asserted_judgment",
        label="important",
        operation=operation,
        required_edges=(
            EdgeRequirement("importance_evaluation", "uses_evaluator", "important_evaluator"),
            EdgeRequirement("importance_evaluation", "evaluates", "harmony"),
            EdgeRequirement("importance_evaluation", "yields", "positive_importance"),
        ),
        forbidden_if=(GuardPredicate.TURNS_JUDGMENT_INTRINSIC,),
        omitted_dimensions=("harmony.resolution_branch", "harmony.suppression_branch"),
        safe_for=(operation,),
        unsafe_for=("select_harmony_implementation",),
        provenance=(Evidence("inference_rule", "task_scoped_judgment_projection"),),
    )

    decision = RecompositionGuard().evaluate_candidate(graph, candidate, operation)

    assert decision.outcome == RecompositionOutcome.ACCEPT
    assert decision.candidate_id == candidate.id
    assert set(decision.licensed_edge_ids) == {
        "importance.uses",
        "importance.target",
        "importance.result",
    }
    assert not decision.falsification_findings


def test_rejects_implementation_promoted_to_handle_definition():
    graph = graph_for("Harmony is important.")
    operation = "summarize_harmony"
    candidate = CandidateRecomposition(
        id="harmony.as_suppression",
        label="harmony",
        operation=operation,
        required_edges=(
            EdgeRequirement("harmony", "implemented_by", "conflict_suppression"),
            EdgeRequirement(
                "harmony", "treated_as_equivalent_to", "conflict_suppression"
            ),
        ),
        forbidden_if=(
            GuardPredicate.INVENTS_EQUIVALENCE,
            GuardPredicate.PROMOTES_IMPLEMENTATION,
        ),
        unresolved_blockers=("harmony.suppression_branch",),
        omitted_dimensions=("harmony.resolution_branch",),
        safe_for=(),
        unsafe_for=(operation,),
    )

    decision = RecompositionGuard().evaluate_candidate(graph, candidate, operation)
    codes = finding_codes(decision)

    assert decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.REQUIRED_EDGE_UNLICENSED in codes
    assert GuardPredicate.INVENTS_EQUIVALENCE in codes
    assert GuardPredicate.PROMOTES_IMPLEMENTATION in codes
    assert GuardPredicate.UNRESOLVED_BLOCKER in codes
    assert GuardPredicate.DROPS_OPERATION_RELEVANT_DIMENSION in codes


def test_retains_high_dimensional_belonging_when_no_candidate_is_safe():
    graph = graph_for("I need belonging.")
    operation = "choose_relational_configuration"
    candidate = CandidateRecomposition(
        id="belonging.original_handle",
        label="belonging",
        operation=operation,
        required_edges=(EdgeRequirement("speaker", "needs", "belonging"),),
        forbidden_if=(GuardPredicate.MERGES_UNRESOLVED_BRANCHES,),
        unresolved_blockers=("belonging.social", "belonging.place"),
        omitted_dimensions=("belonging.social", "belonging.place"),
        safe_for=("repeat_source_wording",),
        unsafe_for=(operation,),
    )

    rejected = RecompositionGuard().evaluate_candidate(graph, candidate, operation)
    decision = RecompositionGuard().decide(graph, (candidate,), operation)

    assert rejected.outcome == RecompositionOutcome.REJECT
    assert decision.outcome == RecompositionOutcome.RETAIN_HIGH_DIMENSIONAL
    assert decision.candidate_id is None
    assert decision.retained_edge_ids == tuple(edge.id for edge in graph.edges)
    assert GuardPredicate.UNRESOLVED_BLOCKER in finding_codes(decision)


def test_falsifier_rejects_causal_strengthening_and_intrinsic_judgment():
    harmony = graph_for("Harmony is important.")
    cause_operation = "infer_cause"
    cause_candidate = CandidateRecomposition(
        id="suppression.causes_signal_loss",
        label="conflict suppression causes signal loss",
        operation=cause_operation,
        required_edges=(
            EdgeRequirement("conflict_suppression", "causes", "signal_preservation"),
        ),
        forbidden_if=(
            GuardPredicate.STRENGTHENS_RELATION,
            GuardPredicate.ADDS_SENSITIVE_RELATION,
        ),
        safe_for=(cause_operation,),
    )
    cause_decision = RecompositionGuard().evaluate_candidate(
        harmony, cause_candidate, cause_operation
    )
    assert GuardPredicate.STRENGTHENS_RELATION in finding_codes(cause_decision)
    assert GuardPredicate.ADDS_SENSITIVE_RELATION in finding_codes(cause_decision)

    property_operation = "describe_intrinsic_property"
    property_candidate = CandidateRecomposition(
        id="harmony.intrinsically_important",
        label="intrinsically important harmony",
        operation=property_operation,
        required_edges=(
            EdgeRequirement("harmony", "has_property", "positive_importance"),
        ),
        forbidden_if=(GuardPredicate.TURNS_JUDGMENT_INTRINSIC,),
        safe_for=(property_operation,),
    )
    property_decision = RecompositionGuard().evaluate_candidate(
        harmony, property_candidate, property_operation
    )
    assert GuardPredicate.TURNS_JUDGMENT_INTRINSIC in finding_codes(property_decision)


def test_falsifier_detects_merge_of_exclusive_good_engineer_readings():
    graph = graph_for("Good engineers know heap internals.")
    operation = "compress_good_engineer_reading"
    candidate = CandidateRecomposition(
        id="good.combined_reading",
        label="heap knowledge defines and predicts good engineers",
        operation=operation,
        required_edges=(
            EdgeRequirement("good_evaluator", "sensitive_to", "heap_internals"),
            EdgeRequirement("good_engineer", "tend_to_have", "heap_internals"),
        ),
        forbidden_if=(GuardPredicate.MERGES_UNRESOLVED_BRANCHES,),
        safe_for=(operation,),
    )

    decision = RecompositionGuard().evaluate_candidate(graph, candidate, operation)

    assert decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.MERGES_UNRESOLVED_BRANCHES in finding_codes(decision)


def test_falsifier_does_not_drop_direction_qualifiers():
    graph = graph_for("Harmony is important.")
    operation = "describe_suppression_effect"
    candidate = CandidateRecomposition(
        id="suppression.unspecified_effect",
        label="conflict suppression affects signal preservation",
        operation=operation,
        required_edges=(
            EdgeRequirement("conflict_suppression", "affects", "signal_preservation"),
        ),
        forbidden_if=(GuardPredicate.DROPS_QUALIFIER,),
        safe_for=(operation,),
    )

    decision = RecompositionGuard().evaluate_candidate(graph, candidate, operation)

    assert decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.DROPS_QUALIFIER in finding_codes(decision)


def test_recomposition_records_serialize_stable_predicate_codes():
    candidate = CandidateRecomposition(
        id="candidate",
        label="label",
        operation="operation",
        required_edges=(EdgeRequirement("a", "relation", "b"),),
        forbidden_if=(GuardPredicate.INVENTS_EQUIVALENCE,),
        unresolved_blockers=("branch.a",),
    )

    payload = candidate.to_dict()
    assert payload["forbidden_if"] == ["invents_equivalence"]
    assert payload["unresolved_blockers"] == ["branch.a"]


def test_shared_edge_does_not_count_as_merging_branches_and_unknown_ids_fail():
    graph = graph_for("I need belonging.")
    shared_operation = "name_shared_candidate"
    shared_candidate = CandidateRecomposition(
        id="belonging.recognition_only",
        label="recognition",
        operation=shared_operation,
        required_edges=(EdgeRequirement("belonging", "factors_into", "recognition"),),
        forbidden_if=(GuardPredicate.MERGES_UNRESOLVED_BRANCHES,),
        safe_for=(shared_operation,),
    )
    shared_decision = RecompositionGuard().evaluate_candidate(
        graph, shared_candidate, shared_operation
    )
    assert GuardPredicate.MERGES_UNRESOLVED_BRANCHES not in finding_codes(shared_decision)
    assert GuardPredicate.REQUIRED_EDGE_UNLICENSED in finding_codes(shared_decision)

    unknown_operation = "unknown_reference_check"
    unknown_candidate = CandidateRecomposition(
        id="unknown.items",
        label="unknown",
        operation=unknown_operation,
        required_edges=(EdgeRequirement("speaker", "needs", "belonging"),),
        unresolved_blockers=("missing.branch",),
        omitted_dimensions=("missing.dimension",),
        safe_for=(unknown_operation,),
    )
    unknown_decision = RecompositionGuard().evaluate_candidate(
        graph, unknown_candidate, unknown_operation
    )
    assert GuardPredicate.UNKNOWN_ITEM_REFERENCE in finding_codes(unknown_decision)


def test_respect_rejects_definition_and_unlicensed_obedience_requirement():
    sentence = "Respect is important."
    graph = graph_for(sentence)

    definition = fixture_candidate(
        sentence, "define_respect", "respect means deference"
    )
    definition_decision = RecompositionGuard().evaluate_candidate(
        graph, definition, RecompositionOperation("define_respect")
    )
    definition_codes = finding_codes(definition_decision)
    assert definition_decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.REQUIRED_EDGE_UNLICENSED in definition_codes
    assert GuardPredicate.INVENTS_EQUIVALENCE in definition_codes
    assert GuardPredicate.PROMOTES_IMPLEMENTATION in definition_codes
    assert GuardPredicate.UNRESOLVED_BLOCKER in definition_codes
    assert GuardPredicate.DROPS_OPERATION_RELEVANT_DIMENSION in definition_codes

    obedience = fixture_candidate(
        sentence, "infer_respect_requirement", "respect requires obedience"
    )
    obedience_decision = RecompositionGuard().evaluate_candidate(
        graph, obedience, RecompositionOperation("infer_respect_requirement")
    )
    obedience_codes = finding_codes(obedience_decision)
    assert obedience_decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.REQUIRED_EDGE_MISSING in obedience_codes
    assert GuardPredicate.ADDS_SENSITIVE_RELATION in obedience_codes
    assert GuardPredicate.COMPLETES_FROM_DEFAULT_PRIOR in obedience_codes


def test_harmony_rejects_implementation_as_definition_and_retains_signal_difference():
    sentence = "Harmony is important."
    graph = graph_for(sentence)
    candidate = fixture_candidate(
        sentence, "define_harmony", "harmony means conflict suppression"
    )
    decision = RecompositionGuard().evaluate_candidate(
        graph, candidate, RecompositionOperation("define_harmony")
    )
    codes = finding_codes(decision)

    assert decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.REQUIRED_EDGE_UNLICENSED in codes
    assert GuardPredicate.INVENTS_EQUIVALENCE in codes
    assert GuardPredicate.PROMOTES_IMPLEMENTATION in codes
    assert GuardPredicate.UNRESOLVED_BLOCKER in codes
    assert GuardPredicate.DROPS_OPERATION_RELEVANT_DIMENSION in codes
    assert "resolution.signal" in next(
        finding.item_ids
        for finding in decision.falsification_findings
        if finding.predicate == GuardPredicate.DROPS_OPERATION_RELEVANT_DIMENSION
    )


def test_good_engineer_retention_and_selected_branch_licensing_are_operation_local():
    sentence = "Good engineers know heap internals."
    graph = graph_for(sentence)
    before = graph.to_dict()
    operation_id = "summarize_sentence_meaning"

    retained = RecompositionGuard().decide(
        graph,
        proposals_for(sentence, operation_id),
        RecompositionOperation(operation_id),
    )
    assert retained.outcome == RecompositionOutcome.RETAIN_HIGH_DIMENSIONAL
    assert retained.candidate_id is None
    assert retained.licensed_edge_ids == ("claim.good_group_knows",)
    assert GuardPredicate.UNRESOLVED_BLOCKER in finding_codes(retained)
    assert retained.retained_edge_ids == tuple(edge.id for edge in graph.edges)

    normative = fixture_candidate(
        sentence,
        operation_id,
        "the good-engineer evaluator is sensitive to heap-internals knowledge",
    )
    selected_operation = RecompositionOperation(
        operation_id,
        ("good.normative_branch",),
    )
    accepted = RecompositionGuard().evaluate_candidate(
        graph, normative, selected_operation
    )
    assert accepted.outcome == RecompositionOutcome.ACCEPT
    assert set(accepted.licensed_edge_ids) == {
        "claim.good_group_knows",
        "good.reading.uses",
        "good.reading.evaluates",
        "good.reading.normative",
    }
    assert graph.to_dict() == before
    assert graph.edge("good.reading.normative").status == "unresolved"
    assert {item.kind for item in graph.edge("good.reading.normative").provenance} == {
        "source_text",
        "inference_rule",
    }
    assert "good.sensitivity.judgment" not in accepted.licensed_edge_ids

    rendered = render_recomposition_decision(
        graph, selected_operation, accepted, normative
    )
    assert "rule candidate · unresolved in graph · selected for operation" in rendered
    assert rendered.count("[source assertion]") == 1
    assert (
        "good-engineer evaluator --sensitive to--> heap internals\n"
        "    [rule candidate · unresolved in graph · selected for operation]"
    ) in rendered


def test_invalid_exclusive_branch_selection_is_rejected_without_graph_mutation():
    sentence = "Good engineers know heap internals."
    graph = graph_for(sentence)
    before = graph.to_dict()
    candidate = fixture_candidate(
        sentence,
        "summarize_sentence_meaning",
        "the good-engineer evaluator is sensitive to heap-internals knowledge",
    )
    operation = RecompositionOperation(
        "summarize_sentence_meaning",
        ("good.normative_branch", "good.descriptive_branch"),
    )
    decision = RecompositionGuard().evaluate_candidate(graph, candidate, operation)
    assert decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.INVALID_BRANCH_SELECTION in finding_codes(decision)
    assert graph.to_dict() == before


def test_provenance_disagreement_is_checked_only_when_operation_requires_it():
    sentence = "Good engineers know heap internals."
    graph = graph_for(sentence)
    candidate = fixture_candidate(
        sentence,
        "summarize_sentence_meaning",
        "the good-engineer evaluator is sensitive to heap-internals knowledge",
    )
    ordinary = RecompositionOperation(
        "summarize_sentence_meaning", ("good.normative_branch",)
    )
    sensitive = RecompositionOperation(
        "summarize_sentence_meaning",
        ("good.normative_branch",),
        provenance_sensitive=True,
    )

    ordinary_decision = RecompositionGuard().evaluate_candidate(
        graph, candidate, ordinary
    )
    sensitive_decision = RecompositionGuard().evaluate_candidate(
        graph, candidate, sensitive
    )
    assert ordinary_decision.outcome == RecompositionOutcome.ACCEPT
    assert sensitive_decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.ERASES_PROVENANCE_DISAGREEMENT in finding_codes(
        sensitive_decision
    )


def test_mentor_rejects_authority_and_obligation_but_accepts_exact_evaluation_report():
    sentence = "A mentor should guide you."
    graph = graph_for(sentence)
    cases = (
        (
            "infer_mentor_authority",
            "mentor has authority over addressee",
            RecompositionOutcome.REJECT,
        ),
        (
            "infer_addressee_obligation",
            "addressee is obligated to obey mentor",
            RecompositionOutcome.REJECT,
        ),
        (
            "report_normative_evaluation",
            "the guidance action is positively normatively evaluated",
            RecompositionOutcome.ACCEPT,
        ),
    )
    for operation_id, label, expected in cases:
        candidate = fixture_candidate(sentence, operation_id, label)
        decision = RecompositionGuard().evaluate_candidate(
            graph, candidate, RecompositionOperation(operation_id)
        )
        assert decision.outcome == expected
        if expected == RecompositionOutcome.REJECT:
            assert GuardPredicate.ADDS_SENSITIVE_RELATION in finding_codes(decision)
        else:
            assert set(decision.licensed_edge_ids) == {
                "claim.should.uses",
                "claim.should.evaluates",
                "claim.should.result",
            }
    assert not any(edge.relation == "obligated_to" for edge in graph.edges)
    assert not any(edge.relation == "has_authority_over" for edge in graph.edges)


def test_healthy_relationship_requires_report_is_accepted_but_causation_is_rejected():
    sentence = "Healthy relationships require honesty."
    graph = graph_for(sentence)

    cause = fixture_candidate(
        sentence, "infer_relationship_cause", "honesty causes relationship health"
    )
    cause_decision = RecompositionGuard().evaluate_candidate(
        graph, cause, RecompositionOperation("infer_relationship_cause")
    )
    assert cause_decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.STRENGTHENS_RELATION in finding_codes(cause_decision)
    assert GuardPredicate.ADDS_SENSITIVE_RELATION in finding_codes(cause_decision)

    report = fixture_candidate(
        sentence,
        "report_source_requirement",
        "the source treats honesty as required",
    )
    report_decision = RecompositionGuard().evaluate_candidate(
        graph, report, RecompositionOperation("report_source_requirement")
    )
    assert report_decision.outcome == RecompositionOutcome.ACCEPT
    assert report_decision.licensed_edge_ids == (
        "claim.evaluated_category_requires",
    )


def test_good_parent_surface_report_is_accepted_but_jurisdiction_is_rejected():
    sentence = "Good parents set boundaries."
    graph = graph_for(sentence)

    jurisdiction = fixture_candidate(
        sentence,
        "infer_parent_jurisdiction",
        "parents have jurisdiction over children",
    )
    jurisdiction_decision = RecompositionGuard().evaluate_candidate(
        graph, jurisdiction, RecompositionOperation("infer_parent_jurisdiction")
    )
    assert jurisdiction_decision.outcome == RecompositionOutcome.REJECT
    assert GuardPredicate.ADDS_SENSITIVE_RELATION in finding_codes(
        jurisdiction_decision
    )

    report = fixture_candidate(
        sentence, "report_source_statement", "good parents set boundaries"
    )
    report_decision = RecompositionGuard().evaluate_candidate(
        graph, report, RecompositionOperation("report_source_statement")
    )
    assert report_decision.outcome == RecompositionOutcome.ACCEPT
    assert report_decision.licensed_edge_ids == ("claim.good_group_action",)


def test_recomposition_decisions_and_rendering_are_deterministic_and_non_mutating():
    sentence = "Respect is important."
    graph = graph_for(sentence)
    before = graph.to_dict()
    candidate = fixture_candidate(
        sentence, "define_respect", "respect means deference"
    )
    operation = RecompositionOperation("define_respect")
    first = RecompositionGuard().evaluate_candidate(graph, candidate, operation)
    second = RecompositionGuard().evaluate_candidate(graph, candidate, operation)

    assert first.to_dict() == second.to_dict()
    assert render_recomposition_decision(
        graph, operation, first, candidate
    ) == render_recomposition_decision(graph, operation, second, candidate)
    assert graph.to_dict() == before


if __name__ == "__main__":
    test_accepts_fully_licensed_task_scoped_judgment_projection()
    test_rejects_implementation_promoted_to_handle_definition()
    test_retains_high_dimensional_belonging_when_no_candidate_is_safe()
    test_falsifier_rejects_causal_strengthening_and_intrinsic_judgment()
    test_falsifier_detects_merge_of_exclusive_good_engineer_readings()
    test_falsifier_does_not_drop_direction_qualifiers()
    test_recomposition_records_serialize_stable_predicate_codes()
    test_shared_edge_does_not_count_as_merging_branches_and_unknown_ids_fail()
    test_respect_rejects_definition_and_unlicensed_obedience_requirement()
    test_harmony_rejects_implementation_as_definition_and_retains_signal_difference()
    test_good_engineer_retention_and_selected_branch_licensing_are_operation_local()
    test_invalid_exclusive_branch_selection_is_rejected_without_graph_mutation()
    test_provenance_disagreement_is_checked_only_when_operation_requires_it()
    test_mentor_rejects_authority_and_obligation_but_accepts_exact_evaluation_report()
    test_healthy_relationship_requires_report_is_accepted_but_causation_is_rejected()
    test_good_parent_surface_report_is_accepted_but_jurisdiction_is_rejected()
    test_recomposition_decisions_and_rendering_are_deterministic_and_non_mutating()
