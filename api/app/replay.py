"""Replay mode: answers saved from a finished evaluation run, no model and no key.

The file `replay_answers.json` is built by `export-replay` in the pipeline from real answers,
real passages and the real graph. A question that is not in the file gets a plain refusal that
lists the saved questions, so nothing is ever made up.
"""

import json
from pathlib import Path
from uuid import uuid4

from app.schemas import Answer, AskResponse

DEFAULT_FILE = Path(__file__).with_name("replay_answers.json")


def _key(question: str) -> str:
    return " ".join(question.lower().split())


class ReplayService:
    def __init__(self, path: Path = DEFAULT_FILE) -> None:
        entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
        self._entries = {_key(e["question"]): e for e in entries}
        self._questions = [e["question"] for e in entries]

    def examples(self) -> list[str]:
        return list(self._questions)

    def ask(self, question: str, compare: bool) -> AskResponse:
        entry = self._entries.get(_key(question))
        if entry is None:
            message = (
                "Replay mode only knows the saved example questions. "
                "Pick one of the examples to see a full answer."
            )
            answer = Answer(mode="local", status="refused", message=message, model="none")
            return AskResponse(answer_id=uuid4().hex, answer=answer, fixture=True)
        baseline = None
        if compare and entry.get("baseline"):
            baseline = Answer(**entry["baseline"])
        return AskResponse(
            answer_id=uuid4().hex,
            answer=Answer(**entry["answer"]),
            baseline=baseline,
            fixture=True,
        )
