import os
import logging
import json
from openai import OpenAI
from flask import Flask, render_template, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

app = Flask(__name__)

ENDPOINT = os.environ.get(
    "AZURE_AI_ENDPOINT",
    "https://ai-nimashkowski7010ai130812469137.services.ai.azure.com/api/projects/ai-nimashkowski-agent-test",
)
API_KEY = os.environ.get("AZURE_AI_API_KEY", "")
AGENT_NAME = os.environ.get("AGENT_NAME", "refi-wizard")
AGENT_VERSION = os.environ.get("AGENT_VERSION", "5")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ── Database ─────────────────────────────────────────────────────────────────

SAMPLE_HOMES = [
    {"address": "742 Evergreen Terrace", "city": "Austin", "state": "TX", "price": 425000, "bedrooms": 3, "bathrooms": 2.0, "sqft": 1850, "description": "Charming single-story home with updated kitchen, hardwood floors, and a spacious backyard with mature trees."},
    {"address": "1200 Lakeview Dr", "city": "Denver", "state": "CO", "price": 310000, "bedrooms": 2, "bathrooms": 1.0, "sqft": 1200, "description": "Cozy mountain-view condo near downtown with open floor plan and in-unit laundry."},
    {"address": "88 Willow Creek Rd", "city": "Raleigh", "state": "NC", "price": 550000, "bedrooms": 4, "bathrooms": 3.0, "sqft": 2600, "description": "Spacious colonial with a two-car garage, finished basement, and large deck overlooking a wooded lot."},
    {"address": "455 Sunset Blvd", "city": "Phoenix", "state": "AZ", "price": 289000, "bedrooms": 2, "bathrooms": 2.0, "sqft": 1100, "description": "Modern desert retreat with solar panels, quartz countertops, and a community pool."},
    {"address": "33 Harbor Walk", "city": "Charleston", "state": "SC", "price": 675000, "bedrooms": 4, "bathrooms": 2.5, "sqft": 2200, "description": "Historic district gem with wraparound porch, exposed brick, and walking distance to waterfront."},
    {"address": "910 Pine Ridge Ct", "city": "Portland", "state": "OR", "price": 485000, "bedrooms": 3, "bathrooms": 2.0, "sqft": 1750, "description": "Craftsman bungalow with original built-ins, updated bathrooms, and a rain garden."},
    {"address": "2750 Prairie View Ln", "city": "Nashville", "state": "TN", "price": 365000, "bedrooms": 3, "bathrooms": 2.5, "sqft": 1900, "description": "New construction in growing neighborhood with open concept, smart home features, and energy-efficient appliances."},
    {"address": "18 Coral Bay Cir", "city": "Tampa", "state": "FL", "price": 520000, "bedrooms": 4, "bathrooms": 3.0, "sqft": 2400, "description": "Waterfront property with private dock, screened lanai, and a resort-style pool."},
]


def _get_db():
    """Return a database connection. Uses PostgreSQL if DATABASE_URL is set, else SQLite."""
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    else:
        import sqlite3
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "homes.db")
        return sqlite3.connect(db_path)


def _is_postgres():
    return bool(DATABASE_URL)


def _init_db():
    conn = _get_db()
    cur = conn.cursor()
    if _is_postgres():
        cur.execute("""
            CREATE TABLE IF NOT EXISTS homes (
                id SERIAL PRIMARY KEY,
                address VARCHAR(255), city VARCHAR(100), state VARCHAR(2),
                price INTEGER, bedrooms INTEGER, bathrooms REAL,
                sqft INTEGER, image_url TEXT, description TEXT
            )
        """)
        cur.execute("SELECT COUNT(*) FROM homes")
        count = cur.fetchone()[0]
        if count == 0:
            for i, h in enumerate(SAMPLE_HOMES):
                cur.execute(
                    "INSERT INTO homes (address, city, state, price, bedrooms, bathrooms, sqft, image_url, description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (h["address"], h["city"], h["state"], h["price"], h["bedrooms"], h["bathrooms"], h["sqft"],
                     f"https://picsum.photos/seed/house{i+1}/400/260", h["description"]),
                )
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS homes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT, city TEXT, state TEXT,
                price INTEGER, bedrooms INTEGER, bathrooms REAL,
                sqft INTEGER, image_url TEXT, description TEXT
            )
        """)
        cur.execute("SELECT COUNT(*) FROM homes")
        count = cur.fetchone()[0]
        if count == 0:
            for i, h in enumerate(SAMPLE_HOMES):
                cur.execute(
                    "INSERT INTO homes (address, city, state, price, bedrooms, bathrooms, sqft, image_url, description) VALUES (?,?,?,?,?,?,?,?,?)",
                    (h["address"], h["city"], h["state"], h["price"], h["bedrooms"], h["bathrooms"], h["sqft"],
                     f"https://picsum.photos/seed/house{i+1}/400/260", h["description"]),
                )
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database initialized with %d homes", max(count, len(SAMPLE_HOMES)))


_init_db()


def _fetch_homes():
    conn = _get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, address, city, state, price, bedrooms, bathrooms, sqft, image_url, description FROM homes ORDER BY id")
    cols = ["id", "address", "city", "state", "price", "bedrooms", "bathrooms", "sqft", "image_url", "description"]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def _fetch_home(home_id):
    conn = _get_db()
    cur = conn.cursor()
    ph = "%s" if _is_postgres() else "?"
    cur.execute(f"SELECT id, address, city, state, price, bedrooms, bathrooms, sqft, image_url, description FROM homes WHERE id = {ph}", (home_id,))
    cols = ["id", "address", "city", "state", "price", "bedrooms", "bathrooms", "sqft", "image_url", "description"]
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(zip(cols, row)) if row else None


# ── OpenAI ───────────────────────────────────────────────────────────────────

def _get_openai_client():
    return OpenAI(
        api_key="placeholder",
        base_url=ENDPOINT.rstrip("/") + "/openai/v1/",
        default_headers={"api-key": API_KEY},
    )


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/homes")
def api_homes():
    return jsonify(_fetch_homes())


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    home_id = data.get("home_id")
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    messages = []

    if home_id:
        home = _fetch_home(home_id)
        if home:
            context = (
                f"[Context: The user is looking at this property: {home['address']}, {home['city']} {home['state']} — "
                f"${home['price']:,}, {home['bedrooms']} bed/{home['bathrooms']} bath, {home['sqft']:,} sqft. "
                f"{home['description']}. Help them with financing options for this specific home.]\n\n"
            )
            user_message = context + user_message

    messages.append({"role": "user", "content": user_message})

    try:
        openai_client = _get_openai_client()
        response = openai_client.responses.create(
            input=messages,
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
