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

Um ebenfalls die Caption der Bilder zu benutzen, benutze `cap: `:
\t`Micha Cap: Garten`\t zeigt alle Bilder mit dem Tag Micha deren Caption den String
`Garten` enthält.

Um ebenfalls die Daten der Bilder zu durchsuchen benutze `date: `:
\t`Haus Date: 1910-1950`\t zeigt alle Bilder mit dem Tag Haus zwischen 1910 und 1950 (inklusive)
Verwende immer einen einzelnen Trennstrich zwischen Start- und Enddatum.

`date:` und `cap:` lassen sich beliebig mit der "normalen" Tagsuche kombinieren, aber achte
darauf immer ein Leerzeichen nach dem Doppelpunkt zu lassen. Ein komplexeres Beispiel:

\t`"Münster Kemperweg" Haus Date: 19950601-19980130 Cap: Dach`\t zeigt alle Bilder mit den
Tags "Münster Kemperweg"und Haus, die das Wort "Dach" in der Caption haben und zwischen
dem 1.6.1995 und dem 30.1.1998 gemacht wurden.


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
