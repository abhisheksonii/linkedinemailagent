import os
from typing import Dict

class CoursePersonaAgent:
    """
    Agent to process and store course details and persona information.
    """
    def __init__(self):
        self.course_details = None
        self.persona = None

    def load(self, course_details: str, persona: str):
        self.course_details = course_details
        self.persona = persona

    def get_context(self) -> Dict[str, str]:
        return {
            'course_details': self.course_details,
            'persona': self.persona
        }
