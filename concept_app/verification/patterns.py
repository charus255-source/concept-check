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
       rf"{ACT(SAVE)}{G}{K}{G}(?:in|on|to) (?:the |our |a |every |each )?(?:browser|frontend|front end|client-side code)",
       rf"{ACT(r'put')}{G}{K}{G}(?:in|on) (?:the |our |a |every |each )?(?:browser|frontend|front end|client-side code)",
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


# --- Rule version 1.1.0: everyday phrase families --------------------------------
# Added after a review found correct answers in a learner's own words were rejected.
# Same method as above: finite relation templates, clause-bounded, never keyword scoring.

# Tight gap for verbless placements ("attempts in the database"): stays inside one
# comma-separated clause and never crosses a negation.
T = r"(?:(?!\b(?:not|never|cannot|no|without)\b)[^,.;:!?\n]){0,45}?"
WHO = r"(?:visitors?|users?|anyone|anybody|customers?|people|someone|somebody|attackers?|everyone)"
STORE = r"(?:database|db|durable storage|persistent storage|permanent storage|disk|supabase|postgres(?:ql)?|sqlite|sql table|table|local ?storage)"
THING = r"(?:progress|attempts?|answers?|responses?|results?|data|state|rows?|it|them|everything|(?:each|every) (?:attempt|answer|response|one))"
SECRET = r"(?:secrets?|credentials?|(?:private |api |secret )*keys?|tokens?)"
ENV = r"(?:(?:server(?:-side)?|backend) (?:env(?:ironment)?(?: variables?| vars?| config(?:uration)?)?|\.env)|env(?:ironment)? (?:variables?|vars?|config(?:uration)?|file)|secrets? manager|server-side|(?:on |in )?the (?:server|backend))"
UI = r"(?:(?:temporary |local |component |react |frontend |browser |client |ui |in-memory )+state|state in the (?:browser|frontend|ui|component|page)|memory|a variable|the browser|the frontend|the ui)"
LOADING = r"(?:loading (?:message|text|status|state|spinner|indicator)|loading)"
GONE = r"(?:does not exist|not exist|nonexistent|missing|is not there|not there|not present|no such|unknown|invalid)"


def extend(name, *patterns, negative=False):
    start = len(PATTERNS[name])
    PATTERNS[name] += tuple(
        Pattern(name + f".{start + index + 1}", re.compile(r"\b" + pattern + r"(?!\w)", re.I), negative)
        for index, pattern in enumerate(patterns))


extend("browser_exposure",
       rf"{WHO}{G}{ACT(r'(?:inspect|read|view|see|find|extract|copy|take|steal|grab|alter|change|edit|modify|tamper with|look at)')}{G}(?:code|javascript|js|key|token|rules|logic|discounts?|secret|page source|source)",
       rf"{WHO}{G}{ACT(r'(?:open|opens|use|uses)')}{G}(?:dev ?tools|developer tools|inspect element|page source|view source)",
       rf"(?:code|javascript|js|rules|logic|{K}){G}(?:is|are|becomes?){G}{ACT(r'(?:visible|exposed|readable|public)')}")
extend("key_extraction",
       rf"{WHO}{G}{ACT(r'(?:steal|grab|see|read|find|get|use|reuse)')}{G}{K}",
       rf"{K}{G}(?:is|are|becomes?){G}{ACT(r'(?:visible|exposed|readable|public|leaked)')}")
extend("server_rules",
       rf"{S}{G}{ACT(r'(?:hold|holds|keep|keeps|store|stores|own|owns|decide|decides|run|runs|check|checks|compute|computes|contain|contains)')}{G}(?:business rules|discount(?:s| rules| logic)?|rules|logic|price)",
       rf"{ACT(r'(?:put|keep|move|store|run|check|hold|place)')}{G}(?:business rules|discount(?: rules| logic)?|rules|logic){G}(?:on|in|to|onto){G}{S}")
extend("rule_benefit",
       rf"(?:one|a single)\s+(?:trusted |central |shared )?(?:copy|place|source of truth|source|version)",
       rf"{ACT(r'(?:update|updated|change|changed|edit|edited|fix|fixed)')}{G}(?:in |at )?(?:one|a single) place",
       rf"{ACT(r'(?:update|updated|change|changed)')}{G}without{G}(?:browser|client|app|user|redeploy|ship)",
       rf"(?:the )?same{T}for (?:everyone|everybody|every user|all users|every customer|all customers)")
