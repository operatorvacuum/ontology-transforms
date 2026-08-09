from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology import PROJECTION_SAFETY_INVARIANT, SemanticCompiler

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "examples" / "fixtures"


def compile_fixture(name: str):
    fixture = load_fixture(FIXTURE_DIR / name)
    return SemanticCompiler().compile(fixture["sentence"])


def relations(compilation, pass_name="validated"):
    return {
        (edge.source, edge.relation, edge.target): edge
        for edge in compilation.state(pass_name).graph.edges
    }


def test_belonging_preserves_contextual_factor_branches():
    compilation = compile_fixture("belonging.yaml")
    edges = relations(compilation)

    assert ("speaker", "needs", "belonging") in edges
    assert ("belonging", "factors_into", "recognition") in edges
    assert ("belonging", "factors_into", "access") in edges
    assert ("belonging", "factors_into", "place_attachment") in edges

    branches = {branch.id: branch for branch in compilation.graph.branches}
    assert branches["belonging.social"].status == "unresolved"
    assert branches["belonging.place"].status == "unresolved"
    assert branches["belonging.social"].mode == "one_or_more"
    assert "belonging.recognition" in branches["belonging.place"].edge_ids


def test_harmony_keeps_evaluation_separate_from_implementations():
    compilation = compile_fixture("harmony.yaml")
    edges = relations(compilation)

    assert ("importance_evaluation", "evaluates", "harmony") in edges
    assert ("importance_evaluation", "uses_evaluator", "important_evaluator") in edges
    assert ("harmony", "implemented_by", "conflict_resolution") in edges
    assert ("harmony", "implemented_by", "conflict_suppression") in edges

    resolution = edges[("conflict_resolution", "affects", "signal_preservation")]
    suppression = edges[("conflict_suppression", "affects", "signal_preservation")]
    assert dict(resolution.qualifiers)["direction"] == "increase"
    assert dict(suppression.qualifiers)["direction"] == "decrease"
    assert not any(edge.relation == "treated_as_equivalent_to" for edge in compilation.graph.edges)


def test_good_engineer_preserves_normative_and_descriptive_readings():
    compilation = compile_fixture("good_engineer.yaml")
    edges = relations(compilation)

    assert ("good_engineer", "knows", "heap_internals") in edges
    assert ("good_evaluator", "sensitive_to", "heap_internals") in edges
    assert ("good_engineer", "has_property", "heap_internals") in edges
    assert ("good_evaluator", "sensitive_to", "judgment") in edges

    branches = {branch.id: branch for branch in compilation.graph.branches}
    assert branches["good.normative_branch"].status == "unresolved"
    assert branches["good.descriptive_branch"].status == "unresolved"
    assert branches["good.normative_branch"].mode == "exclusive"
    assert not any(edge.relation == "treated_as_equivalent_to" for edge in compilation.graph.edges)


def test_every_inferred_edge_and_branch_has_first_class_provenance():
    for path in FIXTURE_DIR.glob("*.yaml"):
        compilation = SemanticCompiler().compile(load_fixture(path)["sentence"])
        for edge in compilation.graph.edges:
            if edge.status == "asserted":
                continue
            kinds = {evidence.kind for evidence in edge.provenance}
            assert "source_text" in kinds, edge.id
            assert kinds.intersection(
                {"catalog_fragment", "inference_rule", "model_hypothesis"}
            ), edge.id
        for branch in compilation.graph.branches:
            kinds = {evidence.kind for evidence in branch.provenance}
            assert "source_text" in kinds, branch.id
            assert kinds.intersection(
                {"catalog_fragment", "inference_rule", "model_hypothesis"}
            ), branch.id


def test_intermediate_states_are_exposed_and_monotonic_before_projection():
    compilation = compile_fixture("harmony.yaml")
    assert [state.pass_name for state in compilation.states] == [
        "parsed",
        "resolved",
        "factorized",
        "validated",
    ]
    counts = [len(state.graph.edges) for state in compilation.states]
    assert counts == sorted(counts)
    assert not any(
        edge.relation == "implemented_by"
        for edge in compilation.state("parsed").graph.edges
    )
    assert any(
        edge.relation == "implemented_by"
        for edge in compilation.state("factorized").graph.edges
    )


def test_every_projection_has_an_explicit_loss_ledger():
    for path in FIXTURE_DIR.glob("*.yaml"):
        compilation = SemanticCompiler().compile(load_fixture(path)["sentence"])
        for projection in compilation.projections:
            assert projection.losses
            for loss in projection.losses:
                assert loss.reason
                assert loss.safe_because
                assert "validated graph remains unchanged" in loss.safe_because
    assert PROJECTION_SAFETY_INVARIANT == (
        "Every projection records what it omitted or merged and why that was safe."
    )


def test_nodes_have_no_global_kind_taxonomy():
    compilation = compile_fixture("belonging.yaml")
    payload = compilation.to_dict()
    for state in payload["states"]:
        for node in state["graph"]["nodes"]:
            assert set(node) == {"id", "label"}


def load_fixture(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


if __name__ == "__main__":
    test_belonging_preserves_contextual_factor_branches()
    test_harmony_keeps_evaluation_separate_from_implementations()
    test_good_engineer_preserves_normative_and_descriptive_readings()
    test_every_inferred_edge_and_branch_has_first_class_provenance()
    test_intermediate_states_are_exposed_and_monotonic_before_projection()
    test_every_projection_has_an_explicit_loss_ledger()
    test_nodes_have_no_global_kind_taxonomy()
