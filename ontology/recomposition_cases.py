from __future__ import annotations

from ontology.recomposition import (
    CandidateRecomposition,
    EdgeRequirement,
    GuardPredicate,
    OperationId,
)
from ontology.schema import Evidence


def _normalized(value: str) -> str:
    return " ".join(value.strip().lower().rstrip(".!?").split())


def proposals_for(sentence: str, operation: str) -> tuple[CandidateRecomposition, ...]:
    """Fixture-scoped proposals for exercising the guard, not candidate generation."""

    return _CASES.get((_normalized(sentence), operation), ())


def proposal_for(
    sentence: str,
    operation: str,
    label: str,
) -> CandidateRecomposition | None:
    normalized_label = _normalized(label)
    return next(
        (
            candidate
            for candidate in proposals_for(sentence, operation)
            if _normalized(candidate.label) == normalized_label
        ),
        None,
    )


def _candidate(
    candidate_id: str,
    label: str,
    operation: str,
    required_edges: tuple[EdgeRequirement, ...],
    *,
    forbidden_if: tuple[GuardPredicate, ...] = (),
    unresolved_blockers: tuple[str, ...] = (),
    omitted_dimensions: tuple[str, ...] = (),
    safe_for: tuple[str, ...] = (),
    unsafe_for: tuple[str, ...] = (),
) -> CandidateRecomposition:
    return CandidateRecomposition(
        id=candidate_id,
        label=label,
        operation=OperationId(operation),
        required_edges=required_edges,
        forbidden_if=forbidden_if,
        unresolved_blockers=unresolved_blockers,
        omitted_dimensions=omitted_dimensions,
        safe_for=tuple(OperationId(item) for item in safe_for),
        unsafe_for=tuple(OperationId(item) for item in unsafe_for),
        provenance=(Evidence("inference_rule", "fixture_scoped_recomposition_proposal"),),
    )


