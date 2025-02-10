import os
import json
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage

app = Flask(__name__)

PROJECT_ID = "agentarena-448413"
FIRESTORE_COLLECTION = "answers"  # Firestore collection name
GCS_BUCKET_NAME = "agent_arena_questions"
QUESTIONS_FILE = "questions.json"

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
    # Download the JSON file from GCS
    json_data = blob.download_as_bytes()
    QUESTIONS = json.loads(json_data)
    print("Questions loaded from GCS successfully.")
except Exception as e:
    print(f"Error loading questions from GCS: {e}")
    QUESTIONS = [
        {"id": 1, "text": "What is your favorite color?"},
        {"id": 2, "text": "What is the capital of France?"},
    ]
    print("Using default fallback questions.")


@app.route('/questions', methods=['GET'])
def get_questions():
    return jsonify(QUESTIONS)


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.get_json()
    if not data or 'agent_id' not in data or 'question_id' not in data or 'answer' not in data:
        return jsonify({"error": "Invalid request. Missing agent_id, question_id, or answer."}), 400

    agent_id = data.get('agent_id')
    question_id = data.get('question_id')
    answer_text = data.get('answer')

    try:
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(f"{agent_id}_{question_id}") # Use composite key

        doc = doc_ref.get()
        if doc.exists:  # Document exists, update it
            doc_ref.update({"Answer": answer_text})
        else:  # Document doesn't exist, create it
            doc_ref.set({"agent_id": agent_id, "question_id": question_id, "answer": answer_text})

        return jsonify({"message": "Answer submitted successfully!", "answer": answer_text}), 201

    except Exception as e:
        print(f"Error processing answer submission: {e}")
        return jsonify({"error": "Internal server error.", "details": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
