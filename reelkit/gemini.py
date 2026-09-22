"""One bounded Gemini request. No key ever enters an HTML file or a command argument."""
import json
import os
from datetime import date
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
from .core import ROOT, load, save

API = "https://generativelanguage.googleapis.com"
# Standard <=200k pricing verified 2026-09-21. Unknown models stop, never guess a rate.
RATES = {"gemini-3.1-pro-preview": (2.0, 12.0), "gemini-3.8-flash": (.75, 3.75)}
DEFAULT_MODEL = "gemini-3.8-flash"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Unexpected provider redirect. Refusing to forward the API key.")


def config():
    values = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
    values.update({k: os.environ[k] for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL") if os.environ.get(k)})
    key = values.get("GEMINI_API_KEY") or values.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("No Gemini API key. Run python3 reel.py setup-key, or set GEMINI_API_KEY in your environment.")
    model = values.get("GEMINI_MODEL", DEFAULT_MODEL)
    if model not in RATES:
        raise ValueError("This model has no verified price entry. Update RATES with current official pricing before using it.")
    if model == "gemini-3.8-flash" and date.today() > date(2026,12,31):
        raise ValueError("The verified promotional Flash rates expired. Recheck official pricing and update the rate entry before calling.")
    return key, model


def request(key, method, url, payload=None, headers=None, timeout=120):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "generativelanguage.googleapis.com":
        raise ValueError("Refusing to send the API key to a different host.")
    h = {"x-goog-api-key": key}
    h.update(headers or {})
    req = urllib.request.Request(url, data=payload, headers=h, method=method)
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=timeout) as response:
            return dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        # A provider error may echo content. Keep logs free of credentials/private prompts.
        raise RuntimeError(f"Gemini HTTP {exc.code}. Check key, model access, quota and provider status. No automatic retry.") from None


def json_request(key, endpoint, data, timeout=120):
    _, body = request(key, "POST", API + endpoint, json.dumps(data).encode(),
                      {"Content-Type": "application/json"}, timeout)
    return json.loads(body)


def analyze(path, prompt, ledger_path, budget=.5, allow_upload=False, max_output=8000):
    lock = Path(ledger_path).with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("Another provider request owns this project's budget. If a process crashed, confirm it stopped before removing api-usage.lock.") from None
    try:
        os.close(fd)
        return _analyze(path, prompt, ledger_path, budget, allow_upload, max_output)
    finally:
        lock.unlink(missing_ok=True)


def _analyze(path, prompt, ledger_path, budget=.5, allow_upload=False, max_output=8000):
    if not allow_upload:
        raise ValueError("This sends the selected video to Google. Use --allow-upload after confirming that exact footage may be shared with Gemini.")
    if not 0 < budget <= 10:
        raise ValueError("Set a positive project API budget up to $10.00.")
    key, model = config()
    rate_in, rate_out = RATES[model]
    path, ledger_path = Path(path), Path(ledger_path)
    if path.stat().st_size > 150 * 1024 * 1024:
        raise ValueError("Analysis proxy exceeds 150 MB; use a smaller proxy or split the recording.")
    ledger = load(ledger_path) if ledger_path.exists() else {"calls": [], "price_source": "https://ai.google.dev/gemini-api/docs/pricing"}
    spent = sum(c.get("accounted_usd", 0) for c in ledger["calls"])
    if spent >= budget:
        raise ValueError("Project API budget reached. No video uploaded.")
    info = None
    try:
        headers, _ = request(key, "POST", API + "/upload/v1beta/files",
                             json.dumps({"file": {"display_name": path.name}}).encode(),
                             {"Content-Type": "application/json", "X-Goog-Upload-Protocol": "resumable",
                              "X-Goog-Upload-Command": "start", "X-Goog-Upload-Header-Content-Type": "video/mp4",
                              "X-Goog-Upload-Header-Content-Length": str(path.stat().st_size)})
        upload_url = next(v for k, v in headers.items() if k.lower() == "x-goog-upload-url")
        _, body = request(key, "POST", upload_url, path.read_bytes(),
                          {"X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize"}, timeout=180)
        info = json.loads(body)["file"]
        deadline = time.monotonic() + 180
        while info.get("state") == "PROCESSING" and time.monotonic() < deadline:
            time.sleep(2)
            _, body = request(key, "GET", API + "/v1beta/" + info["name"])
            info = json.loads(body)
        if info.get("state") != "ACTIVE":
            raise RuntimeError("Gemini file processing did not complete. No inference request was sent.")
        contents = [{"role": "user", "parts": [{"file_data": {"mime_type": "video/mp4", "file_uri": info["uri"]}}, {"text": prompt}]}]
        counted = json_request(key, f"/v1beta/models/{model}:countTokens", {"contents": contents})
        tokens = int(counted["totalTokens"])
        if tokens > 200000:
            raise ValueError("This exceeds the verified pricing tier. Split the input.")
        ceiling = (tokens * rate_in + max_output * rate_out) / 1e6
        if spent + ceiling > budget:
            raise ValueError(f"Budget guard: this request reserves ${ceiling:.4f}; ${budget-spent:.4f} remains.")
        rec = {"model": model, "source": path.name, "input_tokens": tokens, "max_output_tokens": max_output,
               "accounted_usd": ceiling, "state": "reserved", "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        ledger["calls"].append(rec)
        save(ledger_path, ledger)
        print(f"Gemini: one request, maximum estimated token charge ${ceiling:.4f}.", flush=True)
        response = json_request(key, f"/v1beta/models/{model}:generateContent",
                                {"contents": contents, "generationConfig": {"responseMimeType": "application/json",
                                 "temperature": .1, "maxOutputTokens": max_output, "thinkingConfig": {"thinkingLevel": "low"}}}, timeout=600)
        # Keep the successful provider payload before parsing. These reports stay in ignored projects.
        raw_path = ledger_path.parent / "provider-responses" / (f"response-{len(ledger['calls']):03}.json")
        save(raw_path, response)
        rec["response_file"] = str(raw_path.relative_to(ledger_path.parent))
        usage = response.get("usageMetadata", {})
        rec["usage"] = usage
        if "promptTokenCount" in usage:
            rec["accounted_usd"] = (usage["promptTokenCount"] * rate_in +
                                    (usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)) * rate_out) / 1e6
        rec["state"] = "response_received"
        save(ledger_path, ledger)
        candidate = response.get("candidates", [{}])[0]
        if candidate.get("finishReason") != "STOP":
            raise RuntimeError("Gemini returned an incomplete response. Budget remains recorded; no automatic retry.")
        text = "".join(p.get("text", "") for p in candidate["content"]["parts"] if not p.get("thought"))
        result = json.loads(text)
        if isinstance(result, list) and len(result) == 1 and isinstance(result[0], dict):
            result = result[0]
        if not isinstance(result, dict):
            raise ValueError("Expected one JSON object from Gemini. Raw response saved locally; inspect it before paying for a new call.")
        rec["state"] = "complete"
        save(ledger_path, ledger)
        return result
    finally:
        if info and info.get("name"):
            try:
                request(key, "DELETE", API + "/v1beta/" + info["name"])
            except Exception:
                ledger.setdefault("cleanup_warnings", []).append({"file": info["name"], "note": "Temporary upload deletion was not confirmed; check Google Files API."})
                save(ledger_path, ledger)
                print("Warning: deletion of the temporary Google upload was not confirmed.", flush=True)
