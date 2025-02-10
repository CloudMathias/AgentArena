import os
import json
import logging
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage

app = Flask(__name__)

PROJECT_ID = "agentarena-448413"
FIRESTORE_COLLECTION = "answers"  # Firestore collection name
GCS_BUCKET_NAME = "agent_arena_questions"
QUESTIONS_FILE = "questions.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')  # Improved format

# Initialize Firebase Admin SDK
cred = credentials.ApplicationDefault()  # Uses default credentials
firebase_admin.initialize_app(cred, {
    'projectId': PROJECT_ID,
})
db = firestore.client()

# Initialize GCS client
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(GCS_BUCKET_NAME)
blob = bucket.blob(QUESTIONS_FILE)

try:
    json_data = blob.download_as_bytes()
    QUESTIONS = json.loads(json_data)
    logging.info("Questions loaded from GCS successfully.")  # Use logging.info
except Exception as e:
    logging.error(f"Error loading questions from GCS: {e}")  # Use logging.error
    QUESTIONS = [
        {"id": 1, "text": "What is your favorite color?"},
        {"id": 2, "text": "What is the capital of France?"},
    ]
    logging.info("Using default fallback questions.")  # Use logging.info


@app.route('/questions', methods=['GET'])
def get_questions():
    logging.info("GET /questions requested")  # Log the request
    return jsonify(QUESTIONS)


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.get_json()
    logging.info(f"POST /submit_answer requested with data: {data}")  # Log the request data

    if not data or 'agent_id' not in data or 'question_id' not in data or 'answer' not in data:
        logging.warning("Invalid request. Missing required fields.")  # Use logging.warning
        return jsonify({"error": "Invalid request. Missing agent_id, question_id, or answer."}), 400

    agent_id = data.get('agent_id')
    question_id = data.get('question_id')
    answer_text = data.get('answer')

    try:
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(f"{agent_id}_{question_id}")

        doc = doc_ref.get()
        if doc.exists:
            doc_ref.update({"Answer": answer_text})
            logging.info(f"Answer updated for agent {agent_id}, question {question_id}") # Log the update
        else:
            doc_ref.set({"agent_id": agent_id, "question_id": question_id, "answer": answer_text})
            logging.info(f"Answer submitted for agent {agent_id}, question {question_id}") # Log the submission

        return jsonify({"message": "Answer submitted successfully!", "answer": answer_text}), 201

    except Exception as e:
        logging.exception(f"Error processing answer submission: {e}")  # Use logging.exception
        return jsonify({"error": "Internal server error.", "details": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
