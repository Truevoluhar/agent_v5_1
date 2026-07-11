import uuid
from dataclasses import dataclass

class Session:

    id: str
    messages: list[dict]

    def __init__(self):

        self.id = str(uuid.uuid4())
        self.messages = []

        self.create_session_jsonl()




    def create_session_jsonl(self):
        open(f"session_{self.id}.jsonl", "x")


    def add_message(self, message: dict):
        
        msg_string = str(message)
        if len(self.messages) > 0:
            msg_string = "\n" + msg_string
        
        self.messages.append(message)

        
        with open(f"session_{self.id}.jsonl", "a", encoding="utf-8") as f:
            f.write(msg_string)


    def get_messages_for_agent(self):
        None
