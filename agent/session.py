import uuid
from dataclasses import dataclass

@dataclass
class Plan:
    id: int
    title: str
    status: str
    description: str
    agent: str


@dataclass
class SessionItem:
    id: str
    action: str
    reason: str
    plan: list[Plan]




class Session:

    id: str
    sessionItems: list[SessionItem]

    def __init__(self):
        self.id = str(uuid.uuid4())

    def get_sessionItem_by_id(self, id: str):
        for s in self.sessionItems:
            if (s.id == id):
                return s
    
