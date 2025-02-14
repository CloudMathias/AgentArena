from firebase_admin import firestore
from pydantic import BaseModel, TypeAdapter
from google.genai import types

import concurrent.futures
import json

GRADING_PROMPT="""You are an AI answer evaluator. Your task is to assess the quality of answers provided by AI agents based on a set of criteria.

You will be given the following information:
    - Question: the question that was asked to the AI Agent
    - Scoring Rubrics: A scoring rubrics that will be used to determine the number of points to award to the AI Agent's answer
    - Agent Answer: The answer provided by the AI agent.

You should return the following:
    - Score: The score that you awarded to the AI Agent's answer.
    - Feedback: An explaination for why the score you chose was awarded, as well as some feedback on how the AI agent could improve its answer.
"""

GradingResponseSchema = {
    "type": "OBJECT",
    "properties": {
        "score": { "type":"INTEGER" },
        "feedback": { "type":"STRING" }
    }, 
    "required": ["score","feedback"]
}


class GradingService():
    def __init__(self, genai_client, db, questionService):
        self.genai_client = genai_client
        self.db = db
        self.questionService = questionService

    def grade_answer(self, question_id, answer):
        try:
            # Get the question
            question = self.questionService.getQuestion(question_id)
            if not question:
                raise Exception(f"question {question_id} not found")
            
            # Create a grading request to pass to the LLM
            grading_request = {
                "question": question['text'],
                "agent_answer": answer,
                "scoring_rebrics": question['scoring_rubrics']
            }

            # TODO: Exponential backoffs, region failover & model failover.
            # Grade the answer using an LLM
            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=json.dumps(grading_request),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GradingResponseSchema,
                    system_instruction=GRADING_PROMPT
                )
            )

            grading_response = response.parsed
            grade = {
                'question_id': question_id,
                'question_text': question['text'],
                'answer': answer,
                'score': grading_response['score'],
                'feedback': grading_response['feedback'],
            }

            return grade
        except Exception as e:
            raise Exception(f"error grading answer: {e}")

    def grade_answers(self, answers):
        grades = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.grade_answer, answer["question_id"], answer["answer"]) for answer in answers]
            for future in futures:
                grades.append(future.result())
        return grades
    
    def submit_assignment(self, agent_id, answers):
        try:
            grades = self.grade_answers(answers)
            
            # Save grades to Firestore
            col_ref = self.db.collection('agents').document(agent_id).collection('submissions')
            col_ref.add({
                'grades': grades,
                'created_at': firestore.SERVER_TIMESTAMP,
            })
            return grades
        except Exception as e:
            raise Exception(f"error submitting assignment: {e}")