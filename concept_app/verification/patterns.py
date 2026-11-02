"""Finite relation templates. Gaps are clause-bounded, never keyword scoring."""

import re
from dataclasses import dataclass

from .normalize import unsupported_context

# No arbitrary cross-sentence wildcard. Identifier periods are handled explicitly.
# Do not bind a verb across a contrast or an explicitly different machine/actor.
# This prevents attributing "the browser makes the API call" to an earlier backend.
G = r"(?:(?!\b(?:but|however|whereas)\b|\b(?:backend|server|browser|frontend|client|website|page)\s+(?:(?:securely|directly)\s+)?(?:makes?|calls?|stores?|keeps?|contacts?|should|must|can|will)\b)(?:\.(?=[a-z_])|[^.;!?\n])){0,90}?"
S = r"(?:backend|back end|server)"
B = r"(?:browser|frontend|front end|client(?:-side)?)"
D = r"(?:database|durable storage|persistent storage)"
A = r"(?:attempts?|responses?|events?)"
K = r"(?:private (?:api )?key|api key|key|secret|credentials?|token)"
SAVE = r"(?:save(?:s|d)?|store(?:s|d)?|persist(?:s|ed)?|keep(?:s)?|kept|retain(?:s|ed)?)"
ACT = lambda expression: r"\b(?P<action>" + expression + r")\b"


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

# Recognized contradictions are independently matched, including appended bad advice.
define("bad_key_browser",
       rf"{ACT(SAVE)}{G}{K}{G}(?:in|on|to){G}(?:browser|frontend|front end|client-side code)",
       rf"{ACT(r'put')}{G}{K}{G}(?:in|on){G}(?:browser|frontend|front end|client-side code)",
       rf"{ACT(r'(?:send|ship|deliver|expose)')}{G}(?:private |api )?key{G}(?:visitors?|browser)",
       rf"{ACT(r'(?:hide|embed)')}\s+(?:the )?{K}\s+in\s+(?:the )?{B}(?:\s+javascript|\s+code)?",
       rf"{B}\s+{ACT(r'(?:call|calls)')}\s+(?:the )?(?:third-party|third party|provider)\s+api\s+(?:using|with)\s+(?:the )?{K}",
       rf"{ACT(r'call')}\s+(?:the )?(?:third-party|third party|provider)\s+api\s+from\s+(?:the )?{B}\s+(?:using|with)\s+(?:the )?{K}")
define("bad_browser_trust",
       rf"{ACT(r'(?:trust|accept|use)')}{G}(?:browser-supplied|browser supplied|customer-modified){G}(?:price|total|discount)",
       rf"browser(?:-only)? (?:rules|code|price){G}{ACT(r'(?:is|are)')}{G}(?:authoritative|tamper-proof|trusted)")
define("bad_temp",
       rf"(?:temporary variable|in-memory state|temporary state){G}{ACT(r'(?:survive|survives|retain|retains|persist|persists)')}{G}(?:restart|refresh)",
       rf"{ACT(r'(?:keep|save|store)')}{G}(?:attempts|progress|answers){G}only{G}(?:temporary variable|memory)")
define("bad_event_cell",
       rf"{ACT(r'(?:keep|store|save|put)')}{G}(?:all |every )?(?:attempts|responses|events){G}(?:one|single) (?:comma-separated )?cell",
       rf"{ACT(r'(?:overwrite|replace)')}{G}(?:past attempts|history){G}(?:latest|newest)")
define("bad_fk_direction",
       rf"learners\.(?:id|attempt_id)\s*(?:->|references)\s*attempts\.(?:id|learner_id)",
       rf"{ACT(r'(?:store|put|keep|add)')}{G}(?:all |five |twelve )?attempt ids{G}(?:learner row|learner record)")
define("bad_orphan",
       rf"{ACT(r'(?:allow|accept|store)')}{G}(?:orphan attempts|orphan references|attempts for nonexistent learners)")
define("bad_gap",
       rf"{ACT(r'(?:discard|delete|ignore)')}{G}(?:original |the )?gap",
       rf"{ACT(r'(?:link|connect)')}{G}retry{G}unrelated gap",
       rf"retry{G}{ACT(r'(?:proves|guarantees)')}{G}(?:understanding|mastery)")
define("bad_response",
       rf"{ACT(r'(?:always return|always report)')}{G}success{G}(?:saving fails|save fails|failure)",
       rf"{ACT(r'(?:return|send|respond with)')}{G}(?:http )?(?:400|401|403|404|500)\b{G}(?:successful creation|created successfully)",
       rf"{ACT(r'(?:return|send)')}{G}(?:http )?202 accepted{G}(?:already created|creation completed)")
define("bad_729",
       rf"(?:request|requested order){G}{ACT(r'(?:keep|keeps|target|targets|identify|identifies)')}{G}(?:order )?(?:4821|1729)\b",
       rf"{ACT(r'(?:change|update)')}{G}only{G}(?:displayed label|label)",
       rf"{ACT(r'(?:change|replace|set|switch)')}{G}(?:order id|order identifier|requested order){G}(?:to|with) (?!729\b)\d+\b")
define("bad_body_required", rf"every request{G}(?:must|always){G}{ACT(r'(?:have|include|contain)')}{G}body")


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
