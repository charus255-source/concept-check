"""Finite relation templates. Gaps are clause-bounded, never keyword scoring."""

import re
from dataclasses import dataclass

from .normalize import unsupported_context

# No arbitrary cross-sentence wildcard. Identifier periods are handled explicitly.
# Do not bind a verb across a contrast or an explicitly different machine/actor.
# This prevents attributing "the browser makes the API call" to an earlier backend.
G = r"(?:(?!\b(?:but|however|whereas)\b|\b(?:backend|server|browser|frontend|client|website|page)\s+(?:(?:securely|directly)\s+)?(?:makes?|calls?|stores?|keeps?|contacts?|should|must|can|will)\b)(?:\.(?=[a-z_])|[^.;!?\n])){0,90}?"
# For bad advice: the gap may not cross a negation, so "the key on the server, not in
# the browser" is not read as "the key in the browser".
GN = G.replace(r"(?!\b(?:but|however|whereas)\b", r"(?!\b(?:but|however|whereas|not|never|instead|rather|nor|unlike)\b", 1)
assert GN != G
S = r"(?:backend|back end|server)"
B = r"(?:browser|frontend|front end|client(?:-side)?)"
D = r"(?:database|db|durable storage|persistent storage|supabase|postgres(?:ql)?)"
A = r"(?:attempts?|responses?|events?)"
K = r"(?:private (?:api )?key|api key|key|secret|credentials?|token)"
SAVE = r"(?:save(?:s|d)?|store(?:s|d)?|persist(?:s|ed)?|keep(?:s)?|kept|retain(?:s|ed)?|put(?:s)?|write(?:s)?|wrote|written)"
ACT = lambda expression: r"\b(?P<action>" + expression + r")\b"
LOSE = r"(?:lost|lose(?:s)?|vanish(?:es|ed)?|disappear(?:s|ed)?|wipe(?:s|d)?|clear(?:s|ed)?|reset(?:s)?|erase(?:s|d)?|gone)"
RESTART = r"(?:refresh(?:es|ed)?|reload(?:s|ed)?|restart(?:s|ed)?)"
TEMP = r"(?:(?:a |an |the )?(?:local |global |temporary |javascript |js |python )?variables?|(?:in-)?memory|ram|temporary state)"


@dataclass(frozen=True)
class Pattern:
    id: str
    regex: re.Pattern
    allow_negation: bool = False


PATTERNS = {}


def define(name, *patterns, negative=False):
    PATTERNS[name] = tuple(Pattern(name + f".{index + 1}", re.compile(r"\b" + pattern + r"(?!\w)", re.I), negative)
                           for index, pattern in enumerate(patterns))


define("browser_exposure",
       rf"(?:visitors?|users?|anyone){G}{ACT(r'(?:inspect|read|view|extract|copy|take|alter|change)')}{G}(?:code|javascript|key|token|rules)",
       rf"(?:browser(?:-delivered)? code|browser javascript|frontend code|shipped (?:code|javascript)){G}(?:can be|is){G}{ACT(r'(?:inspected|read|changed|altered)')}(?:{G}(?:users?|visitors?))?")
define("key_extraction",
       rf"(?:visitors?|users?|anyone){G}{ACT(r'(?:extract|copy|take|steal)')}{G}{K}",
       rf"{K}{G}(?:can be|is){G}{ACT(r'(?:extracted|copied|stolen)')}")
define("server_rules",
       rf"{S}{G}{ACT(r'(?:centralize|apply|enforce|handle|manage|calculate|validate|recalculate)(?:s|d)?')}{G}(?:business rules|discount(?:s| rules)?|rules|price)",
       rf"{ACT(r'(?:apply|enforce|centralize)')}{G}(?:discount rules|business rules|rules){G}(?:on|in){G}{S}")
define("rule_benefit",
       rf"{ACT(r'centraliz(?:e|es|ed)')}{G}(?:business )?rules",
       rf"{ACT(r'(?:apply|applies|applied|enforce|enforces)')}{G}(?:consistently|centrally)",
       rf"{ACT(r'(?:allow|allows|update|updates|change|changes)')}{G}(?:updates|rules){G}(?:without|independent)",
       rf"(?:browser code|browser rules|it){G}{ACT(r'cannot be')}{G}(?:authority|trusted)")
