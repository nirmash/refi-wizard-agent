import os
import logging
from flask import Flask, render_template, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

ENDPOINT = os.environ.get(
    "AZURE_AI_ENDPOINT",
    "https://ai-nimashkowski7010ai130812469137.services.ai.azure.com/api/projects/ai-nimashkowski-agent-test",
)
AGENT_NAME = os.environ.get("AGENT_NAME", "refi-wizard")
AGENT_VERSION = os.environ.get("AGENT_VERSION", "2")


def _load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


def _get_openai_client():
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    from azure.ai.projects import AIProjectClient

    client_id = os.environ.get("AZURE_CLIENT_ID")
    if client_id:
        credential = ManagedIdentityCredential(client_id=client_id)
    else:
        credential = DefaultAzureCredential(
            exclude_shared_token_cache_credential=True,
            exclude_visual_studio_code_credential=True,
            exclude_powershell_credential=True,
            exclude_interactive_browser_credential=True,
        )
    project_client = AIProjectClient(endpoint=ENDPOINT, credential=credential)
    return project_client.get_openai_client()


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
