from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass

from ontology.schema import CollapsedVariable, MatchEvidence, OntologyEntry, OperatorGraph, TransformResult
from ontology.store import OntologyStore


@dataclass(frozen=True)
class CollapseRule:
    name: str
    patterns: tuple[str, ...]
    collapsed_variables: tuple[str, ...]
    hidden_variables: tuple[str, ...]
    operators: tuple[str, ...] = ("compression",)
    objects: tuple[str, ...] = ()


COLLAPSE_RULES = (
    CollapseRule(
        name="trivia_hiring",
        patterns=(r"\bgood engineers?\b.*\b(heap|internals?)\b",),
        collapsed_variables=("trivia_knowledge = engineering_value",),
        hidden_variables=(
            "judgment",
            "debugging",
            "system_modeling",
            "AI_navigation",
            "curiosity",
        ),
        operators=("compression", "prediction"),
    ),
    CollapseRule(
        name="harmony_truth_collapse",
        patterns=(r"\bharmony\b.*\bimportant\b",),
        collapsed_variables=("harmony = truth", "harmony = health"),
        hidden_variables=(
            "contradiction",
            "signal_preservation",
            "disagreement_as_information",
        ),
        objects=("harmony",),
        operators=("compression", "coordination"),
    ),
    CollapseRule(
        name="identity_behavior_collapse",
        patterns=(r"\bi am (a |an )?\w+\b", r"\bwe are (a |an )?\w+\b"),
        collapsed_variables=("identity = behavior",),
        hidden_variables=("frequency", "context", "competence", "role", "obligation"),
        objects=("identity",),
        operators=("compression", "coordination"),
    ),
    CollapseRule(
        name="college_best_years",
        patterns=(r"\bcollege\b.*\bbest years\b",),
        collapsed_variables=("remembered_peak = life_value",),
        hidden_variables=(
            "current_options",
            "nostalgia",
            "comparison_set",
            "agency",
            "time_horizon",
        ),
        operators=("compression", "representation"),
    ),
    CollapseRule(
        name="silence_as_loaded_object",
        patterns=(r"\bsilence\b.*\b(agree|agreement|means)\b",),
        collapsed_variables=("silence = agreement",),
        hidden_variables=(
            "fear",
            "uncertainty",
            "power_difference",
            "conflict_avoidance",
            "missing_channel",
        ),
        operators=("compression", "prediction"),
    ),
)