define("request_order",
       rf"request{G}{ACT(r'(?:identify|identifies|provide|provides|carry|carries|include|includes|contain|contains|send|sends|specify|specifies)')}{G}(?:order (?:identifier|id)|4821)",
       rf"{ACT(r'(?:send|put|include|provide)')}{G}(?:4821|order (?:id|identifier)){G}(?:request|url|path|parameter)")
define("request_operation",
       rf"request{G}{ACT(r'(?:identify|identifies|specify|specifies)')}{G}(?:intended operation|retriev|fetch|get the order)",
       rf"(?:identifier|order id|4821){G}{ACT(r'(?:tell|tells|identify|identifies|select|selects)')}{G}(?:server|order)",
       rf"{ACT(r'(?:retrieve|fetch|get)')}{G}order{G}(?:request|id|4821)",
       rf"request{G}{ACT(r'(?:retrieve|fetch|get)')}{G}order")
define("browser_backend",
       rf"{B}{G}{ACT(r'(?:call|calls|send|sends|route|routes)')}{G}{S}",
       rf"(?:website|page|frontend){G}{ACT(r'(?:send|sends|route|routes)')}{G}request{G}{S}",
       rf"(?:website|page){G}{ACT(r'(?:call|calls)')}{G}{S}",
       rf"{ACT(r'(?:route|send|proxy)')}{G}(?:request|call){G}(?:through|via|to){G}{S}",
       rf"{B}\s+(?:(?:should|must|can)\s+)?{ACT(r'(?:talk|talks|communicate|communicates)')}\s+(?:to|with)\s+(?:the |our |its )?{S}",
       rf"requests?\s+from\s+(?:the )?{B}\s+(?:(?:should|must)\s+)?{ACT(r'(?:go|goes|pass|passes)')}\s+(?:through|via|to)\s+(?:the |our )?{S}")
define("server_key",
       rf"{S}{G}{ACT(SAVE)}{G}{K}",
       rf"{ACT(SAVE)}{G}{K}{G}(?:on|in|at){G}{S}",
       rf"{K}{G}(?:belongs?|lives?|stays?){G}(?:server|server-side)",
       rf"{ACT(SAVE)}\s+(?:the |our )?{K}\s+(?:(?:only|exclusively)\s+)?server-side",
       rf"{K}\s+(?:(?:must|should)\s+)?{ACT(r'(?:remain|remains|stay|stays)')}\s+(?:(?:only|exclusively)\s+)?(?:server-side|on\s+(?:the |our )?{S})")
define("server_call",
       rf"{S}{G}{ACT(r'(?:make|makes|call|calls|contact|contacts|perform|performs)')}{G}(?:authorized|third-party|third party|provider|api)",
       rf"{S}\s+(?:(?:should|must|can|will)\s+)?{ACT(r'(?:send|sends|forward|forwards|relay|relays|proxy|proxies)')}\s+(?:the |an? )?(?:request|call)\s+to\s+(?:the )?(?:third-party api|third party api|provider(?: api)?)",
       rf"(?:third-party api|third party api|provider api)\s+(?:is\s+|(?:must|should)\s+be\s+){ACT(r'(?:called|contacted)')}\s+by\s+(?:the |our )?{S}")
define("temporary_loss",
       rf"(?:temporary|in-memory|memory){G}(?:state|progress|data|variable)?{G}{ACT(r'(?:lost|disappear|disappears|vanish|vanishes|cleared)')}{G}(?:refresh|reload|restart)",
       rf"(?:refresh|reload|restart){G}{ACT(r'(?:lose|loses|clear|clears|discard|discards)')}{G}(?:temporary|memory|progress|state)")
define("save_durable",
       rf"{ACT(SAVE)}{G}(?:progress|attempts?|answer|responses?|data){G}{D}",
       rf"(?:progress|attempts?|answer|responses?|data){G}(?:should|must|can|needs? to)?{G}(?:be )?{ACT(r'(?:saved|stored|persisted|retained)')}{G}{D}")