extend("rule_benefit",
       rf"cannot{G}(?:trust|rely on){G}(?:{B}|users?|customers?)", negative=True)
extend("request_order",
       rf"{ACT(r'(?:carry|carries|contain|contains|have|has|add|adds|pass|passes|need|needs|include|includes)')}{G}(?:4821|order (?:id|identifier|number)){G}(?:request|url|path|parameter|query|body)")
extend("request_operation",
       rf"{S}{G}{ACT(r'(?:know|knows|tell|tells|find|finds|see|sees)')}{G}which order",
       rf"which order{G}{ACT(r'(?:fetch|get|retrieve|return|look up|find|load)')}",
       rf"{ACT(r'(?:carry|carries|include|includes|send|sends|specify|specifies|use|uses|need|needs|have|has|state|states|say|says)')}{G}(?:http )?(?:method|verb|endpoint|operation|action|get request)")
extend("server_key",
       rf"{ACT(r'(?:move|moves|moved|put|puts|place|places|hide|hides)')}{G}{K}{G}(?:on|in|to|onto|at|behind|inside){G}{S}",
       rf"{K}{G}(?:is|are|stays?|remains?|gets?|be){G}{ACT(r'(?:kept|stored|saved|held|hidden|retained|placed|put)')}{G}(?:on|in|at|by|behind|inside){G}{S}",
       rf"{S}{G}{ACT(r'(?:add|adds|attach|attaches|hold|holds|own|owns|has|have)')}{G}{K}")
extend("server_call",
       rf"{S}{G}{ACT(r'(?:forward|forwards|send|sends|relay|relays|pass|passes|proxy|proxies)')}{G}(?:it|them|request|call){G}to{G}(?:provider|third-party|third party|api|service)")
extend("temporary_loss",
       rf"(?:only|just){T}(?:lived|lives|kept|stored|held|saved|existed|exists|was|is){T}in{T}(?:variables?|memory|ram|the browser|the page|the tab|state|javascript)",
       rf"(?:variables?|memory|ram|state|it|everything|progress){G}(?:is|are|gets?){G}{ACT(r'(?:wiped|cleared|lost|reset|gone|erased|emptied|destroyed)')}{G}(?:refresh|reload|restart|close)",
       rf"(?:refresh|reload|restart){G}{ACT(r'(?:wipe|wipes|clear|clears|reset|resets|erase|erases|lose|loses|kill|kills|destroy|destroys|empty|empties)')}{G}(?:it|everything|variables?|memory|data|progress|state)")
extend("temporary_loss",
       rf"(?:progress|it|data|answers?|nothing|they){G}(?:was|is|were|are){G}(?:not|never){G}(?:saved|stored|persisted|written)", negative=True)
extend("save_durable",
       rf"{ACT(SAVE + r'|write|writes|wrote|put|puts|insert|inserts|record|records|add|adds')}{G}{THING}{G}(?:in|to|into|on){G}{STORE}",
       rf"{THING}{G}(?:be|is|are|gets?){G}{ACT(r'(?:saved|stored|persisted|retained|written|put|recorded|inserted)')}{G}(?:in|to|into|on){G}{STORE}")
extend("retrieve_saved",
       rf"{ACT(r'(?:fetch|fetches|fetched|reload|reloads|query|queries)')}{G}(?:saved |previous )?(?:progress|attempts?|answers?|responses?|data|rows?|them|it)",
       rf"{ACT(r'(?:get|gets|pull|pulls|show|shows|display|displays)')}{G}(?:progress|attempts?|answers?|responses?|data|rows?|them|it){G}from{G}{STORE}",
       rf"{ACT(r'(?:read|reads|load|loads|get|gets)')}{G}(?:it|them){G}(?:back|again)")
extend("separate_entities",
       rf"(?:separate|own|new|second|another|different|dedicated) (?:attempts? )?table",
       rf"attempts table",
       rf"(?:two|2|separate|different) tables",
       rf"(?:one|a separate|a new|its own) (?:row|record) (?:per|for each|for every) attempt",
       rf"(?:each|every) attempt{T}(?:own|separate|new) (?:row|record)")
