"""The fixed Module 2 scope from the hackathon brief."""

IDEAS = {
    "BACKEND_PURPOSE": "Why does a backend exist?",
    "API_REQUEST": "What does an API call carry?",
    "API_AUTH": "Why must private keys stay off the browser?",
    "PERSISTENCE": "How does an app remember?",
    "FOREIGN_KEY_MANY_SIDE": "Why is the foreign key on the many side?",
    "EVENT_ROWS": "Why is each attempt a separate row?",
    "DATA_LOCATION": "Where should each piece of data live?",
}


def public_case(row):
    """Never expose answer keys or criteria in an assessment payload."""
    return {key: row[key] for key in ("case_id", "idea_id", "case_question")}


def select_fresh_case(rows, idea_id, seen_ids):
    """Do not silently test another concept or reuse a seen case."""
    if idea_id not in IDEAS:
        raise ValueError("Unsupported Module 2 idea.")
    eligible = sorted(
        (row for row in rows if row["idea_id"] == idea_id
         and row["case_id"] not in seen_ids),
        key=lambda row: row["case_id"],
    )
    if not eligible:
        raise ValueError("No unseen case is available for this idea.")
    return eligible[0]