_CASES = {
    (_normalized("Respect is important."), "define_respect"): (
        _candidate(
            "respect.means_deference",
            "respect means deference",
            "define_respect",
            (
                EdgeRequirement("respect", "implemented_by", "deference"),
                EdgeRequirement("respect", "treated_as_equivalent_to", "deference"),
            ),
            forbidden_if=(
                GuardPredicate.INVENTS_EQUIVALENCE,
                GuardPredicate.PROMOTES_IMPLEMENTATION,
            ),
            unresolved_blockers=(
                "respect.recognition_branch",
                "respect.boundaries_branch",
                "respect.politeness_branch",
                "respect.deference_branch",
            ),
            omitted_dimensions=(
                "respect.recognition_branch",
                "respect.boundaries_branch",
                "respect.politeness_branch",
            ),
            unsafe_for=("define_respect",),
        ),
    ),
    (_normalized("Respect is important."), "infer_respect_requirement"): (
        _candidate(
            "respect.requires_obedience",
            "respect requires obedience",
            "infer_respect_requirement",
            (EdgeRequirement("respect", "requires", "obedience"),),
            forbidden_if=(GuardPredicate.ADDS_SENSITIVE_RELATION,),
            unresolved_blockers=(
                "respect.recognition_branch",
                "respect.boundaries_branch",
                "respect.politeness_branch",
                "respect.deference_branch",
            ),
            unsafe_for=("infer_respect_requirement",),
        ),
    ),
    (_normalized("Harmony is important."), "define_harmony"): (
        _candidate(
            "harmony.means_conflict_suppression",
            "harmony means conflict suppression",
            "define_harmony",
            (
                EdgeRequirement("harmony", "implemented_by", "conflict_suppression"),
                EdgeRequirement(
                    "harmony", "treated_as_equivalent_to", "conflict_suppression"
                ),
            ),
            forbidden_if=(
                GuardPredicate.INVENTS_EQUIVALENCE,
                GuardPredicate.PROMOTES_IMPLEMENTATION,
            ),
            unresolved_blockers=(
                "harmony.resolution_branch",
                "harmony.suppression_branch",
            ),
            omitted_dimensions=("harmony.resolution_branch", "resolution.signal"),
            unsafe_for=("define_harmony",),
        ),
    ),
    (_normalized("Good engineers know heap internals."), "summarize_sentence_meaning"): (
        _candidate(
            "good_engineer.normative_summary",
            "the good-engineer evaluator is sensitive to heap-internals knowledge",
            "summarize_sentence_meaning",
            (
                EdgeRequirement(
                    "good_engineer",
                    "knows",
                    "heap_internals",
                    (("modality", "generic"),),
                ),
                EdgeRequirement(
                    "good_engineer_evaluation", "uses_evaluator", "good_evaluator"
                ),
                EdgeRequirement(
                    "good_engineer_evaluation", "evaluates", "engineer_configuration"
                ),
                EdgeRequirement("good_evaluator", "sensitive_to", "heap_internals"),
            ),
            unresolved_blockers=("good.normative_branch",),
            omitted_dimensions=("good.descriptive_branch",),
            safe_for=("summarize_sentence_meaning",),
        ),
        _candidate(
            "good_engineer.descriptive_summary",
            "engineers judged good tend to know heap internals",
            "summarize_sentence_meaning",
            (
                EdgeRequirement(
                    "good_engineer",
                    "knows",
                    "heap_internals",
                    (("modality", "generic"),),
                ),
                EdgeRequirement("good_engineer", "tend_to_have", "heap_internals"),
            ),
            unresolved_blockers=("good.descriptive_branch",),
            omitted_dimensions=("good.normative_branch",),
            safe_for=("summarize_sentence_meaning",),
        ),
    ),
    (_normalized("A mentor should guide you."), "infer_mentor_authority"): (
        _candidate(
            "mentor.authority",
            "mentor has authority over addressee",
            "infer_mentor_authority",
            (EdgeRequirement("mentor_role", "has_authority_over", "addressee"),),
            forbidden_if=(GuardPredicate.ADDS_SENSITIVE_RELATION,),
        ),
    ),
    (_normalized("A mentor should guide you."), "infer_addressee_obligation"): (
        _candidate(
            "addressee.obeys_mentor",
            "addressee is obligated to obey mentor",
            "infer_addressee_obligation",
            (EdgeRequirement("addressee", "obligated_to", "mentor_role"),),
            forbidden_if=(GuardPredicate.ADDS_SENSITIVE_RELATION,),
        ),
    ),
    (_normalized("A mentor should guide you."), "report_normative_evaluation"): (
        _candidate(
            "guidance.normatively_evaluated",
            "the guidance action is positively normatively evaluated",
            "report_normative_evaluation",
            (
                EdgeRequirement(
                    "should_evaluation", "uses_evaluator", "should_evaluator"
                ),
                EdgeRequirement("should_evaluation", "evaluates", "guide_action"),
                EdgeRequirement(
                    "should_evaluation", "yields", "positive_normative_evaluation"
                ),
            ),
            safe_for=("report_normative_evaluation",),
        ),
    ),
    (_normalized("Healthy relationships require honesty."), "infer_relationship_cause"): (
        _candidate(
            "honesty.causes_relationship_health",
            "honesty causes relationship health",
            "infer_relationship_cause",
            (EdgeRequirement("honesty", "causes", "healthy_relationships"),),
            forbidden_if=(
                GuardPredicate.STRENGTHENS_RELATION,
                GuardPredicate.ADDS_SENSITIVE_RELATION,
            ),
        ),
    ),
    (_normalized("Healthy relationships require honesty."), "report_source_requirement"): (
        _candidate(
            "honesty.reported_required",
            "the source treats honesty as required",
            "report_source_requirement",
            (
                EdgeRequirement(
                    "healthy_relationships",
                    "requires",
                    "honesty",
                    (("modality", "generic"),),
                ),
            ),
            safe_for=("report_source_requirement",),
        ),
    ),
    (_normalized("Good parents set boundaries."), "infer_parent_jurisdiction"): (
        _candidate(
            "parents.jurisdiction",
            "parents have jurisdiction over children",
            "infer_parent_jurisdiction",
            (
                EdgeRequirement(
                    "parent_configuration", "has_jurisdiction_over", "children"
                ),
            ),
            forbidden_if=(GuardPredicate.ADDS_SENSITIVE_RELATION,),
        ),
    ),
    (_normalized("Good parents set boundaries."), "report_source_statement"): (
        _candidate(
            "good_parents.surface_report",
            "good parents set boundaries",
            "report_source_statement",
            (
                EdgeRequirement(
                    "good_parents",
                    "set",
                    "boundaries",
                    (("modality", "generic"),),
                ),
            ),
            safe_for=("report_source_statement",),
        ),
    ),
}
