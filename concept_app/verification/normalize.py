"""Normalization with an offset map back to the unchanged learner answer."""

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Text:
    original: str
    value: str
    offsets: tuple[tuple[int, int], ...]

    def evidence(self, start, end):
        first, last = self.offsets[start][0], self.offsets[end - 1][1]
        return {"start": first, "end": last, "text": self.original[first:last]}


def normalize(answer):
    chars, offsets = [], []
    for index, char in enumerate(answer):
        normalized = unicodedata.normalize("NFKC", char).casefold().replace("’", "'")
        normalized = normalized.replace("‘", "'").replace("“", '"').replace("”", '"')
        for part in normalized:
            if part.isspace():
                if chars and chars[-1] == " ":
                    offsets[-1] = (offsets[-1][0], index + 1)
                    continue
                part = " "
            chars.append(part)
            offsets.append((index, index + 1))
    text = "".join(chars)
    contractions = {"can't": "cannot", "don't": "do not", "doesn't": "does not",
                    "isn't": "is not", "won't": "will not", "shouldn't": "should not",
                    "mustn't": "must not", "aren't": "are not", "couldn't": "could not"}
    for match in reversed(list(re.finditer(r"\b(?:" + "|".join(contractions) + r")\b", text))):
        start, end = match.span()
        replacement = contractions[match.group()]
        span = (offsets[start][0], offsets[end - 1][1])
        text = text[:start] + replacement + text[end:]
        offsets[start:end] = [span] * len(replacement)
    left, right = len(text) - len(text.lstrip()), len(text.rstrip())
    return Text(answer, text[left:right], tuple(offsets[left:right]))


def unsupported_context(text, match, allow_negation=False):
    """Conservative, finite scope rules; no general natural-language inference."""
    start = match.start()
    # Quoted propositions are not assertions. Quoted field names remain usable.
    for quoted in re.finditer(r'"([^"\n]+)"', text):
        if quoted.start() <= start < quoted.end() and len(quoted.group(1).split()) > 2:
            return True
    clause_start = max(text.rfind(mark, 0, start) for mark in (";", "!", "?", "\n")) + 1
    prefix = text[clause_start:start][-100:]
    if re.search(r"(?:it is wrong (?:that|to)|incorrect (?:claim|idea)\s*:|wrong idea\s*:)\s*[^;.!?]{0,60}$", prefix):
        return True
    # A question or hypothetical does not assert a solution.
    if re.search(r"\b(?:what if|suppose|imagine|would it work if)\b[^;.!?]{0,60}$", prefix):
        return True
    if allow_negation:
        return False
    action = match.start("action") if "action" in match.re.groupindex else match.start()
    before = text[max(clause_start, action - 48):action]
    before = re.sub(r"\bnot only\b", "", before)
    return bool(re.search(r"\b(?:not|never|cannot|no need to|rather than|instead of)\s+(?:[\w'-]+\s+){0,3}$", before))