extend("each_attempt_row",
       rf"(?:one|a separate|a new|its own|an individual) (?:row|record|entry|line) (?:per|for each|for every) (?:attempt|response|event|try)",
       rf"(?:one|a single|each|every) (?:attempt|response|event) (?:per|on its own|in its own|in a separate) (?:row|record|line)",
       rf"{ACT(r'(?:put|give|write|insert|add|record|create|make)')}{G}(?:each|every|one) {A}{G}(?:row|record)",
       rf"{ACT(r'(?:create|creates|add|adds|insert|inserts|make|makes|store|stores|save|saves)')}{G}(?:five|5|twelve|12|multiple|many|several|separate) (?:rows|records|entries)",
       rf"(?:separate|individual|their own|its own) (?:rows|records)")
extend("attempt_learner",
       rf"(?:foreign key|fk|reference|link|pointer){T}(?:to|back to|referencing|pointing to|into){T}learners?(?: table| row| record|\.id)?",
       rf"(?:each|every|attempts?|rows?){G}{ACT(r'(?:with|has|have|having|gets?|carry|carries|stores?|includes?)')}{G}(?:learner_id|learner id)",
       rf"(?:learner_id|learner id){T}(?:column|field|foreign key|fk){G}(?:each|every|attempt|row|pointing|referenc|learner)")
extend("combined_problem",
       rf"{ACT(r'(?:parse|parsing|split|splitting|scan|scanning|unpack|unpacking|search through|searching through)')}{G}(?:string|cell|text|list|blob|field|comma)")
extend("combined_problem",
       rf"(?:cannot|hard to|difficult to|impossible to|no (?:easy |simple )?way to|painful to|messy to){G}(?:filter|count|update|relate|query|search|sort|find|pick out|separate){G}(?:cell|string|attempts?|events?|responses?|individual|one|them|anything|date|week|failed)", negative=True)
extend("independent_query",
       rf"(?:own|separate|individual|one) (?:rows?|records?){G}{ACT(r'(?:filter|count|query|group|search|sum)(?:s|ed|ing)?')}",
       rf"{ACT(r'(?:filter|count|query|group)')}{G}(?:by|on|per){G}(?:day|date|result|learner|week|status|monday)")
extend("fixed_code",
       rf"(?:concept list|fixed list|list of (?:supported )?concepts|supported concepts|concepts){T}(?:in|inside|into) (?:the |our )?(?:code|codebase|source code|a constant|repo)",
       rf"(?:concept list|fixed list|list of (?:supported )?concepts|supported concepts|concepts|list){T}(?:hard-?coded|a constant|constants)")
extend("secret_location",
       rf"{SECRET}{T}(?:in|into|inside|as|on) (?:the |a |an )?{ENV}",
       rf"{SECRET}{T}{ENV}")
extend("attempt_location",
       rf"(?:learner attempts|saved attempts|attempts?){T}(?:in|into|to|inside) (?:the |a |our )?{STORE}")
extend("loading_location",
       rf"{LOADING}{T}{UI}")
extend("response_status",
       rf"{ACT(r'(?:return|returns|send|sends|respond with|responds with|give|gives|reply with|replies with)')}{G}(?:status code|status|http code|response code|20[014])")
extend("client_errors",
       rf"(?:error|errors|failure|failed|fails|fail|4\d\d|5\d\d){G}client{G}{ACT(r'(?:handle|handles|check|checks|react|reacts|retry|retries|show|shows|know|knows|tell|tells|see|sees)')}",
       rf"client{G}{ACT(r'(?:handle|handles|check|checks|react|reacts|retry|retries|show|shows|know|knows)')}{G}(?:error|errors|failure|failed|fails|went wrong|4\d\d|5\d\d)")
extend("foreign_key",
       rf"(?:learner_id|learner id){T}(?:foreign key|fk){G}(?:to|referencing|references|on|pointing to){G}learners?",
       rf"(?:foreign key|fk)(?: constraint)?{G}(?:learner_id|learner id){G}(?:to|references|referencing|pointing to){G}learners?",
       rf"(?<!without a )(?<!no )foreign key constraint",
       rf"{ACT(r'(?:add|adds|use|uses|create|creates|define|defines|declare|declares|need|needs|set|sets)')}{T}foreign key")
extend("reject_orphan",
       rf"(?:foreign key|fk|constraint|database|db|postgres|supabase|it){G}{ACT(r'(?:prevent|prevents|reject|rejects|block|blocks|refuse|refuses|stop|stops|disallow|disallows|fail|fails|throw|throws|error|errors)')}{G}{GONE}")
