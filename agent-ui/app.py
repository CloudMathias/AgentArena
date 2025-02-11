import os
from flask import Flask, render_template
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

PROJECT_ID = "agentarena-448413"
FIRESTORE_COLLECTION = "scores"

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': PROJECT_ID,
})
db = firestore.client()

@app.route('/')
def index():
    scores = []
    try:
        docs = db.collection(FIRESTORE_COLLECTION).stream()
        for doc in docs:
            data = doc.to_dict()
            scores.append(data)
    except Exception as e:
        print(f"Error retrieving scores: {e}")
        return "Error retrieving scores."

    return render_template('scores.html', scores=scores)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))