define("retrieve_saved",
       rf"{ACT(r'(?:retrieve|retrieved|load|loaded|read|restore)(?:s)?')}{G}(?:saved |previous )?(?:progress|attempts?|responses?|data|them|it)",
       rf"(?:progress|attempts?|data){G}(?:saved|stored){G}and {ACT(r'(?:retrieved|loaded|restored)')}{G}(?:needed|return)")
define("separate_entities",
       rf"{ACT(SAVE)}{G}learners{G}(?:one|their own|separate) table{G}attempts{G}(?:another|separate|their own)",
       rf"learners and attempts{G}{ACT(r'(?:have|use|belong in|live in)')}{G}separate (?:tables|collections)")
define("each_attempt_row",
       rf"{ACT(SAVE)}{G}(?:each|every) {A}{G}(?:separate|own|individual) (?:row|record)",
       rf"(?:each|every) {A}{G}{ACT(r'(?:has|gets|needs|is|should have|should be)')}{G}(?:own|separate|individual) (?:row|record)",
       rf"{ACT(r'(?:use|create|make)')}{G}(?:one|a separate) (?:row|record) (?:per|for each) attempt")
define("attempt_learner",
       rf"(?:each|every) attempt{G}{ACT(r'(?:contain|contains|has|have|carries|stores|include|includes|reference|references|point|points)')}{G}(?:a )?(?:learner_id|learner id|learner reference|its learner)",
       rf"{ACT(r'(?:put|store|add)')}{G}(?:learner_id|learner id|learner reference){G}(?:each|every) attempt",
       rf"(?:each|every) attempt{G}(?:separate|own) row {ACT(r'with')}{G}(?:learner_id|learner id|learner reference)",
       rf"attempts\.learner_id\s*(?:->|references|points to)\s*learners\.id")
define("combined_problem",
       rf"(?:combining|combined|comma-separated|one (?:long )?cell|single cell){G}{ACT(r'(?:makes?|is|are|prevents?|cannot)')}{G}(?:difficult|hard|filter|count|update|relate|analy)",
       rf"{ACT(r'(?:cannot|cannot easily|hard to|difficult to)')}{G}(?:filter|count|update|relate){G}(?:individual|separate|attempts|events)", negative=True)
define("independent_query",
       rf"(?:each|every) attempt{G}(?:row|record){G}(?:so|because|allow|enable){G}{ACT(r'(?:filter|filtered|count|counted|analy[sz]e|analy[sz]ed)')}",
       rf"(?:separate|individual|own) (?:rows?|records?){G}{ACT(r'(?:allow|enable|make|let)(?:s)?')}{G}(?:filter(?:ing|ed)?|count(?:ing|ed)?|analy[sz](?:e|ed|ing))",
       rf"{ACT(r'(?:filter|count|analy[sz]e)(?:ed|ing)?')}{G}(?:independently|individually|separately)")
define("fixed_code",
       rf"(?:fixed (?:concept |supported-concept )?list|concept list|supported concepts){G}(?:can |should )?{ACT(r'(?:live|lives|belong|belongs|stay|stays|go|goes)')}{G}code",
       rf"{ACT(r'(?:ship|keep|put|store)')}{G}(?:fixed list|concept list|supported concepts){G}code")
define("secret_location",
       rf"(?:secrets?|credentials?|private (?:api )?keys?){G}{ACT(r'(?:belong|belongs|live|lives|go|goes|stay|stays)')}{G}(?:server-side environment|server environment|secrets manager)",
       rf"{ACT(r'(?:keep|put|store)')}{G}(?:secrets?|credentials?|private (?:api )?keys?){G}(?:server-side environment|server environment|secrets manager)")
define("attempt_location",
       rf"(?:learner attempts|attempts){G}{ACT(r'(?:belong|belongs|live|lives|go|goes|stay|stays)')}{G}(?:durable )?(?:database|persistent storage)",
       rf"{ACT(SAVE)}{G}attempts{G}{D}")
define("loading_location",
       rf"(?:loading (?:message|text|status)|loading){G}{ACT(r'(?:belong|belongs|live|lives|go|goes|stay|stays)')}{G}(?:temporary ui state|ui state|temporary frontend state)",
       rf"{ACT(r'(?:hold|keep|put|store)')}{G}loading{G}(?:temporary ui state|ui state)")
