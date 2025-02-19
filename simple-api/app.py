import os
import logging
from flask import Flask, jsonify, request, render_template
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage
from grading import GradingService
from question import QuestionService
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')  # Improved format

if load_dotenv():
    logging.info("Environment variables loaded successfully.")
else:
    logging.warning("No .env file found.")

PROJECT_ID = os.environ.get("PROJECT_ID")

app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.ApplicationDefault()  # Uses default credentials
firebase_admin.initialize_app(cred, {
    'projectId': PROJECT_ID,
})
db = firestore.client()

# Initialize GCS client
storage_client = storage.Client(project=PROJECT_ID)

# Initialize dependencies
question_service = QuestionService(storage_client)
grading_service = GradingService(db, question_service)

@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    return render_template('leaderboard.html')

@app.route('/api/v2/scores', methods=['GET'])
def get_scores():
    try:
        scores = grading_service.get_scores()
        return jsonify(scores), 200
    except Exception as e:
        logging.error(f'failed to get scored: {e}')
        return jsonify(f"failed to get questions"), 500
    
@app.route('/api/v2/scores/<agent_id>', methods=['GET'])
def get_score(agent_id):
    try:
        if not agent_id:
            logging.warning("Invalid request. Missing agent_id")
            return jsonify({"error": "Invalid request. Missing agent_id."}), 400

        score = grading_service.get_score(agent_id)
        return jsonify(score), 200
    except Exception as e:
        logging.error(f'failed to get scored: {e}')
        return jsonify(f"failed to get questions"), 500

@app.route('/api/v2/questions', methods=['GET'])
def get_questions():
    try:
        logging.info("GET /api/v2/questions")
        questions = question_service.getQuestions()
        logging.info(f"Successfully got questions: {questions}")
        return jsonify({'questions': questions}), 200
    except Exception as e:
        logging.error(f"Error getting questions: {e}")
        return jsonify({"error": f"Error getting questions: {e}"}), 500

@app.route('/api/v2/submit', methods=['POST'])
def submit_assignment():
    data = request.get_json()
    logging.info(f"POST /api/v2/submit requested with data: {data}")

    if not data:
        logging.warning("Invalid request. Missing required fields.")
        return jsonify({"error": "Invalid request. Missing data."}), 400
    
    if 'agent_id' not in data:
        logging.warning("Invalid request. Missing agent_id.")
        return jsonify({"error": "Invalid request. Missing agent_id."}), 400
    
    if 'answers' not in data:
        logging.warning("Invalid request. Missing answers.")
        return jsonify({"error": "Invalid request. Missing answers."}), 400
    
    agent_id = data['agent_id']

    # Score each answer
    try:
        grades = grading_service.submit_assignment(agent_id, data.get('answers'))
        logging.info(f"Assignment submitted successfully for agent {agent_id}. Grades: {grades}")
        return jsonify({"grades": grades}), 200
    except Exception as e:
        logging.error(f"Error submitting assignment for agent {agent_id}: {e}")
        return jsonify({"error": f"Error submitting assignment: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
