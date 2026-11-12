"""
El Compa Chambeador 🌮 - asistente IA autónomo (servidor Python)
Ejecuta:  python server.py   y abre  http://localhost:5000
Requiere la variable de entorno ANTHROPIC_API_KEY.
"""
import json
import os
import subprocess
import sys
import tempfile

import anthropic
from flask import Flask, Response, request, send_from_directory

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
# Permite que la IA ejecute código Python en tu equipo (modo agente). Actívalo solo si confías en el entorno.
ALLOW_EXEC = os.getenv("ALLOW_CODE_EXEC", "0") == "1"
MAX_STEPS = 8  # máximo de vueltas del bucle autónomo

client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY
app = Flask(__name__, static_folder=".", static_url_path="")

BASE = ("Te llamas 'El Compa Chambeador'. Responde siempre en el idioma del usuario (por defecto español). "
        "Habla con un tono amigable, cercano y con un ligero toque de humor mexicano (un 'compa', un 'ahorita lo checamos'), "
        "sin exagerar ni volverlo caricatura. La precisión técnica y la exactitud van primero: el código, los cálculos "
        "y las respuestas de examen deben ser correctos y claros. Sé honesto; si no sabes algo, dilo.")
MODES = {
    "general": BASE + " Eres un asistente general: respondes preguntas, explicas, redactas y razonas paso a paso.",
    "programador": BASE + " Eres un ingeniero de software senior. Escribe código completo, correcto y comentado, "
                          "con bloques de código con el lenguaje indicado. Explica brevemente cómo ejecutarlo y señala casos límite.",
    "examen": BASE + " Eres un tutor que resuelve exámenes y problemas. Para cada pregunta: da la respuesta final de forma "
                     "visible y luego una explicación breve del razonamiento. En opción múltiple indica la letra correcta y por qué "
                     "las demás son incorrectas. Si el enunciado es ambiguo, dilo y da la interpretación más probable.",
    "investigador": BASE + " Eres un investigador: busca información actual cuando haga falta, contrasta fuentes y cita de dónde viene cada dato.",
}

RUN_PYTHON = {
    "name": "run_python",
    "description": "Ejecuta código Python 3 y devuelve stdout/stderr. Úsalo para calcular, probar código o verificar resultados.",
    "input_schema": {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Código Python completo a ejecutar"}},
        "required": ["code"],
    },
}
WEB_SEARCH = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


def run_python(code: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "main.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=20, cwd=d)
            out = (r.stdout + r.stderr).strip() or "(sin salida)"
        except subprocess.TimeoutExpired:
            out = "Error: el código tardó más de 20 s y fue detenido."
    return out[-6000:]


def sse(kind: str, **data) -> str:
    return f"data: {json.dumps({'type': kind, **data}, ensure_ascii=False)}\n\n"


@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/api/config")
def config():
    return {"model": MODEL, "exec": ALLOW_EXEC}


@app.post("/api/chat")
def chat():
    body = request.get_json(force=True)
    messages = body.get("messages", [])
    system = MODES.get(body.get("mode", "general"), MODES["general"])
    tools = []
    if body.get("web"):
        tools.append(WEB_SEARCH)
    if body.get("agent") and ALLOW_EXEC:
        tools.append(RUN_PYTHON)
        system += " Puedes usar la herramienta run_python para verificar tu trabajo antes de responder."

    def generate():
        msgs = list(messages)
        try:
            for _ in range(MAX_STEPS):
                kwargs = dict(model=MODEL, max_tokens=4096, system=system, messages=msgs)
                if tools:
                    kwargs["tools"] = tools
                with client.messages.stream(**kwargs) as stream:
                    for t in stream.text_stream:
                        yield sse("text", text=t)
                    final = stream.get_final_message()

                msgs.append({"role": "assistant", "content": final.content})

                if final.stop_reason == "pause_turn":  # herramienta de servidor (búsqueda) en curso
                    continue
                if final.stop_reason != "tool_use":
                    break

                results = []
                for block in final.content:
                    if block.type == "tool_use" and block.name == "run_python":
                        yield sse("tool", name="run_python", code=block.input.get("code", ""))
                        out = run_python(block.input.get("code", ""))
                        yield sse("tool_result", output=out)
                        results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
                if not results:
                    break
                msgs.append({"role": "user", "content": results})
            yield sse("done")
        except Exception as e:  # noqa: BLE001
            yield sse("error", message=str(e))

    return Response(generate(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Falta ANTHROPIC_API_KEY. Defínela antes de ejecutar (ver README.md).")
    print(f"Abre http://localhost:5000  |  modelo: {MODEL}  |  ejecución de código: {'ON' if ALLOW_EXEC else 'OFF'}")
    app.run(host="127.0.0.1", port=5000, threaded=True)