define("response_status",
       rf"(?:api|server){G}{ACT(r'(?:return|returns|send|sends)')}{G}(?:appropriate |success |http )*(?:http )?status(?: code)?",
       rf"{ACT(r'(?:return|send|respond with)')}{G}(?:an? )?(?:appropriate |success |http )+(?:status|201|200|204)")
define("client_errors",
       rf"client{G}{ACT(r'(?:handle|handles|check|checks|process|processes)')}{G}(?:error|failure)",
       rf"{ACT(r'(?:handle|check|process)')}{G}(?:error|failure) responses")
define("foreign_key",
       rf"foreign key(?: constraint)? (?:from attempts\.learner_id |on attempts\.learner_id )?(?:to |referencing |references )?learners\.id",
       rf"foreign key{G}attempts\.learner_id{G}learners\.id",
       rf"attempts\.learner_id\s*(?:->|references)\s*learners\.id{G}foreign key")
define("reject_orphan",
       rf"(?:foreign key|constraint|database){G}{ACT(r'(?:prevent|prevents|reject|rejects|block|blocks)')}{G}(?:attempt|reference|insert){G}(?:nonexistent|missing|does not exist|not exist)",
       rf"(?:foreign key|constraint|database){G}{ACT(r'(?:prevent|prevents|reject|rejects|block|blocks)')}{G}(?:nonexistent|missing) learner")
define("retry_gap",
       rf"(?:retry|subsequent|new) attempt{G}{ACT(r'(?:reference|references|point|points|link|links)')}{G}(?:gap|difficulty)",
       rf"{ACT(r'(?:link|connect)')}{G}(?:retry|retry attempt){G}(?:same |original |that )?gap",
       rf"{ACT(r'(?:save|store|put)')}{G}gap(?:_id| id){G}(?:retry|attempt)")
define("trace_gap",
       rf"(?:this|link|links|relationship){G}{ACT(r'(?:link|links|connect|connects|trace|traces|preserve|preserves)')}{G}(?:original difficulty|difficulty|follow-up){G}(?:retry|subsequent|result)",
       rf"{ACT(r'(?:preserve|preserving|trace|tracing)')}{G}relationship{G}original difficulty{G}retry",
       rf"{ACT(r'(?:tell|see|track|trace|check|evaluate)')}{G}(?:which difficulty|gap|difficulty){G}(?:retry|address|fix)")
define("trusted_price",
       rf"{S}{G}{ACT(r'(?:calculate|calculates|validate|validates|recalculate|recalculates)')}{G}(?:price|total){G}(?:trusted|authoritative|business rules)",
       rf"{S}{G}{ACT(r'(?:calculate|calculates|validate|validates|recalculate|recalculates)')}{G}authoritative price")
define("not_browser_price",
       rf"(?:rather than|instead of|not|never){G}(?:trust|trusting|use|using|accept|accepting){G}(?:value|price|total){G}{B}",
       rf"{B}(?:-supplied)? (?:price|total){G}(?:is not|must not be|cannot be){G}(?:trusted|authoritative)", negative=True)
define("order_729",
       rf"request{G}{ACT(r'(?:identify|identifies|request|requests|target|targets|fetch|fetches)')}{G}order 729\b",
       rf"{ACT(r'(?:change|replace|set|switch)')}{G}(?:order id|order identifier|requested order){G}(?:to|with) 729\b",
       rf"{ACT(r'(?:request|retrieve|fetch|get)')}{G}order 729\b{G}(?:url|path|parameter|request)")
define("reject_temporary",
       r"\Ano(?=[,.!\s])",
       rf"(?:not|never|cannot|instead of){G}(?:rely|relying|use|using){G}(?:temporary variable|memory|temporary state)",
       rf"(?:temporary variable|memory|temporary state){G}(?:not enough|not sufficient|insufficient|cannot)", negative=True)
define("survive_restart",
       rf"(?:answer|it|data){G}{ACT(r'(?:survive|survives|persist|persists|last|lasts)')}{G}restart",
       rf"{ACT(SAVE)}{G}(?:answer|it|data){G}{D}{G}(?:restart)")
define("creation_success",
       rf"{ACT(r'(?:return|send|respond with)')}{G}(?:http )?201(?: created)?\b",
       rf"{ACT(r'(?:return|send|respond with)')}{G}(?:success status|successful status|success http status|http success status){G}(?:code|creat|attempt)",
       rf"{ACT(r'(?:return|send|respond with)')}{G}(?:200 ok|204 no content){G}(?:create|created|creation|saved)")
