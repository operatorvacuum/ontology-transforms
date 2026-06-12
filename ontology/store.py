from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ontology.schema import OntologyEntry


class OntologyStore:
    def __init__(self, entries: Iterable[OntologyEntry]):
        self._entries = {entry.name: entry for entry in entries}
        self._validate_references()

    @classmethod
    def from_yaml(cls, path: str | Path) -> "OntologyStore":
        raw = _load_yaml_subset(Path(path))
        if not isinstance(raw, dict) or not isinstance(raw.get("entries"), list):
            raise ValueError("Ontology YAML must contain an entries list")
        return cls(OntologyEntry.from_mapping(item) for item in raw["entries"])

    def get(self, name: str) -> OntologyEntry:
        return self._entries[name]

    def all(self) -> tuple[OntologyEntry, ...]:
        return tuple(self._entries.values())

    def by_type(self, entry_type: str) -> tuple[OntologyEntry, ...]:
        return tuple(entry for entry in self._entries.values() if entry.type == entry_type)

    def _validate_references(self) -> None:
        names = set(self._entries)
        for entry in self._entries.values():
            references = (
                entry.implements
                + entry.complements
                + entry.transforms
            )
            missing = [name for name in references if name not in names]
            if missing:
                raise ValueError(f"{entry.name} references unknown entries: {missing}")


def load_default_ontology() -> OntologyStore:
    return OntologyStore.from_yaml(Path(__file__).parent / "data" / "core.yaml")


def _load_yaml_subset(path: Path) -> dict[str, object]:
    """Load the tiny YAML subset used by ontology data files.

    The project intentionally avoids a runtime dependency so agents can import it
    in constrained environments. Supported shape: a top-level `entries:` list of
    mappings whose values are strings or lists of strings.
    """
    root: dict[str, object] = {}
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    current_key: str | None = None

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if raw_line == "entries:":
            root["entries"] = entries
            continue

        if raw_line.startswith("  - "):
            current = {}
            entries.append(current)
            current_key = None
            key, value = _parse_key_value(raw_line[4:], line_number)
            current[key] = value
            continue

        if raw_line.startswith("      - "):
            if current is None:
                raise ValueError(f"Line {line_number}: nested value before entry")
            if current_key is None:
                raise ValueError(f"Line {line_number}: list item before list key")
            list_value = current[current_key]
            if not isinstance(list_value, list):
                raise ValueError(f"Line {line_number}: current key is not a list")
            list_value.append(_strip_quotes(raw_line[8:].strip()))
            continue

        if raw_line.startswith("    "):
            if current is None:
                raise ValueError(f"Line {line_number}: nested value before entry")
            content = raw_line[4:]
            key, value = _parse_key_value(content, line_number)
            current[key] = value
            current_key = key if value == [] else None
            continue

        raise ValueError(f"Line {line_number}: unsupported YAML syntax")

    return root


def _parse_key_value(content: str, line_number: int) -> tuple[str, object]:
    if ":" not in content:
        raise ValueError(f"Line {line_number}: expected key/value pair")
    key, value = content.split(":", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        raise ValueError(f"Line {line_number}: empty key")
    if not value:
        return key, []
    return key, _strip_quotes(value)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
