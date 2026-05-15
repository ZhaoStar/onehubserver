import subprocess
import hmac
import hashlib
import os
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "onehub-deploy-secret")
DEPLOY_SCRIPT = "/root/onehubserver/deploy.sh"

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()

    sig_header = request.headers.get("x-hub-signature-256", "")
    expected = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(sig_header, expected):
        raise HTTPException(403, "Invalid signature")

    event = request.headers.get("x-github-event")
    if event != "push":
        return {"message": f"Ignored event: {event}"}

    result = subprocess.run(["bash", DEPLOY_SCRIPT], capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webhook_server:app", host="0.0.0.0", port=8080)
