import os
from flask import Flask, jsonify, request
from google.cloud import bigquery

app = Flask(__name__)

# Initialize BigQuery client
client = bigquery.Client()
table_id = "agentarena-448413.agents.answers"  

questions = [
    {"id": 1, "text": "What is your favorite color?"},
    {"id": 2, "text": "What is the capital of France?"},
    # Add more questions here
]

@app.route('/api/questions', methods=['GET', 'POST'])
def getQuestions():
    if request.method == 'GET':
        print('GET request received')
        return jsonify(questions)

    if request.method == 'POST':
        data = request.get_json()
        print(f'POST request received with data: {data}')

        # Insert answer into BigQuery
        rows_to_insert = [
        {"Agent ID": "agent1", "Question": data.get('question_id'), "Answer": data.get('answer')}
        ]
        errors = client.insert_rows_json(table_id, rows_to_insert)
        if not errors:
            print("New rows have been added.")
        else:
            print("Encountered errors while inserting rows: {}".format(errors))

        return jsonify({'message': 'Answer received and stored', 'data': data})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))