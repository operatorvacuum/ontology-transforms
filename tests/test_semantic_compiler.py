from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology import PROJECTION_SAFETY_INVARIANT, SemanticCompiler, render_projection

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
    assert branches["belonging.social"].group_id == "belonging.configurations"
    assert branches["belonging.place"].group_id == "belonging.configurations"
    assert branches["belonging.social"].mode == "one_or_more"
    assert "belonging.recognition" in branches["belonging.place"].edge_ids
    assert dict(edges[("belonging", "factors_into", "recurrence")].qualifiers) == {
        "necessity": "optional"
    }

    projected = compilation.projection("factor").graph
    projected_branches = {branch.id: branch for branch in projected.branches}
    assert "belonging.recognition" in projected_branches["belonging.social"].edge_ids
    assert "belonging.recognition" in projected_branches["belonging.place"].edge_ids


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
    assert ("good_engineer", "tend_to_have", "heap_internals") in edges
    assert ("good_evaluator", "sensitive_to", "judgment") in edges

    branches = {branch.id: branch for branch in compilation.graph.branches}
    assert branches["good.normative_branch"].status == "unresolved"
    assert branches["good.descriptive_branch"].status == "unresolved"
    assert branches["good.normative_branch"].group_id == "good.primary_readings"
    assert branches["good.descriptive_branch"].group_id == "good.primary_readings"
    assert branches["good.broader_model"].group_id == "good.recursive_candidate_expansion"
    assert branches["good.broader_model"].depth == 1
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
            projected_ids = {
                *(edge.id for edge in projection.graph.edges),
                *(node.id for node in projection.graph.nodes),
                *(branch.id for branch in projection.graph.branches),
            }
            full_ids = {
                *(edge.id for edge in compilation.graph.edges),
                *(node.id for node in compilation.graph.nodes),
                *(branch.id for branch in compilation.graph.branches),
            }
            omitted_ids = full_ids - projected_ids
            recorded_ids = {
                item_id for loss in projection.losses for item_id in loss.item_ids
            }
            assert omitted_ids <= recorded_ids
            for loss in projection.losses:
                assert loss.item_ids
                assert loss.description
                assert loss.semantic_role
                assert loss.reason
                assert loss.safe_for
                assert loss.unsafe_for
    assert PROJECTION_SAFETY_INVARIANT == (
        "Every projection records what it omitted or merged and why that was safe."
    )


def test_nodes_have_no_global_kind_taxonomy():
    compilation = compile_fixture("belonging.yaml")
    payload = compilation.to_dict()
    for state in payload["states"]:
        for node in state["graph"]["nodes"]:
            assert set(node) == {"id", "label"}


def test_shared_rendering_requires_explicit_membership_in_every_branch():
    compilation = compile_fixture("belonging.yaml")
    projection = compilation.projection("factor")
    group = [
        branch
        for branch in projection.graph.branches
        if branch.group_id == "belonging.configurations"
    ]
    assert group
    assert all("belonging.recognition" in branch.edge_ids for branch in group)

    rendered = render_projection(projection, compilation.sentence)
    assert "candidate present in every explicitly listed branch" in rendered
    assert rendered.count("factors into → recognition") == 1

    branches = tuple(
        replace(
            branch,
            edge_ids=tuple(
                edge_id
                for edge_id in branch.edge_ids
                if not (branch.id == "belonging.place" and edge_id == "belonging.recognition")
            ),
        )
        for branch in projection.graph.branches
    )
    without_shared_membership = replace(
        projection,
        graph=replace(projection.graph, branches=branches),
    )
    guarded_render = render_projection(without_shared_membership, compilation.sentence)
    assert "candidate present in every explicitly listed branch" not in guarded_render


def test_human_view_separates_source_rule_and_catalog_claims():
    compilation = compile_fixture("good_engineer.yaml")
    rendered = render_projection(compilation.projection("factor"), compilation.sentence)

    assert rendered.count("knows → heap internals") == 1
    assert "[rule candidate · unresolved]" in rendered
    assert "RECURSIVE CANDIDATE EXPANSION" in rendered
    assert "5 optional candidate members hidden at depth 0" in rendered
    assert "sensitive to → judgment" not in rendered

    expanded = SemanticCompiler().compile(compilation.sentence, projection_depth=1)
    expanded_render = render_projection(expanded.projection("factor"), expanded.sentence)
    assert "RECURSIVE CANDIDATE EXPANSION — depth 1" in expanded_render
    assert "[catalog candidate · unresolved]" in expanded_render
    assert "sensitive to → judgment (optional)" in expanded_render
    assert "broader evaluator sensitivities remains unconfirmed" in expanded_render


def test_candidate_edges_are_never_promoted_and_output_is_deterministic():
    for path in FIXTURE_DIR.glob("*.yaml"):
        fixture = load_fixture(path)
        first = SemanticCompiler().compile(fixture["sentence"])
        second = SemanticCompiler().compile(fixture["sentence"])

        branch_edge_ids = {edge_id for branch in first.graph.branches for edge_id in branch.edge_ids}
        assert all(first.graph.edge(edge_id).status != "asserted" for edge_id in branch_edge_ids)
        assert first.to_dict() == second.to_dict()
        assert render_projection(first.projection(fixture["view"]), first.sentence) == render_projection(
            second.projection(fixture["view"]), second.sentence
        )


def test_projection_losses_are_operation_relative_and_exact():
    compilation = compile_fixture("harmony.yaml")
    losses = compilation.projection("implementation").losses

    assert any(loss.semantic_role == "resolution provenance" for loss in losses)
    assert any("lexically matches" in loss.description for loss in losses)
    assert all("implementation" in loss.safe_for for loss in losses)
    assert any("auditing why" in loss.unsafe_for for loss in losses)


def test_default_depth_records_recursive_expansion_as_projection_loss():
    compilation = compile_fixture("good_engineer.yaml")
    projection = compilation.projection("factor")

    assert projection.depth == 0
    assert not any(branch.depth > 0 for branch in projection.graph.branches)
    recursive_losses = [
        loss for loss in projection.losses if loss.semantic_role == "recursive candidate expansion"
    ]
    assert len(recursive_losses) == 1
    assert "good.broader_model" in recursive_losses[0].item_ids
    assert "current depth" in recursive_losses[0].safe_for


def test_one_or_more_and_single_bundle_unresolved_wording():
    belonging = compile_fixture("belonging.yaml")
    belonging_view = render_projection(belonging.projection("factor"), belonging.sentence)
    assert "No configuration has been selected." in belonging_view
    assert "Neither configuration" not in belonging_view

    expanded = SemanticCompiler().compile(
        "Good engineers know heap internals.", projection_depth=1
    )
    expanded_view = render_projection(expanded.projection("factor"), expanded.sentence)
    assert "broader evaluator sensitivities remains unconfirmed" in expanded_view
    assert "zero or more optional members may apply" in expanded_view


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
    test_shared_rendering_requires_explicit_membership_in_every_branch()
    test_human_view_separates_source_rule_and_catalog_claims()
    test_candidate_edges_are_never_promoted_and_output_is_deterministic()
    test_projection_losses_are_operation_relative_and_exact()
    test_default_depth_records_recursive_expansion_as_projection_loss()
    test_one_or_more_and_single_bundle_unresolved_wording()
