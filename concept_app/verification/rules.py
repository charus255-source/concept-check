"""Case-specific authored checks; no inferred or model-generated criteria."""

from dataclasses import dataclass

VERSION = "1.3.0"


@dataclass(frozen=True)
class Check:
    fact: str
    feedback: str


@dataclass(frozen=True)
class Rule:
    required: tuple[Check, ...]
    contradictions: tuple[str, ...]


def rule(checks, contradictions):
    return Rule(tuple(Check(*check) for check in checks), tuple(contradictions))


RULES = {
    1: rule([("browser_exposure", "Explain how users can inspect or alter browser rules."),
             ("server_rules", "Identify the backend's responsibility for the rules."),
             ("rule_benefit", "Explain centralization, consistent application, independent updates, or why browser rules cannot be the authority.")], ["bad_browser_trust"]),
    # Real learners answered "what should the request carry?" with the order ID and where it
    # goes; requiring them to also name the operation rejected correct answers (1.2.0).
    2: rule([("request_order", "Say what the request must carry: the order ID, e.g. in the URL path or a parameter.")],
            ["bad_body_required"]),
    3: rule([("browser_exposure", "Explain how visitors can access browser-delivered code."),
             ("key_extraction", "Explain how visitors could extract the private key."),
             ("browser_backend", "Describe the browser calling the application backend."),
             ("server_key", "Identify the server as the place that retains the private key."),
             ("server_call", "Describe the backend making the authorized API call.")], ["bad_key_browser"]),
    4: rule([("temporary_loss", "Explain loss of temporary state on refresh or restart."),
             ("save_durable", "Describe saving progress in durable storage."),
             ("retrieve_saved", "Describe retrieving the saved progress.")], ["bad_temp"]),
    5: rule([("separate_entities", "Represent learners and attempts in separate tables."),
             ("attempt_learner", "Show each attempt pointing to its learner.")], ["bad_fk_direction"]),
    6: rule([("combined_problem", "Explain a query or relationship problem with combined events."),
             ("each_attempt_row", "Store every attempt as its own row.")], ["bad_event_cell"]),
    7: rule([("fixed_code", "Map the fixed concept list to code."),
             ("secret_location", "Map secrets to server environment configuration or a secrets manager."),
             ("attempt_location", "Map saved attempts to durable database storage."),
             ("loading_location", "Map the loading message to temporary UI state.")], ["bad_key_browser", "bad_temp"]),
    8: rule([("response_status", "Describe the API returning an outcome status."),
             ("client_errors", "Explain client handling of error responses.")], ["bad_response"]),
    9: rule([("foreign_key", "Identify the attempt-to-learner foreign-key relationship."),
             ("reject_orphan", "Explain why nonexistent learners cannot be referenced.")], ["bad_orphan", "bad_fk_direction"]),
    10: rule([("retry_gap", "Link the retry attempt to the gap it addresses."),
              ("trace_gap", "Explain tracing the original difficulty to the subsequent retry/result.")], ["bad_gap"]),
    11: rule([("trusted_price", "Have the backend calculate or validate the authoritative price."),
              ("not_browser_price", "Reject trusting the browser-supplied price as authority.")], ["bad_browser_trust"]),
    12: rule([("order_729", "Change the request's order identifier to 729.")], ["bad_729"]),
    13: rule([("browser_backend", "Route the third-party request through the backend."),
              ("server_key", "Keep the key on the server."),
              ("server_call", "Have the backend make the authorized third-party call.")], ["bad_key_browser"]),
    14: rule([("save_durable", "Save attempts in durable storage."),
              ("retrieve_saved", "Retrieve the saved attempts on return.")], ["bad_temp"]),
    15: rule([("each_attempt_row", "Store each attempt in a separate row."),
              ("attempt_learner", "Link every attempt to its learner.")], ["bad_fk_direction"]),
    16: rule([("each_attempt_row", "Store each attempt in its own row."),
              ("independent_query", "Explain independent filtering, counting, or analysis.")], ["bad_event_cell"]),
    17: rule([("reject_temporary", "Reject relying only on a temporary variable."),
              ("save_durable", "Save the submitted answer in durable storage."),
              ("survive_restart", "Connect that storage to surviving a restart.")], ["bad_temp"]),
    18: rule([("creation_success", "Return a success status communicating completed attempt creation.")], ["bad_response"]),
    19: rule([("foreign_key", "Identify the foreign key referencing learners.id."),
              ("reject_orphan", "Explain database rejection when the referenced learner is absent.")], ["bad_orphan", "bad_fk_direction"]),
    20: rule([("gap_record", "Store the difficulty as a gap record."),
              ("retry_gap", "Link the retry attempt to that gap."),
              ("followup_gap", "Link the follow-up to the same gap."),
              ("trace_gap", "Preserve the original-difficulty-to-retry relationship.")], ["bad_gap"]),
    # Case variants (1.3.0): fresh scenarios that need the same ideas as a proven case,
    # so learners get a third case per concept (trainer: "add case variants").
    21: rule([("browser_exposure", "Explain how users can inspect or change rules in browser code."),
              ("server_rules", "Identify the backend's responsibility for the refund rules."),
              ("rule_benefit", "Explain centralization, consistent application, independent updates, or why browser rules cannot be the authority.")], ["bad_browser_trust"]),
    22: rule([("request_order", "Say what the request must carry: the order ID, e.g. in the URL path or a parameter.")], ["bad_body_required"]),
    23: rule([("browser_backend", "Route the weather API request through the backend."),
              ("server_key", "Keep the key on the server."),
              ("server_call", "Have the backend make the authorized call to the weather API.")], ["bad_key_browser"]),
    24: rule([("temporary_loss", "Explain that memory is lost when the server restarts."),
              ("save_durable", "Save the attempts in durable storage."),
              ("retrieve_saved", "Retrieve the saved attempts to show the history.")], ["bad_temp"]),
    25: rule([("each_attempt_row", "Store each attempt in a separate row."),
              ("attempt_learner", "Link every attempt to its learner (learner_id foreign key).")], ["bad_fk_direction"]),
    26: rule([("each_attempt_row", "Store each attempt in its own row."),
              ("independent_query", "Explain filtering, counting, or analysis per attempt.")], ["bad_event_cell"]),
    27: rule([("reject_temporary", "Reject relying only on a temporary server variable."),
              ("save_durable", "Save the data in durable storage."),
              ("survive_restart", "Connect that storage to surviving a restart or deploy.")], ["bad_temp"]),
    28: rule([("creation_success", "Return a success status that says the account was created (e.g. 201 Created).")], ["bad_response"]),
    29: rule([("foreign_key", "Identify the foreign key referencing learners.id."),
              ("reject_orphan", "Explain that the database rejects attempts for a learner that does not exist.")], ["bad_orphan", "bad_fk_direction"]),
    30: rule([("retry_gap", "Link each retry attempt to the gap it addresses."),
              ("trace_gap", "Explain tracing the original difficulty to the retry and its result.")], ["bad_gap"]),
}
