from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology import TransformAPI, load_default_ontology

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "examples" / "fixtures"


def api() -> TransformAPI:
    return TransformAPI(load_default_ontology())


def collapses(result):
    return [item["collapse"] for item in result.to_dict()["collapsed_variables"]]


def test_belonging_regression_expands_object_into_implementations():
    result = api().expand("I need belonging.")
    payload = result.to_dict()

    assert payload["objects"] == ["belonging"]
    assert "coordination" in payload["operators"]
    assert "friendship" in payload["competing_implementations"]
    assert "recurring contact" in payload["competing_implementations"]
    assert "belonging_is_single_object" in payload["hidden_variables"]


def test_harmony_regression_decomposes_coordination_and_truth_collapse():
    result = api().expand("Harmony is important.")
    payload = result.to_dict()

    assert "harmony" in payload["objects"]
    assert "coordination" in payload["operators"]
    assert "harmony = truth" in collapses(result)
    assert "harmony = health" in collapses(result)
    assert "contradiction" in payload["hidden_variables"]
    assert "signal_preservation" in payload["complements"]
    assert "complement not represented" in payload["warnings"]


def test_identity_regression_decomposes_graph_compression():
    result = api().expand("I am a teacher.")
    payload = result.to_dict()

    assert "identity" in payload["objects"]
    assert "compression" in payload["operators"]
    assert "identity = behavior" in collapses(result)
    assert "frequency" in payload["hidden_variables"]
    assert "context" in payload["hidden_variables"]
    assert "role" in payload["competing_implementations"]


def test_trivia_hiring_regression_detects_value_collapse():
    result = api().expand("Good engineers know heap internals.")
    payload = result.to_dict()

    assert "trivia_knowledge = engineering_value" in collapses(result)
    assert "judgment" in payload["hidden_variables"]
    assert "debugging" in payload["hidden_variables"]
    assert "AI_navigation" in payload["hidden_variables"]
    assert "compression" in payload["operators"]


def test_represented_complement_is_not_missing():
    result = api().expand("Harmony is important with signal preservation.")
    payload = result.to_dict()

    assert "signal_preservation" not in payload["complements"]
    assert "exit" in payload["complements"]


def test_yaml_fixtures_are_regressions():
    for path in sorted(FIXTURE_DIR.glob("*.yaml")):
        fixture = load_fixture(path)
        payload = api().expand(fixture["sentence"]).to_dict()
        actual_collapses = [item["collapse"] for item in payload["collapsed_variables"]]

        assert_contains(path, payload["objects"], fixture["objects"])
        assert_contains(path, payload["operators"], fixture["operators"])
        assert_contains(path, actual_collapses, fixture["collapsed_variables"])
        assert_contains(path, payload["hidden_variables"], fixture["hidden_variables"])
        assert_contains(path, payload["complements"], fixture["complements"])
        assert_contains(
            path,
            payload["competing_implementations"],
            fixture["competing_implementations"],
        )
        assert_contains(path, payload["warnings"], fixture["warnings"])


def assert_contains(path: Path, actual: list[str], expected: list[str]) -> None:
    missing = [item for item in expected if item not in actual]
    assert not missing, f"{path.name} missing {missing} from {actual}"


def load_fixture(path: Path) -> dict[str, list[str] | str]:
    fixture: dict[str, list[str] | str] = {}
    current_key = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith("  - "):
            fixture[current_key].append(raw_line[4:].strip())
            continue
        key, value = raw_line.split(":", 1)
        current_key = key
        if value.strip():
            fixture[key] = value.strip()
        else:
            fixture[key] = []
    return fixture


if __name__ == "__main__":
    test_belonging_regression_expands_object_into_implementations()
    test_harmony_regression_decomposes_coordination_and_truth_collapse()
    test_identity_regression_decomposes_graph_compression()
    test_trivia_hiring_regression_detects_value_collapse()
    test_represented_complement_is_not_missing()
    test_yaml_fixtures_are_regressions()