extend("reject_orphan",
       rf"cannot{G}(?:add|insert|create|save|store|have){G}attempt{G}(?:unless|without|until){G}(?:learner|exists?)", negative=True)
extend("retry_gap",
       rf"(?:retry(?: attempt| row)?|second attempt|new attempt){G}{ACT(r'(?:need|needs|has|have|get|gets|store|stores|carry|carries|include|includes|keep|keeps|with)')}{G}(?:gap_id|gap id)",
       rf"(?:foreign key|fk|link|reference|connection|pointer){G}(?:from|between){G}retry{G}(?:to|and){G}gap",
       rf"(?:retry(?: attempt| row)?|second attempt){G}(?:foreign key|fk|reference|link|pointer){G}gap")
extend("trace_gap",
       rf"{ACT(r'(?:tell|see|know|track|trace|check|evaluate|measure|show|find out)')}{G}(?:whether|if|which|what){G}(?:retry|gap|difficulty|follow-up)")
extend("trace_gap",
       rf"{ACT(r'(?:trace|track|link|connect|follow)')}{G}(?:difficulty|gap){G}(?:to|through to|with){G}(?:result|retry|outcome|answer|attempt)")
extend("followup_gap",
       rf"follow-up{G}{ACT(r'(?:store|stores|has|have|get|gets|carry|carries|keep|keeps|need|needs)')}{G}(?:gap_id|gap id)",
       rf"follow-up{G}(?:foreign key|fk|reference|link|pointer){G}gap")
extend("gap_record",
       rf"{ACT(r'(?:create|creates|make|makes|add|adds|use|uses|have|need|needs)')}{G}(?:gaps? table|table (?:for|of) gaps)")
extend("trusted_price",
       rf"{S}{G}{ACT(r'(?:calculate|calculates|validate|validates|recalculate|recalculates|compute|computes|look up|looks up|check|checks|verify|verifies|decide|decides|set|sets|work out|works out)')}{G}(?:price|total|amount|cost)")
extend("not_browser_price",
       rf"(?:ignore|ignores|discard|discards|distrust|overwrite|overwrites|reject|rejects){G}(?:price|total|value|amount|whatever){G}(?:{B}|user|sends?|sent)",
       rf"(?:cannot|never|do not|must not|should not){G}trust{G}(?:{B}|user|customer)", negative=True)
extend("order_729",
       rf"(?:path|url|endpoint|route){T}{ACT(r'(?:changes? to|becomes?|is|should be|would be|ends? (?:in|with)|points? to|goes? to)')} (?:/orders?/|order |id )?(?<!\d)729\b",
       rf"{ACT(r'(?:use|call|request|hit|get|fetch|send)')}{T}/orders?/729\b",
       rf"4821{T}(?:to|with|by|becomes|->){T}(?<!\d)729\b")
extend("survive_restart",
       rf"(?:it|answer|data){G}(?:is|will be|stays?|remains?) (?:still )?(?:there|available|around|safe)",
       rf"(?:variables?|memory|ram|it|everything){G}(?:is|are|gets?){G}{ACT(r'(?:wiped|cleared|lost|gone|reset|erased|emptied)')}{G}(?:restarts?|reboots?|crash|redeploy)")
extend("bad_browser_trust",
       rf"{ACT(r'(?:trust|accept|use)')}{G}(?:price|total){G}{B} (?:sends?|supplies|gives|provides|sent)")

# Wrong designs a careless quote could otherwise slip past (see scripts/evaluate_checker.py).
extend("bad_729",
       rf"{ACT(r'(?:change|update|edit)')}{T}(?:label|text|title|heading|display)")
extend("bad_event_cell",
       rf"{ACT(r'(?:keep|store|save|put)')}{T}(?:all|every|the) (?:attempts|responses|events){T}(?:one|a single|the same) (?:row|cell|field|column)")
extend("bad_fk_direction",
       rf"learners?{T}(?:foreign key|fk){T}(?:to|for){T}attempts?",
       rf"(?:comma|list){T}(?:in|inside|on){T}learner (?:row|record)",
       rf"(?:one|a single) row per learner",
       rf"attempts?(?: table)?{T}inside{T}learner (?:row|record)")


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