define("gap_record",
       rf"{ACT(SAVE)}{G}(?:gap|difficulty){G}(?:record|row)",
       rf"{ACT(r'(?:create|make)')}{G}(?:gap record|gap row)")
define("followup_gap",
       rf"{ACT(r'(?:link|connect)')}{G}follow-up{G}(?:retry attempt|retry){G}(?:same |that |original )?gap",
       rf"follow-up{G}{ACT(r'(?:references|points to|links to)')}{G}(?:same |that |original )?gap")

# Version 1.1.0: phrase families found by the trainer's review and learner testing.
# Each addition is covered by a regression answer in tests/test_phrase_families.py.
def extend(name, *patterns, negative=False):
    start = len(PATTERNS[name])
    PATTERNS[name] += tuple(Pattern(name + f".{start + index + 1}", re.compile(r"(?<!\w)" + pattern + r"(?!\w)", re.I), negative)
                            for index, pattern in enumerate(patterns))


DEVTOOLS = r"(?:dev ?tools|developer tools|devtools|page source|view source|inspect element|source code)"
extend("browser_exposure",
       rf"(?:visitors?|users?|anyone|customers?|people|attackers?){G}{ACT(r'(?:open|opens|see|sees|edit|edits|modify|modifies|tamper with|view|views|inspect|read|change|alter)')}{G}(?:them|it|{DEVTOOLS}|the rules|discounts?|prices?)",
       rf"{ACT(r'(?:open|opens|opening|use|uses|using|view|views|viewing)')}\s+(?:the\s+)?(?:browser'?s?\s+)?{DEVTOOLS}")
extend("key_extraction",
       rf"(?:visitors?|users?|anyone|customers?|people|attackers?){G}{ACT(r'(?:see|sees|find|finds|read|reads|grab|grabs|get|gets|view|views|steal|steals)')}{G}{K}",
       rf"{K}{G}{ACT(r'(?:steal|steals|stolen|abuse|abused|misuse|misused|reuse|reused)')}")
extend("server_rules",
       rf"{ACT(r'(?:put|keep|move|store|run|place|have)')}{G}(?:discount |business )?rules{G}(?:on|in|to|at){G}{S}")
extend("rule_benefit",
       rf"{ACT(r'(?:applied|apply|applies)')}{G}(?:the same way|same for everyone|for everyone|everywhere|consistent(?:ly)?)",
       rf"{ACT(r'(?:update|updated|change|changed)')}{G}(?:in one place|once|centrally)",
       rf"(?:browser|frontend|client){G}{ACT(r'cannot be')}{G}(?:authority|trusted)")
extend("request_order",
       rf"request{G}{ACT(r'(?:needs?|must have|should have|has)')}{G}(?:the )?(?:order (?:identifier|id|number)|4821)",
       rf"{ACT(r'(?:get|fetch)')}\s+/orders?/4821")
extend("request_operation",
       rf"(?:server|backend|api){G}{ACT(r'(?:knows?|can tell|can find|finds?|looks? up)')}{G}(?:which|what|the) order",
       rf"{ACT(r'(?:get|fetch)')}\s+/orders?/\d+")
extend("server_key",
       rf"{ACT(r'(?:move|moves|moved)')}{G}{K}{G}(?:to|on|in|into){G}{S}",
       rf"{ACT(SAVE)}{G}{K}{G}(?:in|into|as) (?:an |the |a )?(?:environment variables?|env vars?|\.env|secrets? manager)")
extend("temporary_loss",
       rf"{TEMP}{G}{ACT(LOSE)}",
       rf"{ACT(LOSE)}{G}(?:because|since|as){G}(?:only )?{G}(?:in|was) {TEMP}",
       rf"{RESTART}{G}{ACT(LOSE)}",
       rf"{TEMP}{G}{ACT(LOSE)}{G}{RESTART}")
extend("save_durable",
       rf"{ACT(SAVE)}\s+(?:it|them|this|everything|that)\s+(?:in|into|to|on)\s+(?:a |the |an )?{D}")
