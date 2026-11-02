"""Authored regression answers, NOT additional or modified Golden Pairs."""

# Three independently worded supported answers per case. Human learner testing is
# separate; these fixtures do not stand in for discovery or observed learning.
CORRECT = {
 1: [
  "Users can change browser rules. The backend should centralize discount rules.",
  "Anyone can inspect the code. A server can enforce business rules consistently.",
  "Browser code can be changed by users. The backend should apply rules consistently."],
 2: [
  "Send 4821 in the request URL so the identifier tells the server which order to fetch.",
  "The request should carry the order ID and identify the intended operation.",
  "Provide the order identifier in the request. The request should retrieve the order."],
 3: [
  "Visitors can inspect the code and copy the key. The browser calls the backend. Keep the private key on the server. The backend calls the provider API.",
  "Anyone can extract the key from shipped code. Send the request through the backend. The server stores the secret and makes the authorized API call.",
  "Users can read the JavaScript and take the token. The frontend calls the server. The server retains the key and contacts the provider."],
 4: [
  "Temporary state is lost on refresh. Save progress in a database and load the saved progress on return.",
  "A restart clears application memory. Store progress in persistent storage. Retrieve the progress later.",
  "In-memory progress disappears after reload. Persist progress in durable storage and restore it when needed."],
 5: [
  "Store learners in one table and attempts in another. Each attempt has a learner_id referencing its learner.",
  "Learners and attempts belong in separate tables. Every attempt contains a learner ID pointing to its learner.",
  "Learners and attempts use separate tables. Store the learner reference on every attempt."],
 6: [
  "A single cell makes filtering individual events hard. Store each attempt as a separate row.",
  "Comma-separated responses are difficult to filter. Every attempt needs its own record.",
  "Combining attempts makes individual events hard to update. Use one row per attempt."],
 7: [
  "The concept list lives in code. Private keys belong in server-side environment configuration. Attempts belong in database storage. The loading message belongs in temporary UI state.",
  "Keep the fixed list in code. Put credentials in a secrets manager. Save attempts in durable storage. Hold loading status in UI state.",
  "Supported concepts go in code. Secrets stay in server environment configuration. Learner attempts live in persistent storage. Loading text stays in temporary UI state."],
 8: [
  "The server should return an HTTP status code. The client must handle error responses.",
  "Return an appropriate status for the save. Handle failure responses on the client.",
  "The API sends an appropriate HTTP status. The client checks error responses too."],
 9: [
  "A foreign key from attempts.learner_id to learners.id prevents attempts referencing nonexistent learners.",
  "The foreign key on attempts.learner_id references learners.id. The database rejects attempts for missing learners.",
  "Use a foreign key referencing learners.id. That constraint blocks an attempt when its learner does not exist."],
 10: [
  "The retry attempt references its gap. This link connects the original difficulty and follow-up to the subsequent result.",
  "Link the retry to the original gap. The link preserves the original difficulty to retry relationship.",
  "Store the gap ID on the retry attempt. This lets us track which difficulty the retry addresses."],
 11: [
  "The backend should calculate the authoritative price rather than trusting a price supplied by the browser.",
  "The server validates the price using trusted rules. The browser-supplied price must not be trusted.",
  "The backend recalculates the authoritative price instead of accepting the total from the frontend."],
 12: [
  "Change the order ID in the request to 729.",
  "The request should target order 729.",
  "Set the requested order to 729 in the URL path."],
 13: [
  "The website sends the request through its backend. The backend keeps the key and makes the authorized third-party call.",
  "Route the private API request to the server. The server stores the key and contacts the provider.",
  "The page calls the backend. Keep the secret on the server. The backend calls the provider API."],
 14: [
  "Save attempts in a database and retrieve them when the learner returns.",
  "Store the attempts in persistent storage. Load the saved attempts on return.",
  "Persist attempts in durable storage and read the previous attempts later."],
 15: [
  "Each attempt has its own row and contains a learner_id pointing to its learner.",
  "Store each attempt in a separate row with a learner reference.",
  "Use one row per attempt. Put the learner ID on every attempt."],
 16: [
  "Store each attempt as its own row so it can be filtered independently.",
  "Use one row per attempt. Separate rows allow independent counting.",
  "Every attempt gets an individual record so we can analyze it independently."],
 17: [
  "No. Save the answer in a database so it survives a restart.",
  "Do not rely only on a temporary variable. Store the answer in durable storage so the data survives a restart.",
  "A temporary variable is not sufficient. Persist the answer in persistent storage so it lasts across a restart."],
 18: [
  "Return HTTP 201 Created.",
  "Send a success status code for the created attempt.",
  "Respond with 200 OK when creation has completed."],
 19: [
  "A foreign key referencing learners.id rejects the attempt if that learner does not exist.",
  "A foreign key on attempts.learner_id references learners.id. The database blocks attempts for nonexistent learners.",
  "Use a foreign key from attempts.learner_id to learners.id so the constraint prevents attempts referencing missing learners."],
 20: [
  "Store the gap as a record. Link the follow-up and retry attempt to that gap, preserving the relationship between the original difficulty and retry.",
  "Create a gap record. The retry attempt references that gap. The follow-up points to that same gap. This link traces the original difficulty to the subsequent result.",
  "Save the difficulty in a gap row. Link the follow-up and retry to the same gap. This link preserves the original difficulty to retry relationship."],
}

# Appended to otherwise correct answers: recognition must not stop after a pass.
CONTRADICTION = {
 1: "Browser-only rules are authoritative.",
 2: "Every request must include a body.",
 3: "Store the private key in the browser.",
 4: "A temporary variable survives a restart.",
 5: "Store all attempt IDs in the learner row.",
 6: "Store all attempts in one comma-separated cell.",
 7: "Send the private key to every browser.",
 8: "Always report success even when saving fails.",
 9: "Allow orphan attempts.",
 10: "The retry proves understanding.",
 11: "Trust the browser-supplied price.",
 12: "The request targets order 4821.",
 13: "Ship the private key to visitors.",
 14: "Save attempts only in a temporary variable.",
 15: "learners.id -> attempts.learner_id",
 16: "Overwrite past attempts with the latest response.",
 17: "An ordinary temporary variable survives a restart.",
 18: "Return HTTP 500 for successful creation.",
 19: "Accept attempts for nonexistent learners.",
 20: "Link the retry to an unrelated gap.",
}
