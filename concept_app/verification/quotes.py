"""Python confirmation of model-proposed quotes.

The model may only point at text: for an idea the phrase rules missed, it proposes
the exact passage of the learner's answer that states the idea. Python then decides.
A quote counts only if it is copied exactly from the answer and contains every
anchor group for that idea, each in an asserted (not negated, quoted or hypothetical)
form. Contradictions are still found by the deterministic rules on the full answer,
so a quote can never override recognised bad advice.
"""

import re

from .normalize import normalize, unsupported_context

MAX_QUOTE = 400
S = r"(?:backend|back end|server|server-side|api route)"
B = r"(?:browser|frontend|front end|client|website|web page|page|javascript)"
K = r"(?:key|secret|credential|token)"
D = r"(?:database|db|durable storage|persistent storage|supabase|postgres|table)"
NEGATION = r"(?:not|never|no|don't|do not|shouldn't|should not|cannot|can't|instead of|rather than|avoid)"

# Each idea lists anchor groups; a confirmed quote must contain one match from every group.
ANCHORS = {
    "browser_exposure": [B + r"|dev ?tools|developer tools|page source|code",
                         r"inspect\w*|see|sees|seen|view\w*|read\w*|edit\w*|chang\w+|modif\w+|alter\w*|copy|copied|visible|tamper\w*|mess\w*|open\w*"],
    "key_extraction": [K, r"cop(?:y|ied|ies)|steal\w*|stolen|extract\w*|take|taken|grab\w*|see|seen|visible|read|find|found|reuse\w*|abuse\w*"],
    "server_rules": [S, r"rules?|discounts?|prices?|logic"],
    "rule_benefit": [r"consistent\w*|same|everyone|every customer|centrali[sz]\w*|one place|updat\w+|trust\w*|authorit\w*|tamper\w*"],
    "request_order": [r"order|id|identifier|4821", r"request|url|path|parameter|query|endpoint|send|include\w*"],
    "request_operation": [r"get|fetch\w*|retriev\w*|which order|operation|endpoint|/orders?"],
    "browser_backend": [B, S],
    "server_key": [K, S + r"|environment|env|secrets? manager|vault"],
    "server_call": [S, r"api|provider|third-party|third party|service", r"call\w*|request\w*|send\w*|make\w*|makes|contact\w*|forward\w*"],
    "temporary_loss": [r"memory|variables?|temporary|state|ram",
                       r"lost|los\w+|vanish\w*|disappear\w*|wip\w+|clear\w*|reset\w*|eras\w+|gone|refresh\w*|reload\w*|restart\w*"],
    "save_durable": [r"sav\w+|stor\w+|persist\w*|writ\w+|wrote|put|keep\w*|kept|insert\w*", D],
    "retrieve_saved": [r"load\w*|fetch\w*|read\w*|retriev\w+|restor\w+|get|gets|query\w*|pull\w*|select\w*|show\w*"],
    "separate_entities": [r"learners?", r"attempts?", r"tables?"],
    "each_attempt_row": [r"attempts?|responses?|events?", r"rows?|records?"],
    "attempt_learner": [r"attempts?|rows?|records?", r"learner_id|learner id|foreign key|fk|referenc\w+|point\w*"],
    "combined_problem": [r"cell|combin\w+|comma\w*|string|single field|one field|one column",
                         r"filter\w*|count\w*|quer\w+|updat\w+|hard|difficult|cannot|can't|impossible|slow|messy|pars\w+"],
    "independent_query": [r"filter\w*|count\w*|quer\w+|analy[sz]\w*|group\w*|sort\w*|where"],
    "fixed_code": [r"concepts?|list", r"code|hard-?coded|constant|source|file"],
    "secret_location": [r"secrets?|keys?|credentials?|tokens?", S + r"|environment|env|secrets? manager|vault"],
    "attempt_location": [r"attempts?", D],
    "loading_location": [r"loading", r"state|ui|frontend|memory|temporary|component|client"],
    "response_status": [r"status|201|200|204|4\d\d|5\d\d"],
    "client_errors": [r"client|frontend|app|browser|caller", r"errors?|fail\w*|status"],
    "foreign_key": [r"foreign key|fk|referenc\w+", r"learners?(?:\.id)?"],
    "reject_orphan": [r"reject\w*|prevent\w*|block\w*|fail\w*|refus\w+|error|stop\w*|disallow\w*",
                      r"exist\w*|missing|nonexistent|99|invalid|unknown"],
    "retry_gap": [r"retry|attempt", r"gaps?|gap_id"],
    "trace_gap": [r"trac\w+|see|track\w*|link\w*|connect\w*|know|which|show\w*", r"difficult\w*|gaps?|problem|struggle"],
    "trusted_price": [S, r"prices?|totals?", r"calculat\w+|comput\w+|validat\w+|check\w*|look\w* up|decid\w+|recalculat\w+|recomput\w+|set\w*"],
    "not_browser_price": [NEGATION, r"trust\w*|accept\w*|use|using|rely\w*", B],
    "order_729": [r"729"],
    "reject_temporary": [r"no|not|never|instead|insufficient|lost|wip\w+|isn't enough|not enough|disappear\w*",
                         r"variables?|memory|temporary"],
    "survive_restart": [r"restart\w*|surviv\w+|reboot\w*|crash\w*"],
    "creation_success": [r"201|created|success\w*|200"],
    "gap_record": [r"gaps?|difficult\w*", r"records?|rows?|tables?|stor\w+|sav\w+"],
    "followup_gap": [r"follow-?up", r"gaps?|gap_id"],
}
# Ideas whose meaning is itself a rejection: negation inside the quote is expected.
NEGATIVE_IDEAS = {"not_browser_price", "reject_temporary", "combined_problem", "reject_orphan"}
# A real clause has grammar. Keyword lists ("order, request, get") have none of these.
FUNCTION_WORDS = re.compile(r"(?<!\w)(?:the|a|an|to|in|on|of|for|from|by|with|so|it|its|that|this|is|are|was|"
                            r"were|be|can|could|should|must|will|would|has|have|does|do|their|its|our|then|when|if)(?!\w)")
CLAUSE_BREAK = re.compile(r"[;!?\n,:]|\.(?=\s|$)")
COMPILED = {fact: [re.compile(r"(?<!\w)(?:" + group + r")(?!\w)", re.I) for group in groups]
            for fact, groups in ANCHORS.items()}


def confirm_quote(answer, fact, quote):
    """Return evidence for the quote, or None if Python does not accept it."""
    if fact not in COMPILED or not isinstance(quote, str):
        return None
    quote = quote.strip()
    if not quote or len(quote) > MAX_QUOTE:
        return None
    start = answer.find(quote)
    if start < 0:
        return None
    text = normalize(quote).value
    allow_negation = fact in NEGATIVE_IDEAS
    # Every anchor must be asserted inside one clause that reads as a sentence.
    position = 0
    for clause in CLAUSE_BREAK.split(text) + [""]:
        if clause.strip():
            offset = text.find(clause, position)
            position = offset + len(clause)
            if (len(clause.split()) >= 3 and FUNCTION_WORDS.search(clause)
                    and all(any(not unsupported_context(text, _shift(match, offset), allow_negation)
                                for match in anchor.finditer(clause))
                            for anchor in COMPILED[fact])):
                return {"start": start, "end": start + len(quote), "text": quote,
                        "pattern_id": "quote." + fact}
    return None


class _shift:
    """A match whose position is relative to the whole quote, for unsupported_context."""

    def __init__(self, match, offset):
        self._match, self._offset, self.re = match, offset, match.re

    def start(self, *group):
        return self._match.start() + self._offset
