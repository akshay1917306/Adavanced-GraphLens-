from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ontology import Ontology, load_ontology

ONTOLOGY_FILE = Path(__file__).resolve().parents[2] / "ontology" / "research_v1.yaml"


def test_reference_ontology_matches_blueprint():
    ontology = load_ontology(ONTOLOGY_FILE)
    assert ontology.name == "research"
    assert ontology.version == 1
    assert [t.name for t in ontology.entity_types] == [
        "Paper", "Author", "Method", "Dataset", "Task", "Organization",
    ]  # fmt: skip
    assert len(ontology.predicates) == 8


def test_allows_valid_edges_and_rejects_others():
    ontology = load_ontology(ONTOLOGY_FILE)
    assert ontology.allows("USES", "Paper", "Dataset")
    assert ontology.allows("IMPROVES_ON", "Method", "Method")
    assert not ontology.allows("USES", "Dataset", "Paper")  # wrong direction
    assert not ontology.allows("INVENTED", "Paper", "Method")  # unknown predicate


def _minimal(**overrides):
    data = {
        "name": "t",
        "version": 1,
        "entity_types": [{"name": "A", "description": "a"}],
        "predicates": [{"name": "LINKS", "from": ["A"], "to": ["A"], "description": "x"}],
    }
    data.update(overrides)
    return data


def test_rejects_predicate_with_unknown_type():
    bad = _minimal(predicates=[{"name": "LINKS", "from": ["A"], "to": ["B"], "description": "x"}])
    with pytest.raises(ValidationError, match="unknown types"):
        Ontology.model_validate(bad)


def test_rejects_duplicate_entity_type():
    bad = _minimal(entity_types=[{"name": "A", "description": "a"}] * 2)
    with pytest.raises(ValidationError, match="duplicate entity type"):
        Ontology.model_validate(bad)


def test_rejects_lowercase_predicate():
    bad = _minimal(predicates=[{"name": "links", "from": ["A"], "to": ["A"], "description": "x"}])
    with pytest.raises(ValidationError, match="UPPER_SNAKE_CASE"):
        Ontology.model_validate(bad)
