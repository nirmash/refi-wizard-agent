#!/usr/bin/env python3
"""One-time device code login. Run on Embr via: embr shell → python3 login.py
Caches a refresh token that the app uses for automatic token renewal (~90 days)."""

import os
import json
import msal

TENANT_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"
CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Azure CLI public client
SCOPES = ["https://ai.azure.com/.default"]
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache.json")

cache = msal.SerializableTokenCache()
if os.path.exists(CACHE_PATH):
    cache.deserialize(open(CACHE_PATH).read())

app = msal.PublicClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    token_cache=cache,
)

# Check if we already have a valid token
accounts = app.get_accounts()
if accounts:
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        print(f"✓ Already authenticated as {accounts[0]['username']}")
        print(f"  Token valid. No action needed.")
        with open(CACHE_PATH, "w") as f:
            f.write(cache.serialize())
        exit(0)

# Start device code flow
flow = app.initiate_device_flow(scopes=SCOPES)
if "user_code" not in flow:
    raise RuntimeError(f"Device flow failed: {json.dumps(flow, indent=2)}")

print(flow["message"])  # "Go to https://microsoft.com/devicelogin and enter code ..."
print()

result = app.acquire_token_by_device_flow(flow)
if "access_token" in result:
    with open(CACHE_PATH, "w") as f:
        f.write(cache.serialize())
    print(f"\n✓ Logged in as {result.get('id_token_claims', {}).get('preferred_username', 'unknown')}")
    print(f"  Token cached at {CACHE_PATH}")
    print(f"  Refresh token will auto-renew for ~90 days.")
    print(f"\n  Now restart gunicorn: kill -HUP $(pgrep -f 'gunicorn.*app:app' | head -1)")
else:
    print(f"\n✗ Login failed: {result.get('error_description', result)}")
    exit(1)
