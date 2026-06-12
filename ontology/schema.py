from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EntryType = Literal["operator", "object", "transform", "complement"]


@dataclass(frozen=True)
class OntologyEntry:
    name: str
    type: EntryType
    description: str = ""
    generator: tuple[str, ...] = ()
    implements: tuple[str, ...] = ()
    benefits: tuple[str, ...] = ()
    costs: tuple[str, ...] = ()
    suppressed_variables: tuple[str, ...] = ()
    complements: tuple[str, ...] = ()
    competing_implementations: tuple[str, ...] = ()
    common_compressions: tuple[str, ...] = ()
    failure_modes: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    transforms: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "OntologyEntry":
        required = ("name", "type")
        missing = [key for key in required if key not in raw]
        if missing:
            raise ValueError(f"Ontology entry missing required fields: {missing}")

        def tuple_of_strings(key: str) -> tuple[str, ...]:
            value = raw.get(key)
            if value is None:
                return ()
            if not isinstance(value, list):
                raise ValueError(f"{raw['name']}.{key} must be a list")
            if not all(isinstance(item, str) for item in value):
                raise ValueError(f"{raw['name']}.{key} must contain only strings")
            return tuple(value)

        return cls(
            name=str(raw["name"]),
            type=raw["type"],
            description=str(raw.get("description", "")),
            generator=tuple_of_strings("generator"),
            implements=tuple_of_strings("implements"),
            benefits=tuple_of_strings("benefits"),
            costs=tuple_of_strings("costs"),
            suppressed_variables=tuple_of_strings("suppressed_variables"),
            complements=tuple_of_strings("complements"),
            competing_implementations=tuple_of_strings("competing_implementations"),
            common_compressions=tuple_of_strings("common_compressions"),
            failure_modes=tuple_of_strings("failure_modes"),
            examples=tuple_of_strings("examples"),
            transforms=tuple_of_strings("transforms"),
            aliases=tuple_of_strings("aliases"),
            patterns=tuple_of_strings("patterns"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "generator": list(self.generator),
            "implements": list(self.implements),
            "benefits": list(self.benefits),
            "costs": list(self.costs),
            "suppressed_variables": list(self.suppressed_variables),
            "complements": list(self.complements),
            "competing_implementations": list(self.competing_implementations),
            "common_compressions": list(self.common_compressions),
            "failure_modes": list(self.failure_modes),
            "examples": list(self.examples),
            "transforms": list(self.transforms),
            "aliases": list(self.aliases),
            "patterns": list(self.patterns),
        }


@dataclass(frozen=True)
class MatchEvidence:
    entry: str
    reason: str
    matched_text: str

    def to_dict(self) -> dict[str, str]:
        return {
            "entry": self.entry,
            "reason": self.reason,
            "matched_text": self.matched_text,
        }


@dataclass(frozen=True)
class OperatorGraph:
    objects: tuple[str, ...] = ()
    operators: tuple[str, ...] = ()
    complements: tuple[str, ...] = ()
    transforms: tuple[str, ...] = ()
    edges: tuple[tuple[str, str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "objects": list(self.objects),
            "operators": list(self.operators),
            "complements": list(self.complements),
            "transforms": list(self.transforms),
            "edges": [
                {"source": source, "relation": relation, "target": target}
                for source, relation, target in self.edges
            ],
        }


@dataclass(frozen=True)
class CollapsedVariable:
    collapse: str
    missing_variables: tuple[str, ...] = ()
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "collapse": self.collapse,
            "missing_variables": list(self.missing_variables),
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class TransformResult:
    sentence: str
    objects: tuple[str, ...] = ()
    operators: tuple[str, ...] = ()
    compressions: tuple[str, ...] = ()
    collapsed_variables: tuple[CollapsedVariable, ...] = ()
    hidden_variables: tuple[str, ...] = ()
    complements: tuple[str, ...] = ()
    competing_implementations: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    transforms: tuple[str, ...] = ()
    evidence: tuple[MatchEvidence, ...] = ()
    operator_graph: OperatorGraph = field(default_factory=OperatorGraph)

    @property
    def possible_implementations(self) -> tuple[str, ...]:
        return self.competing_implementations

    @property
    def hidden_assumptions(self) -> tuple[str, ...]:
        return self.hidden_variables

    @property
    def suppressed_variables(self) -> tuple[str, ...]:
        return self.hidden_variables

    @property
    def common_compressions(self) -> tuple[str, ...]:
        return self.compressions

    @property
    def missing_complements(self) -> tuple[str, ...]:
        return self.complements

    def to_dict(self) -> dict[str, Any]:
        return {
            "sentence": self.sentence,
            "objects": list(self.objects),
            "operators": list(self.operators),
            "compressions": list(self.compressions),
            "collapsed_variables": [item.to_dict() for item in self.collapsed_variables],
            "hidden_variables": list(self.hidden_variables),
            "complements": list(self.complements),
            "competing_implementations": list(self.competing_implementations),
            "warnings": list(self.warnings),
        }
