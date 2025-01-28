import os
from flask import Flask, jsonify, request
from google.cloud import bigquery

app = Flask(__name__)

PROJECT_ID = "agentarena-448413"
BIGQUERY_DATASET = "agents"
BIGQUERY_TABLE = "answers"
BIGQUERY_TABLE_ID = "agentarena-448413.agents.answers" 

QUESTIONS = [
    {"id": 1, "text": "What is your favorite color ?"},
    {"id": 2, "text": "What is the capital of France?"},
    # Add more questions here
]

# Initialize BigQuery client
bq_client = bigquery.Client(project=PROJECT_ID)
table_ref = bq_client.dataset(BIGQUERY_DATASET).table(BIGQUERY_TABLE)

@app.route('/questions', methods=['GET'])
def get_questions():
    """Returns the list of questions to the client."""
    return QUESTIONS

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Receives and stores the answer from the client in BigQuery."""
    data = request.get_json()
    if not data or 'question_id' not in data or 'answer' not in data:
        return jsonify({"error": "Invalid request. Missing question_index or answer."}), 400

    question_id = data.get('question_id')
    answer_text = data.get('answer')

    try:
        rows_to_insert = [{
            "Agent ID": "Test",
            "Question": question_id,
            "Answer": answer_text
        }]
        errors = bq_client.insert_rows_json(table_ref, rows_to_insert)
        if errors == []:
            return jsonify({"message": "Answer submitted successfully!", "answer": answer_text}), 201
        else:
            print(f"Errors inserting rows: {errors}")
            return jsonify({"error": "Failed to store answer in BigQuery.", "details": errors}), 500
    except Exception as e:
        print(f"Error processing answer submission: {e}")
        return jsonify({"error": "Internal server error.", "details": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))