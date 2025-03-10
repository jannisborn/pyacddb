from copy import deepcopy
from together import Together

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
Um diese Nachricht zu sehen, schreib `Help`.
Viel Spass!🥳
"""


class LLM:
    def __init__(
        self,
        token: str,
        task_prompt: str,
        model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        temperature: float = 0.7,
    ):
        self.token = token
        self.temperature = temperature
        self.task = task_prompt
        self.message_history = [{"role": "system", "content": task_prompt}]
        self.model = model
        self.client = Together(api_key=token)
        self.counter = 0

    def _add_to_message_history(self, role: str, content: str):
        self.message_history.append({"role": role, "content": content})

    def send_message(self, message: str, history: bool = True):
        # Add user's message to the conversation history.
        self._add_to_message_history("user", message)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.message_history,
            stream=True,
            temperature=self.temperature,
        )

        # Process and stream the response.
        response_content = ""
        self.counter += 1

        if not history:
            self.message_history = self.message_history[:-1]

        for token in response:
            delta = token.choices[0].delta.content
            # End token indicating the end of the response.
            if token.choices[0].finish_reason:
                if history:
                    self._add_to_message_history("assistant", response_content)
                break
            else:
                # Append content to message and stream it.
                response_content += delta
                yield delta

    def __call__(self, *args, **kwargs):
        response = self.send_message(*args, **kwargs)
        full_text = "".join([part for part in response])
        return full_text