class TransformAPI:
    def __init__(self, store: OntologyStore):
        self.store = store

    def expand(self, sentence: str) -> TransformResult:
        matched_objects = self._match_entries(sentence, "object")
        matched_operators = self._match_entries(sentence, "operator")
        entries = self._unique_entries([*matched_objects, *matched_operators])
        collapsed_variables = self.detect_collapsed_variables(sentence)

        objects = self._names(entry for entry in entries if entry.type == "object")
        direct_operators = self._names(entry for entry in entries if entry.type == "operator")
        implemented_operators = self._flatten(entry.implements for entry in entries)
        collapse_operators = self._flatten(
            self._collapse_rule_for(collapse.evidence).operators
            for collapse in collapsed_variables
        )
        collapse_objects = self._flatten(
            self._collapse_rule_for(collapse.evidence).objects
            for collapse in collapsed_variables
        )
        objects = self._unique([*objects, *collapse_objects])
        operators = self._unique([*direct_operators, *implemented_operators, *collapse_operators])
        complements = self.find_complements(sentence)
        missing_complements = self._missing_complements(sentence, complements)
        transforms = self._flatten(entry.transforms for entry in entries)
        implementations = self.find_competing_implementations(sentence)
        hidden = self.find_hidden_assumptions(sentence)
        suppressed = self._flatten(entry.suppressed_variables for entry in entries)
        collapsed_hidden = self._flatten(
            collapse.missing_variables for collapse in collapsed_variables
        )
        compressions = self.find_compressions(sentence)
        warnings = self._warnings_for(missing_complements)
        evidence = tuple(self._evidence(sentence, entries))
        graph = self.extract_operator_graph(sentence)

        return TransformResult(
            sentence=sentence,
            objects=tuple(objects),
            operators=tuple(operators),
            compressions=tuple(compressions),
            collapsed_variables=tuple(collapsed_variables),
            hidden_variables=tuple(self._unique([*hidden, *suppressed, *collapsed_hidden])),
            complements=tuple(missing_complements),
            competing_implementations=tuple(implementations),
            warnings=tuple(warnings),
            transforms=tuple(transforms),
            evidence=evidence,
            operator_graph=graph,
        )

    def detect_collapsed_variables(self, sentence: str) -> list[CollapsedVariable]:
        normalized = sentence.lower()
        collapsed: list[CollapsedVariable] = []
        for rule in COLLAPSE_RULES:
            if any(re.search(pattern, normalized) for pattern in rule.patterns):
                collapsed.extend(
                    CollapsedVariable(
                        collapse=collapse,
                        missing_variables=rule.hidden_variables,
                        evidence=rule.name,
                    )
                    for collapse in rule.collapsed_variables
                )
        return self._unique_collapses(collapsed)

    def find_compressions(self, sentence: str) -> list[str]:
        entries = self._matched_entries(sentence)
        compressions = []
        for entry in entries:
            compressions.extend(entry.common_compressions)
        return self._unique(compressions)

    def find_hidden_assumptions(self, sentence: str) -> list[str]:
        assumptions: list[str] = []
        for entry in self._matched_entries(sentence):
            if entry.type == "object":
                assumptions.append(f"{entry.name}_is_single_object")
            if entry.name == "identity":
                assumptions.append("compressed_label_is_real_self")
            if entry.name == "harmony":
                assumptions.append("coordination_can_be_obtained_without_signal_loss")
        return self._unique(assumptions)

    def find_complements(self, sentence: str) -> list[str]:
        complements: list[str] = []
        for entry in self._matched_entries(sentence):
            complements.extend(entry.complements)
            for operator_name in entry.implements:
                complements.extend(self.store.get(operator_name).complements)
        for collapse in self.detect_collapsed_variables(sentence):
            for operator_name in self._collapse_rule_for(collapse.evidence).operators:
                if operator_name in self.store._entries:
                    complements.extend(self.store.get(operator_name).complements)
        return self._unique(complements)

    def find_competing_implementations(self, sentence: str) -> list[str]:
        implementations: list[str] = []
        for entry in self._matched_entries(sentence):
            implementations.extend(entry.competing_implementations)
        return self._unique(implementations)

    def decompose_identity(self, sentence: str) -> TransformResult:
        return self._decompose_named_object(sentence, "identity")

    def decompose_belonging(self, sentence: str) -> TransformResult:
        return self._decompose_named_object(sentence, "belonging")

    def decompose_harmony(self, sentence: str) -> TransformResult:
        return self._decompose_named_object(sentence, "harmony")

    def extract_operator_graph(self, sentence: str) -> OperatorGraph:
        entries = self._matched_entries(sentence)
        objects = self._names(entry for entry in entries if entry.type == "object")
        direct_operators = self._names(entry for entry in entries if entry.type == "operator")
        implemented_operators = self._flatten(entry.implements for entry in entries)
        operators = self._unique([*direct_operators, *implemented_operators])
        complements = self.find_complements(sentence)
        transforms = self._flatten(entry.transforms for entry in entries)
        edges: list[tuple[str, str, str]] = []

        for entry in entries:
            for operator_name in entry.implements:
                edges.append((entry.name, "implements", operator_name))
            for complement in entry.complements:
                edges.append((entry.name, "requires_complement", complement))
            for transform in entry.transforms:
                edges.append((entry.name, "uses_transform", transform))
            for implementation in entry.competing_implementations:
                edges.append((entry.name, "can_be_implemented_as", implementation))

        for operator_name in operators:
            if operator_name in self.store._entries:
                for complement in self.store.get(operator_name).complements:
                    edges.append((operator_name, "requires_complement", complement))

        return OperatorGraph(
            objects=tuple(objects),
            operators=tuple(operators),
            complements=tuple(complements),
            transforms=tuple(transforms),
            edges=tuple(self._unique_edges(edges)),
        )

    def _decompose_named_object(self, sentence: str, name: str) -> TransformResult:
        entry = self.store.get(name)
        if not self._sentence_matches(sentence, entry):
            sentence = f"{sentence} {name}"
        return self.expand(sentence)

    def _match_entries(self, sentence: str, entry_type: str) -> list[OntologyEntry]:
        return [
            entry
            for entry in self.store.by_type(entry_type)
            if self._sentence_matches(sentence, entry)
        ]

    def _matched_entries(self, sentence: str) -> list[OntologyEntry]:
        return self._unique_entries(
            [
                entry
                for entry in self.store.all()
                if entry.type in {"object", "operator"} and self._sentence_matches(sentence, entry)
            ]
        )

    def _sentence_matches(self, sentence: str, entry: OntologyEntry) -> bool:
        normalized = sentence.lower()
        tokens = [entry.name, *entry.aliases]
        if any(re.search(rf"\b{re.escape(token.lower())}\b", normalized) for token in tokens):
            return True
        return any(re.search(pattern, normalized) for pattern in entry.patterns)

    def _evidence(self, sentence: str, entries: list[OntologyEntry]) -> list[MatchEvidence]:
        evidence = []
        for entry in entries:
            evidence.append(
                MatchEvidence(
                    entry=entry.name,
                    reason=f"matched {entry.type}",
                    matched_text=self._first_match(sentence, entry),
                )
            )
        return evidence

    def _first_match(self, sentence: str, entry: OntologyEntry) -> str:
        normalized = sentence.lower()
        for token in [entry.name, *entry.aliases]:
            if re.search(rf"\b{re.escape(token.lower())}\b", normalized):
                return token
        for pattern in entry.patterns:
            match = re.search(pattern, normalized)
            if match:
                return match.group(0)
        return ""

    def _warnings_for(self, missing_complements: list[str]) -> list[str]:
        if not missing_complements:
            return []
        return ["complement not represented"]

    def _missing_complements(self, sentence: str, complements: list[str]) -> list[str]:
        missing = []
        for complement in complements:
            entry = self.store.get(complement)
            if not self._sentence_matches(sentence, entry):
                missing.append(complement)
        return self._unique(missing)

    def _collapse_rule_for(self, name: str) -> CollapseRule:
        for rule in COLLAPSE_RULES:
            if rule.name == name:
                return rule
        raise KeyError(name)

    def _unique_collapses(self, values: list[CollapsedVariable]) -> list[CollapsedVariable]:
        by_collapse: OrderedDict[str, CollapsedVariable] = OrderedDict()
        for value in values:
            by_collapse.setdefault(value.collapse, value)
        return list(by_collapse.values())

    def _unique_entries(self, entries: list[OntologyEntry]) -> list[OntologyEntry]:
        by_name: OrderedDict[str, OntologyEntry] = OrderedDict()
        for entry in entries:
            by_name.setdefault(entry.name, entry)
        return list(by_name.values())

    def _unique_edges(self, edges: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        return list(OrderedDict((edge, None) for edge in edges).keys())

    def _unique(self, values: list[str]) -> list[str]:
        return list(OrderedDict((value, None) for value in values if value).keys())

    def _flatten(self, groups) -> list[str]:
        return self._unique([item for group in groups for item in group])

    def _names(self, entries) -> list[str]:
        return self._unique([entry.name for entry in entries])
