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


# Short lessons for the Learn part of each concept: the idea, an everyday analogy, a small
# example and a common mistake. Learners read them first; the Check part (explain, one
# follow-up, a fresh case) then shows whether they understood or are reciting.
LESSONS = {
    "BACKEND_PURPOSE": {
        "idea": "A website runs in two places: the frontend in each user's browser, and the backend on your own server. "
                "Anything in the browser can be read and changed by the user, so it cannot be trusted with things that "
                "matter, such as prices, discounts or permissions. The backend is where the app keeps those rules, applies "
                "them the same way for everyone, and can update them in one place.",
        "analogy": "Price tags on a shop shelf versus the till. A customer can swap the tags on the shelf, but the till looks up the real price.",
        "example": "A discount is checked only in JavaScript. A user opens dev tools and sets discount = 100%. If the server "
                   "recalculates the total itself, the trick changes nothing.",
        "mistake": "\"The frontend hides it, so it is safe.\" Hidden is not secure: the browser has a copy of everything it runs.",
    },
    "API_REQUEST": {
        "idea": "An API call is a message from a client to a server. It says what to do (the method, such as GET or POST), "
                "which thing it is about (the URL path, such as /orders/4821), and any other details the server needs "
                "(query parameters, headers or a body). If the request leaves out something the server needs, like which "
                "order, the server cannot answer.",
        "analogy": "Ordering at a counter: what you want, which item number, and your ticket. Leave out the item number and the staff cannot help.",
        "example": "GET /orders/4821 asks for order 4821. GET /orders asks for all orders. POST /orders with a JSON body creates a new one.",
        "mistake": "Assuming the server knows what you mean. It only knows what is in the request.",
    },
    "API_AUTH": {
        "idea": "An API key is like a password that lets your app use a paid service. Everything sent to the browser, "
                "including JavaScript, can be read by every visitor, so a key in frontend code is public. Keep the key on "
                "your backend: the browser calls your backend, and the backend adds the key and calls the service.",
        "analogy": "You would not print your bank PIN on a flyer you hand to every customer.",
        "example": "Browser → POST /api/translate on your server → the server reads TRANSLATE_KEY from an environment variable "
                   "→ calls the translation API → sends the result back to the browser.",
        "mistake": "Hiding or scrambling the key in minified code. Anyone with dev tools can still find it.",
    },
    "PERSISTENCE": {
        "idea": "A running program keeps values in memory, in variables. Memory is wiped when the page refreshes or the "
                "server restarts. To remember things between visits, save them to durable storage, usually a database, "
                "and load them back when they are needed.",
        "analogy": "A whiteboard versus a notebook. The whiteboard is quick, but it gets wiped; the notebook is still there tomorrow.",
        "example": "progress = 3 in a variable → refresh → gone. Insert each attempt into a database → when the learner "
                   "returns, select their attempts and show them.",
        "mistake": "Saving the data but never loading it back, or thinking a global variable counts as saved.",
    },
    "FOREIGN_KEY_MANY_SIDE": {
        "idea": "When one thing has many of another (one learner, many attempts), use two tables. Each attempt row stores "
                "learner_id, a foreign key that points to its learner. The key goes on the \"many\" side because each "
                "attempt belongs to exactly one learner, while a learner can have any number of attempts.",
        "analogy": "Each library loan slip says which member borrowed the book; the member card does not list every loan ever made.",
        "example": "learners(id, name) and attempts(id, learner_id → learners.id, answer, passed).",
        "mistake": "Adding columns attempt_1, attempt_2 … or a list of attempt IDs in the learner row. It breaks when "
                   "there are more attempts than columns, and it is hard to query.",
    },
    "EVENT_ROWS": {
        "idea": "Each event, such as each attempt, deserves its own row with its own fields (date, result). Then the "
                "database can filter, count, sort and analyse them. Packing many events into one cell turns your data "
                "into text the database cannot query.",
        "analogy": "Receipts kept one by one in a folder versus one long scribbled note listing everything you bought.",
        "example": "Count last week's failed attempts: SELECT count(*) FROM attempts WHERE passed = false AND created_at >= '2026-11-09'.",
        "mistake": "Overwriting the old attempt with the newest one. The history, and what changed, is lost.",
    },
    "DATA_LOCATION": {
        "idea": "Different data belongs in different places. Fixed lists that ship with the app go in code. Secrets such "
                "as API keys go in server environment variables or a secrets manager, never in code or the browser. "
                "Records that must last, such as attempts, go in a database. Short-lived screen information, such as a "
                "loading message, stays in UI state.",
        "analogy": "A kitchen: the recipe book (code), a locked safe (secrets), the pantry (database), and the timer you set while cooking (UI state).",
        "example": "The concept list lives in the code; SESSION_SECRET is set in the hosting settings; each attempt is a "
                   "database row; \"Checking your answer…\" is shown only while the request runs.",
        "mistake": "Committing secrets to GitHub, or storing temporary screen state in the database.",
    },
    "HTTP_RESPONSE": {
        "idea": "Every request gets a response with a status code that tells the client what happened: 2xx means success "
                "(201 Created for a new record), 4xx means the request was wrong (400, 404), and 5xx means the server "
                "failed (500). The client should check the code and handle errors instead of assuming success.",
        "analogy": "A delivery receipt: \"delivered\", \"address not found\" or \"depot closed\" each tell you what to do next.",
        "example": "POST /attempts → 201 Created with the new id. A missing field → 400. The database is down → 500, and "
                   "the app shows \"please try again\".",
        "mistake": "Always returning 200 OK, even when saving failed, so the client believes something that is not true.",
    },
    "REFERENTIAL_INTEGRITY": {
        "idea": "A foreign key constraint makes the database itself check links: attempts.learner_id must match an "
                "existing learners.id. Inserting an attempt for a learner that does not exist is rejected, so no "
                "\"orphan\" rows appear, whatever bug the app code has.",
        "analogy": "A guest list at the door: if your name is not on the list, you do not get in.",
        "example": "attempts.learner_id REFERENCES learners(id). Inserting an attempt with learner_id 99, when there is no learner 99, fails.",
        "mistake": "Relying only on app code to check. One bug or one manual insert is enough to create orphans.",
    },
    "RETRY_GAP": {
        "idea": "When a learner struggles, record the difficulty as a gap. When they try again, the retry stores the gap's "
                "id. That link lets you trace difficulty → follow-up question → retry → result, and see whether "
                "practice actually closed the gap.",
        "analogy": "A doctor's follow-up visit refers back to the original diagnosis, so you can tell whether the treatment worked.",
        "example": "gaps(id, attempt_id, follow_up_question) and attempts(…, gap_id → gaps.id). This app stores its own retries this way.",
        "mistake": "Saving the retry with no link. The data shows that the learner tried again, but not what they were trying to fix.",
    },
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