extend("retrieve_saved",
       rf"{ACT(r'(?:read|load|fetch|get|pull|query)')}\s+(?:it|them|this|the progress|the attempts)\s+back")
extend("separate_entities",
       rf"learners\s+(?:in|into)\s+(?:a |the |their own |one )?(?:learners )?table{G}attempts\s+(?:in|into)\s+(?:a |an |the |another |their own )?(?:attempts |separate )?table",
       rf"{ACT(r'(?:make|create|use|add|have)')}\s+(?:a |an )?(?:separate |own |new )?attempts table")
extend("each_attempt_row",
       rf"(?:one|a|its own|a separate) (?:row|record) (?:per|for each|for every) (?:attempt|response|event)",
       rf"(?:attempts table|table of attempts){G}(?:each|every|one) (?:row|record)")
extend("attempt_learner",
       rf"(?:attempts?|row|record)s?{G}{ACT(r'(?:with|has|have|carries|contains|gets|stores|includes)')}\s+(?:a |an |the )?(?:foreign key|fk|learner_id|learner id)(?: column| field)?{G}(?:learners?|learner_id|learner id)",
       rf"(?:learner_id|learner id)(?: column| field| foreign key)?{G}{ACT(r'(?:points?|pointing|refers?|referring|references|referencing|links?|linking)')}{G}(?:the |its |their )?learners?",
       rf"(?:each|every) attempt (?:row|record) {ACT(r'(?:has|have|carries|contains|stores|includes)')}\s+(?:a |an )?(?:learner_id|learner id)")
extend("independent_query",
       rf"(?:per attempt|each attempt|separate rows?|own rows?|individual rows?){G}(?:you |we |it |the team )?(?:can |could )?(?:easily |just )?{ACT(r'(?:filter|count|query|group|sort|analy[sz]e)')}")
extend("fixed_code",
       rf"(?:fixed (?:concept )?list|concept list|supported concepts|list of (?:supported )?concepts){G}{ACT(r'(?:hard-?coded|hard coded|kept|stored|written|be|is)')}{G}(?:code|source|constant|python|javascript|file)")
extend("secret_location",
       rf"(?:secrets?|credentials?|(?:private |api )?keys?|tokens?){G}{ACT(r'(?:belong|belongs|live|lives|go|goes|stay|stays|kept|stored)')}{G}(?:environment variables?|env vars?|\.env|server-side environment|server environment|secrets manager)")
extend("loading_location",
       rf"(?:loading (?:message|text|status|spinner)|loading){G}{ACT(r'(?:is|are|lives in|belongs in|stays in|goes in)')}{G}(?:temporary |frontend |browser |component |local |react )?(?:ui )?state")
extend("response_status",
       rf"{ACT(r'(?:return|returns|send|sends|respond with|responds with)')}\s+(?:an? |the )?(?:appropriate |proper |correct |http )*status(?: codes?)?")
extend("trusted_price",
       rf"{S}{G}{ACT(r'(?:calculate|calculates|validate|validates|recalculate|recalculates|recompute|recomputes|compute|computes|look up|looks up|decide|decides)')}{G}(?:the |final |real )?(?:price|total)")
extend("not_browser_price",
       rf"(?:not|never|cannot|do not)\s+(?:[\w'-]+\s+){{0,2}}(?:trust|accept|use)\w*{G}{B}(?:-supplied| supplied|'s)?\s+(?:price|total|value)",
       negative=True)
extend("followup_gap",
       rf"{ACT(r'(?:link|connect)')}{G}(?:retry|retry attempt){G}follow-up{G}(?:same |that |original )?gap")
extend("order_729",
       rf"/orders?/729\b",
       rf"4821{G}to 729\b")
extend("survive_restart",
       rf"{TEMP}{G}{ACT(LOSE)}{G}(?:when|on|after|if){G}{RESTART}")
extend("gap_record",
       rf"{ACT(r'(?:create|make|add|use|have)')}\s+(?:a |an )?(?:gaps?|difficult(?:y|ies)) (?:table|record|row)")
extend("retry_gap",
       rf"(?:retry|retry attempt|attempt){G}{ACT(r'(?:store|stores|has|have|carries|includes|references|keeps?)')}{G}(?:the |a )?gap(?:_id| id)")
