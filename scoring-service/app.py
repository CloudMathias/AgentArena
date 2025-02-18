import json
import re
import base64
import firebase_admin
import logging
from firebase_admin import credentials, firestore
from google.cloud import storage
from google.cloud import pubsub_v1
from google import genai
from google.genai import types
import functions_framework

PROJECT_ID = "agentarena-448413"
FIRESTORE_COLLECTION = "scores"
GCS_BUCKET_NAME = "agent_arena_questions"
QUESTIONS_FILE = "questions_answers.json"

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': PROJECT_ID,
})
db = firestore.client()

storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(GCS_BUCKET_NAME)
blob = bucket.blob(QUESTIONS_FILE)

try:
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

client = genai.Client(
    vertexai=True,
    project="agentarena-448413",
    location="europe-west1",
)

model = "gemini-2.0-flash-001"

generate_content_config = types.GenerateContentConfig(
    temperature=1,
    top_p=0.95,
    max_output_tokens=2,
    response_modalities=["TEXT"],
    safety_settings=[types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="OFF"
    ), types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="OFF"
    ), types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="OFF"
    ), types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="OFF"
    )],
)

def extract_integer_from_llm_output(llm_output):
    if not isinstance(llm_output, str):
        return None
    match = re.search(r'\d+', llm_output)
    if match:
        try:
            return int(match.group())
        except ValueError:
            return None
    else:
        return None

def generate(question, scoring_criteria, answer):
    if answer == "":
        answer = "No answer from the agent"
    text1 = types.Part.from_text(text=f"""You are an AI answer evaluator. Your task is to assess the quality of answers provided by AI agents based on a set of criteria. You will be given the question, the important points that should be included in the answer, and the actual answer provided by the AI agent.  Your output should be a score from 1 to 10, where 1 is the lowest score (very poor answer) and 10 is the highest score (excellent answer).

Instructions:

1. Carefully analyze the question and understand its nuances.
2. Review the important points that should be present in a good answer. These points serve as your evaluation criteria.
3. Evaluate the AI agent's answer based on how well it addresses the question and incorporates the important points.
4. Consider the following factors when assigning a score:
    * Accuracy: Does the answer correctly address the question?
    * Completeness: Does the answer cover all the important points?
    * Clarity: Is the answer easy to understand and well-organized?
    * Relevance: Is the information provided in the answer relevant to the question?
    * Conciseness: Is the answer concise and to the point, avoiding unnecessary information?

5. Assign a score from 1 to 10 based on your overall assessment.  Be objective and consistent in your scoring.

Input:

Question: {question}

Important Points: {scoring_criteria}

Answer: {answer}

Output:  Return only a numerical value from 1 to 10. Do not include any other text. Do not include any space""")
    contents = [
        types.Content(
            role="user",
            parts=[
                text1
            ]
        )
    ]
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    return response.text

@functions_framework.cloud_event
def score_answers(cloud_event):
    """Background Cloud Function to be triggered by Pub/Sub.
       This function scores answers submitted by agents.
    """
    message = cloud_event.data["message"]
    if not message or "data" not in message:
        logging.error(f"invalid cloud_event format: {cloud_event}")
        raise Exception(f"failed to extract data from cloud event: {cloud_event}")
    
    try:
        # Extract the data from the events body.
        encoded_data = message["data"]
        decoded_data = base64.b64decode(encoded_data).decode("utf-8")
        logging.info(f"Successfully decoded event data: {decoded_data}")
        data = json.loads(decoded_data)
        agent_id = data['agent_id']
        question_id = data['question_id']
        answer_text = data['answer']

        question = next((q['text'] for q in QUESTIONS if q['id'] == question_id), None)
        scoring_criteria = next((q['criteria'] for q in QUESTIONS if q['id'] == question_id), None)
        if not question or not scoring_criteria:
            logging.error(f"question or scoring criteria not found for question ID: {question_id}")
            raise Exception(f"question or scoring criteria not found for question ID: {question_id}")

        # Generate a score for each question in relation to the scoring criteria.
        llm_output = generate(question, scoring_criteria, answer_text)
        score = extract_integer_from_llm_output(llm_output)
        if score is None:
            logging.error(f"Invalid score generated for agent {agent_id}, question {question_id}: {llm_output}")
            raise Exception(f"Invalid score generated for agent {agent_id}, question {question_id}: {llm_output}")
        
        # Save the agent's score to the database.
        score = int(score)
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(f"{agent_id}_{question_id}")
        doc_ref.set({
            'agent_id': agent_id,
            'question_id': question_id,
            'answer': answer_text,
            'score': score
        })
        logging.info(f"Scored answer for agent {agent_id}, question {question_id}: {score}")
            

    except Exception as e:
        print(f"Error processing message: {e}")