import os
import time
from flask import Flask, render_template
import firebase_admin
from firebase_admin import credentials, firestore
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

PROJECT_ID = "agentarena-448413"
FIRESTORE_COLLECTION = "scores"

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': PROJECT_ID,
})
db = firestore.client()

def get_ranked_agents():
    agent_scores = {}
    try:
        docs = db.collection(FIRESTORE_COLLECTION).stream()
        for doc in docs:
            data = doc.to_dict()
            agent_id = data.get('agent_id')
            score = data.get('score', 0)
            if agent_id:
                if agent_id in agent_scores:
                    agent_scores[agent_id] += score
                else:
                    agent_scores[agent_id] = score
        ranked_agents = []
        for agent_id, total_score in agent_scores.items():
            ranked_agents.append({"agent_id": agent_id, "total_score": total_score})
        ranked_agents.sort(key=lambda x: x["total_score"], reverse=True)
        return ranked_agents
    except Exception as e:
        print(f"Error retrieving scores: {e}")
        return

@app.route('/')
def index():
    ranked_agents = get_ranked_agents()
    return render_template('scores.html', ranked_agents=ranked_agents)

def background_thread():
    while True:
        socketio.emit('update_scores', {'data': get_ranked_agents()})
        time.sleep(5)

@socketio.on('connect')
def connect():
    print('Client connected')
    socketio.start_background_task(background_thread)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8081)))