extend("followup_gap",
       rf"follow-up{G}{ACT(r'(?:store|stores|has|have|carries|includes|references)')}{G}(?:the |a )?gap(?:_id| id)?")


# Version 1.2.0: phrase families from real learner answers (evaluation/real_answers.csv).
ORDER = r"(?:order|oder|ordr|odrer)"
extend("browser_exposure",
       rf"{B}{G}(?:can|could|will|would) be {ACT(r'(?:manipulated|changed|edited|modified|tampered with|altered|faked|fudged)')}",
       rf"(?:users?|customers?|visitors?|anyone){G}{ACT(r'(?:manipulate|manipulates|fudge|fudges|tamper|tampers)')}{G}(?:{B}|data|rules|price|discount|code)")
extend("server_rules",
       rf"(?:rules|logic|calculation|pricing){G}(?:should|must|need to|needs to|has to|have to)\s+(?:be|live|stay|run|happen)\s+(?:in|on|at)\s+(?:the\s+)?{S}",
       rf"(?:critical|business|pricing|discount)\s+(?:logic|rules)\s+(?:must|should)\s+{ACT(r'(?:happen|run|live|be)')}\s+(?:in|on)\s+(?:the\s+)?{S}")
extend("rule_benefit",
       rf"(?:determined|decided|controlled|set)\s+by\s+(?:the\s+)?(?:company|business|server|backend)",
       rf"{ACT(r'(?:keep|keeps|keeping)')}{G}away\s+from\s+(?:the\s+)?(?:users?|client|browser)")
extend("trusted_price",
       rf"(?:critical|business|pricing|price)\s+(?:logic|rules|calculation)\s+(?:must|should)\s+{ACT(r'(?:happen|run|live|be)')}\s+(?:in|on)\s+(?:the\s+)?{S}")
extend("not_browser_price",
       rf"(?:never|not|do not|don't)\s+{ACT(r'trust')}\s+(?:the\s+)?(?:client|browser|frontend|user input|user)", negative=True)
extend("independent_query",
       rf"(?:allow|allows|allowing|let|lets|letting|enable|enables|enabling){G}{ACT(r'(?:filter|count|query|group|sort)')}")
extend("request_order",
       rf"{ORDER}\s?(?:id|identifier|number){G}(?:path|url|query|param\w*|parameter|body|json|payload|package)",
       rf"(?:path|url|query|param\w*|parameter|body|json|payload|package){G}{ORDER}\s?(?:id|identifier|number)")


# Version 1.3.0: words the new case variants use for what gets saved.
extend("save_durable",
       rf"{ACT(SAVE)}{G}(?:messages?|history|scores?|results?){G}{D}",
       rf"(?:messages?|history|scores?|results?){G}(?:should|must|can|needs? to)?{G}(?:be )?{ACT(r'(?:saved|stored|persisted|retained|kept)')}{G}{D}")


# Recognized contradictions are independently matched, including appended bad advice.
define("bad_key_browser",
       rf"{ACT(SAVE)}{GN}{K}{GN}\b(?:in|on|to)\b{GN}(?:browser|frontend|front end|client-side code)",
       rf"{ACT(r'put')}{GN}{K}{GN}\b(?:in|on)\b{GN}(?:browser|frontend|front end|client-side code)",
       rf"{ACT(r'(?:send|ship|deliver|expose)')}{GN}(?:private |api )?key{GN}(?:visitors?|browser)",
       rf"{ACT(r'(?:hide|embed)')}\s+(?:the )?{K}\s+in\s+(?:the )?{B}(?:\s+javascript|\s+code)?",
       rf"{B}\s+{ACT(r'(?:call|calls)')}\s+(?:the )?(?:third-party|third party|provider)\s+api\s+(?:using|with)\s+(?:the )?{K}",
       rf"{ACT(r'call')}\s+(?:the )?(?:third-party|third party|provider)\s+api\s+from\s+(?:the )?{B}\s+(?:using|with)\s+(?:the )?{K}")
