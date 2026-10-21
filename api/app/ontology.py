"""Load and validate an ontology YAML file (blueprint section 2.4).

Validation rules:
- entity type names and predicate names are unique
- predicate names are UPPER_SNAKE_CASE
- every predicate connects only entity types that the file defines
"""

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

    def allows(self, predicate: str, from_type: str, to_type: str) -> bool:
        """True if the ontology permits this (from_type)-[predicate]->(to_type) edge."""
        for p in self.predicates:
            if p.name == predicate:
                return from_type in p.from_types and to_type in p.to_types
        return False


def load_ontology(path: Path) -> Ontology:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Ontology.model_validate(data)
