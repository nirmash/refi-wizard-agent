import os
import json
import logging
import msal
from openai import OpenAI
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

_TENANT_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"
_CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Azure CLI public client
_SCOPES = ["https://ai.azure.com/.default"]
_TOKEN_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".token_cache.json"
)

_msal_cache = msal.SerializableTokenCache()
if os.path.exists(_TOKEN_CACHE_PATH):
    _msal_cache.deserialize(open(_TOKEN_CACHE_PATH).read())

_msal_app = msal.PublicClientApplication(
    _CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{_TENANT_ID}",
    token_cache=_msal_cache,
)


def _save_cache():
    if _msal_cache.has_state_changed:
        with open(_TOKEN_CACHE_PATH, "w") as f:
            f.write(_msal_cache.serialize())


def _get_token():
    """Get a valid access token using cached refresh token from az CLI."""
    accounts = _msal_app.get_accounts()
    # Prefer microsoft.com account
    msft = [a for a in accounts if "microsoft.com" in a.get("username", "")]
    account = msft[0] if msft else (accounts[0] if accounts else None)
    if account:
        result = _msal_app.acquire_token_silent(_SCOPES, account=account, force_refresh=False)
        if result and "access_token" in result:
            _save_cache()
            return result["access_token"]
        logger.error("Token refresh failed: %s", result.get("error_description") if result else "no result")
    raise RuntimeError(
        "No cached credentials. Copy ~/.azure/msal_token_cache.json to .token_cache.json"
    )


def _get_openai_client():
    token = _get_token()
    return OpenAI(
        api_key=token,
        base_url=ENDPOINT.rstrip("/") + "/openai/v1/",
        default_headers={"User-Agent": "RefiWizard/1.0"},
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