define("bad_browser_trust",
       rf"{ACT(r'(?:put|keep|store)')}{GN}(?:discount |business )?rules{GN}(?:only )?(?:in|on) (?:the )?(?:browser|frontend)(?: javascript| code)?",
       rf"{ACT(r'(?:trust|accept|use)')}{GN}(?:price|total|discount){GN}(?:the )?browser sends",
       rf"{ACT(r'(?:trust|accept|use)')}{GN}(?:browser-supplied|browser supplied|customer-modified){GN}(?:price|total|discount)",
       rf"browser(?:-only)? (?:rules|code|price){GN}{ACT(r'(?:is|are)')}{GN}(?:authoritative|tamper-proof|trusted)")
define("bad_temp",
       rf"(?:temporary variable|in-memory state|temporary state|global variable|variable|memory)[^,.;!?\n]{{0,40}}?{ACT(r'(?:survive|survives|retain|retains|persist|persists|stays?|lasts?)')}{GN}(?:{RESTART}|next day)",
       rf"{ACT(r'(?:keep|save|store|leave)')}{GN}(?:attempts|progress|answers|it|them){GN}(?:in )?(?:memory|a (?:global |temporary )?variable){GN}(?:so|survive|next day|there)",
       rf"(?:temporary variable|variable|memory) (?:is|would be) (?:fine|enough|ok|okay)",
       rf"{ACT(r'(?:keep|save|store)')}{GN}(?:attempts|progress|answers){GN}only{GN}(?:temporary variable|memory)")
define("bad_event_cell",
       rf"{ACT(r'keep')}\s+(?:them|it|everything|all attempts)\s+in\s+(?:one|a single) cell",
       rf"{ACT(r'(?:keep|store|save|put)')}{GN}(?:all |every )?(?:attempts|responses|events){GN}(?:one|single) (?:comma-separated )?cell",
       rf"{ACT(r'(?:overwrite|replace)')}{GN}(?:past attempts|history){GN}(?:latest|newest)")
define("bad_fk_direction",
       rf"{ACT(r'(?:store|put|keep|add)')}{GN}(?:all |five |twelve )?attempt ids{GN}(?:learner row|learner record)(?:{GN}list)?",
       rf"learners\.(?:id|attempt_id)\s*(?:->|references)\s*attempts\.(?:id|learner_id)",
       rf"{ACT(r'(?:store|put|keep|add)')}{GN}(?:all |five |twelve )?attempt ids{GN}(?:learner row|learner record)")
define("bad_orphan",
       rf"{ACT(r'(?:allow|accept|store)')}{GN}(?:orphan attempts|orphan references|attempts for nonexistent learners)")
define("bad_gap",
       rf"{ACT(r'(?:discard|delete|ignore)')}{GN}(?:original |the )?gap",
       rf"{ACT(r'(?:link|connect)')}{GN}retry{GN}unrelated gap",
       rf"retry{GN}{ACT(r'(?:proves|guarantees)')}{GN}(?:understanding|mastery)")
define("bad_response",
       rf"{ACT(r'(?:always return|always report)')}{GN}success{GN}(?:saving fails|save fails|failure)",
       rf"{ACT(r'(?:return|send|respond with)')}{GN}(?:http )?(?:400|401|403|404|500)\b{GN}(?:successful creation|created successfully)",
       rf"{ACT(r'(?:return|send)')}{GN}(?:http )?202 accepted{GN}(?:already created|creation completed)")
define("bad_729",
       rf"(?:request|requested order){GN}{ACT(r'(?:keep|keeps|target|targets|identify|identifies)')}{GN}(?:order )?(?:4821|1729)\b",
       rf"{ACT(r'(?:change|update)')}{GN}only{GN}(?:displayed label|label)",
       rf"{ACT(r'(?:change|replace|set|switch)')}{GN}(?:order id|order identifier|requested order){GN}(?:to|with) (?!729\b)\d+\b")
define("bad_body_required", rf"every request{GN}(?:must|always){GN}{ACT(r'(?:have|include|contain)')}{GN}body")


def match_facts(text):
    facts = {}
    for name, patterns in PATTERNS.items():
        matches = []
        for pattern in patterns:
            for match in pattern.regex.finditer(text.value):
                if unsupported_context(text.value, match, pattern.allow_negation):
                    continue
                evidence = text.evidence(*match.span())
                evidence["pattern_id"] = pattern.id
                if evidence not in matches:
                    matches.append(evidence)
        facts[name] = tuple(matches)
    return facts
