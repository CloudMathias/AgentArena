import os
import json
import logging

class QuestionService:

    def __init__(self, storage_client):
        try:
            GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")
            QUESTIONS_FILENAME = os.environ.get("QUESTIONS_FILENAME")
            logging.info(f"Loading questions from GCS: {GCS_BUCKET_NAME}/{QUESTIONS_FILENAME}")
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(QUESTIONS_FILENAME)

            data = blob.download_as_bytes()
            questions = json.loads(data)

            self.questions = {}
            for question in questions:
                self.questions[question['id']] = question
            logging.info(f"Questions loaded from GCS successfully: {self.questions}")
        except Exception as e:
            raise Exception(f"Error loading questions from GCS: {e}")

    def getQuestion(self, question_id):
        return self.questions.get(question_id)

    def getQuestions(self):
        questions = [{'id': question['id'], 'text': question['text']} for question in self.questions.values()]
        return questions