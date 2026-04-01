import os
import logging
from openai import OpenAI
from flask import Flask, render_template, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

ENDPOINT = os.environ.get(
    "AZURE_AI_ENDPOINT",
    "https://ai-nimashkowski7010ai130812469137.services.ai.azure.com/api/projects/ai-nimashkowski-agent-test",
)
API_KEY = os.environ.get("AZURE_AI_API_KEY", "")
AGENT_NAME = os.environ.get("AGENT_NAME", "refi-wizard")
AGENT_VERSION = os.environ.get("AGENT_VERSION", "4")


def _get_openai_client():
    return OpenAI(
        api_key="placeholder",
        base_url=ENDPOINT.rstrip("/") + "/openai/v1/",
        default_headers={"api-key": API_KEY},
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    try:
        openai_client = _get_openai_client()
        response = openai_client.responses.create(
            input=[{"role": "user", "content": user_message}],
            extra_body={
                "agent_reference": {
                    "name": AGENT_NAME,
                    "version": AGENT_VERSION,
                    "type": "agent_reference",
                }
            },
        )
        return jsonify({"response": response.output_text})
    except Exception as exc:
        logger.exception("Chat request failed")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
