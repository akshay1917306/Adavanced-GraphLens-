"""The ontology: which entity types and relationship predicates the graph may contain.

Same validation rules as `api/app/ontology.py` (blueprint 2.4). The pipeline keeps its own copy
because the API and the pipeline are separate packages. This copy adds what extraction needs: a
fingerprint (for cache keys) and the JSON schema that the model's output must follow.
"""

import hashlib
import json
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class EntityType(BaseModel):
    name: str
    description: str
    example: str | None = None


class Predicate(BaseModel):
    name: str
    from_types: list[str] = Field(alias="from", min_length=1)
    to_types: list[str] = Field(alias="to", min_length=1)
    description: str

    @field_validator("name")
    @classmethod
    def upper_snake_case(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
            raise ValueError(f"predicate name must be UPPER_SNAKE_CASE: {value!r}")
        return value


class Ontology(BaseModel):
    name: str
    version: int = Field(ge=1)
    entity_types: list[EntityType] = Field(min_length=1)
    predicates: list[Predicate] = Field(min_length=1)

    @model_validator(mode="after")
    def check_references(self) -> "Ontology":
        type_names = [t.name for t in self.entity_types]
        if len(set(type_names)) != len(type_names):
            raise ValueError("duplicate entity type name")
        predicate_names = [p.name for p in self.predicates]
        if len(set(predicate_names)) != len(predicate_names):
            raise ValueError("duplicate predicate name")
        known = set(type_names)
        for p in self.predicates:
            unknown = (set(p.from_types) | set(p.to_types)) - known
            if unknown:
                raise ValueError(f"predicate {p.name} uses unknown types: {sorted(unknown)}")
        return self

    @property
    def type_names(self) -> list[str]:
        return [t.name for t in self.entity_types]

    @property
    def predicate_names(self) -> list[str]:
        return [p.name for p in self.predicates]

    def allows(self, predicate: str, from_type: str, to_type: str) -> bool:
        """True if the ontology permits this (from_type)-[predicate]->(to_type) edge."""
        for p in self.predicates:
            if p.name == predicate:
                return from_type in p.from_types and to_type in p.to_types
        return False

    def fingerprint(self) -> str:
        """A short hash of the whole ontology; changes when any type or predicate changes."""
        canonical = json.dumps(self.model_dump(by_alias=True), sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def output_schema(self) -> dict:
        """JSON schema for one extraction answer (strict, as OpenAI structured output wants)."""

        def obj(properties: dict) -> dict:
            return {
                "type": "object",
                "additionalProperties": False,
                "required": list(properties),
                "properties": properties,
            }

        entity = obj(
            {
                "name": {"type": "string"},
                "type": {"type": "string", "enum": self.type_names},
                "description": {"type": "string"},
            }
        )
        relationship = obj(
            {
                "source": {"type": "string"},
                "predicate": {"type": "string", "enum": self.predicate_names},
                "target": {"type": "string"},
                "description": {"type": "string"},
                "strength": {"type": "integer"},
            }
        )
        return obj(
            {
                "entities": {"type": "array", "items": entity},
                "relationships": {"type": "array", "items": relationship},
            }
        )


def load_ontology(path: Path) -> Ontology:
    return Ontology.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
