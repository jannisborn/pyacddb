from copy import deepcopy

import requests

INSTRUCTION_MESSAGE = """
Du kannst Fotos anfragen indem du mir einen oder mehrere Tags sendest. Ich werde dann
die entsprechenden Fotos aus der Datenbank suchen. Schreib zum Beispiel:

\t`Kurioses`\tum alle kuriosen Fotos zu sehen.

Oder schreib:
\t`Micha Jannis`\tund ich werde dir alle Fotos zeigen auf denen Micha UND Jannis sind.

Wenn ein einzelner Tag ein Leerzeichen enthält, dann schreib ihn in Anführungszeichen, z.B.:
\t`"Münster Kemperweg" Micha`\tum alle Fotos zu sehen, die Micha am Kemperweg zeigen.
Du kannst beliebig viele Tags kombinieren.

Um eine Übersicht zu sehen welche Tags verfügbar sind, schreibe einfach `Tags`!
Viel Spass!🥳
"""


class LLM:
    def __init__(
        self,
        token: str,
        task_prompt: str,
        model: str = "mistralai/Mistral-7B-Instruct-v0.1",
        temperature: float = 0.7,
    ):
        self.token = token
        self.api_base = "https://api.endpoints.anyscale.com/v1"
        self.session = requests.Session()
        self.url = f"{self.api_base}/chat/completions"
        self.model = model
        self.temperature = temperature
        self.task_prompt = task_prompt
        self.body = {
            "model": model,
            "messages": [
                {"role": "system", "content": task_prompt},
            ],
            "temperature": temperature,
        }
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.counter = 0

    def send_message(self, message: str):
        body = deepcopy(self.body)
        body["messages"].append({"role": "user", "content": message})
        with self.session.post(self.url, headers=self.headers, json=body) as resp:
            output = resp.json()
        self.counter += 1
        return output["choices"][0]["message"]["content"]

    def __call__(self, *args, **kwargs):
        return self.send_message(*args, **kwargs)
