"""The fixed Module 2 scope from the hackathon brief."""

IDEAS = {
    "BACKEND_PURPOSE": "Why does a backend exist?",
    "API_REQUEST": "What does an API call carry?",
    "API_AUTH": "Why must private keys stay off the browser?",
    "PERSISTENCE": "How does an app remember?",
    "FOREIGN_KEY_MANY_SIDE": "Why is the foreign key on the many side?",
    "EVENT_ROWS": "Why is each attempt a separate row?",
    "DATA_LOCATION": "Where should each piece of data live?",
    "HTTP_RESPONSE": "How does an API tell the client what happened?",
    "REFERENTIAL_INTEGRITY": "How does the database stop broken links?",
    "RETRY_GAP": "Why should a retry point to its gap?",
}


# Plain-language words for learners who are new to the curriculum. They explain what the
# words MEAN, never why or how to solve the case: tests check that no word list meets
# any graded idea ("Ideas they never met. Stick to Module 2.").
WORDS = {
    "BACKEND_PURPOSE": [
        ("Frontend", "the part of a website that runs in the browser: the pages and buttons people see."),
        ("Backend", "the part of an app that runs on the company's own server."),
        ("Business rules", "a company's rules for things like prices, discounts or refunds."),
    ],
    "API_REQUEST": [
        ("API", "a way for one program to ask another program for something."),
        ("API call (request)", "the message an app sends to a server. It goes to an address (a URL) and can carry extra details."),
        ("Order ID", "the number that names one order, like 4821."),
    ],
    "API_AUTH": [
        ("API key", "a secret code, like a password, that lets an app use a paid service such as an AI model or a weather service."),
        ("Frontend / browser JavaScript", "code that runs in the visitor's browser to make the page work."),
        ("Backend / server", "the computer that runs the app's own server code."),
    ],
    "PERSISTENCE": [
        ("Variable", "a named value in a program, like score = 3."),
        ("Database", "an organised store of data, a bit like a set of spreadsheets."),
        ("Refresh / restart", "reloading a web page, or turning the server program off and on again."),
    ],
    "FOREIGN_KEY_MANY_SIDE": [
        ("Table, row, column", "a database stores data in tables, like spreadsheets. Each row is one record; each column is one field."),
        ("Learner and attempt", "a learner is a person using a learning app; an attempt is one answer they submit."),
        ("Foreign key", "a column in one table that holds the id of a row in another table, like a learner's id number."),
    ],
    "EVENT_ROWS": [
        ("Attempt", "one answer a learner submits in a learning app."),
        ("Table, row, column", "a database stores data in tables, like spreadsheets. Each row is one record; each column is one field, like date or result."),
        ("Cell", "one box in a table: one column of one row."),
    ],
    "DATA_LOCATION": [
        ("Code", "the program files the developer writes and ships."),
        ("Environment variable", "a setting stored on the server, outside the code files."),
        ("Database", "an organised store of data, a bit like a set of spreadsheets."),
        ("UI state", "what the screen is currently showing, such as which tab is open."),
    ],
    "HTTP_RESPONSE": [
        ("Client", "the program that sends a request, such as a browser or a mobile app."),
        ("API", "a server program that receives requests from clients."),
        ("Response", "the message the server sends back after every request."),
    ],
    "REFERENTIAL_INTEGRITY": [
        ("Table, row", "a database stores data in tables, like spreadsheets; each row is one record."),
        ("learner_id", "a column in the attempts table holding the id number of the learner who made the attempt."),
        ("Broken link", "an attempt whose learner_id is a number that no learner has."),
    ],
    "RETRY_GAP": [
        ("Gap", "a weak spot a learning app found in a learner's explanation, such as one sentence that sounded memorised."),
        ("Follow-up", "the one question the app asks about that weak spot."),
        ("Retry", "the learner's second try, written after the follow-up question."),
    ],
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
