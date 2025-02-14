import os
import time
from flask import Flask, render_template, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ID = "agentarena-448413"
FIRESTORE_COLLECTION = "scores"

try:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'projectId': PROJECT_ID,
    })
    db = firestore.client()
    logger.info("Firebase connection established successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    db = None  # Ensure db is None if Firebase fails

def get_ranked_agents():
    if db is None:
        logger.error("Firebase database connection is not available.")
        return []

    agent_scores = {}
    try:
        docs = db.collection(FIRESTORE_COLLECTION).stream()
        for doc in docs:
            data = doc.to_dict()
            agent_id = data.get('agent_id')
            score = data.get('score', 0)
            if agent_id:
                agent_scores[agent_id] = agent_scores.get(agent_id, 0) + score
        ranked_agents = [{"agent_id": agent_id, "total_score": total_score}
                         for agent_id, total_score in agent_scores.items()]
        ranked_agents.sort(key=lambda x: x["total_score"], reverse=True)
        logger.info("Successfully retrieved and ranked agents.")
        return ranked_agents
    except Exception as e:
        logger.error(f"Error retrieving scores from Firestore: {e}")
        return []

@app.route('/')
def index():
    ranked_agents = get_ranked_agents()
    return render_template('scores.html', ranked_agents=ranked_agents)

@app.route('/api/scores')
def api_scores():
    ranked_agents = get_ranked_agents()
    return jsonify(ranked_agents)

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 8081))
        logger.info(f"Starting Flask application on port {port}")
        app.run(debug=False, host='0.0.0.0', port=port)
    except Exception as e:
        logger.critical(f"Failed to start Flask application: {e}")