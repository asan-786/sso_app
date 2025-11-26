from html import escape
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import json
import re
from typing import List, Tuple, Optional

REDIRECT_SPLIT_PATTERN = re.compile(r"[,\s]+")

def append_query_params_to_url(base_url: str, params: dict) -> str:
    parsed = urlparse(base_url)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        if value is not None:
            existing[key] = value
    new_query = urlencode(existing)
    return urlunparse(parsed._replace(query=new_query))

def parse_redirect_entries(raw: Optional[str]) -> List[str]:
    """Return list of distinct redirect URLs from stored field."""
    if raw is None:
        return []

    entries: List[str] = []

    if isinstance(raw, list):
        for item in raw:
            item_str = str(item).strip()
            if item_str:
                entries.append(item_str)
        return entries

    raw_str = str(raw).strip()
    if not raw_str:
        return []

    # Attempt JSON decoding first to support stored lists
    try:
        parsed = json.loads(raw_str)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(parsed, str):
            raw_str = parsed.strip()
    except json.JSONDecodeError:
        pass

    normalized = raw_str.replace("\r", "\n")
    for part in REDIRECT_SPLIT_PATTERN.split(normalized):
        value = part.strip()
        if value:
            entries.append(value)

    if not entries:
        entries.append(raw_str)
    return entries

def serialize_redirect_entries(entries: List[str]) -> str:
    """Normalize redirect entries into newline-delimited string."""
    seen: List[str] = []
    for entry in entries:
        entry_str = str(entry).strip()
        if entry_str and entry_str not in seen:
            seen.append(entry_str)
    return "\n".join(seen)


def normalize_redirect_field(raw: Optional[str]) -> str:
    return serialize_redirect_entries(parse_redirect_entries(raw))

def normalize_scopes(scope_str: Optional[str]) -> List[str]:
    if not scope_str:
        return []
    normalized = set()
    for part in scope_str.replace(",", " ").split():
        slug = part.strip().lower()
        if slug:
            normalized.add(slug)
    return sorted(normalized)

def scopes_to_string(scopes: List[str]) -> str:
    return " ".join(sorted({scope.strip().lower() for scope in scopes if scope}))

def normalize_url_for_validation(url: str) -> Optional[tuple]:
    """Return (scheme, netloc, path) for comparison. Path has no trailing slash."""
    if not url:
        return None
    
    # The hash fragment (#) should not be considered part of the URI for validation.
    if '#' in url:
        url = url.split('#')[0]

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    path = parsed.path or ""
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")
    return parsed.scheme, parsed.netloc, path

def urls_match(url_a: Optional[str], url_b: Optional[str]) -> bool:
    if not url_a or not url_b:
        return url_a == url_b
    return normalize_url_for_validation(url_a) == normalize_url_for_validation(url_b)

def is_redirect_allowed(redirect_uri: str, allowed_url: Optional[str]) -> bool:
    if not allowed_url:
        return True
    allowed_norm = normalize_url_for_validation(allowed_url)
    incoming_norm = normalize_url_for_validation(redirect_uri)
    if not allowed_norm or not incoming_norm:
        return False
    allowed_scheme, allowed_netloc, allowed_path = allowed_norm
    inc_scheme, inc_netloc, inc_path = incoming_norm
    if allowed_scheme != inc_scheme or allowed_netloc != inc_netloc:
        return False
    if allowed_path and not inc_path.startswith(allowed_path):
        return False
    return True


def get_allowed_redirects_for_app(application: dict) -> List[str]:
    redirects = parse_redirect_entries(application.get("redirect_url"))
    if not redirects and application.get("url"):
        redirects.append(application["url"])
    return redirects

def build_consent_page(consent_token: str, app_name: str, scopes: List[str]) -> str:
    scope_items = "".join(
        f"<li class='flex items-center gap-2 text-gray-700'><span class='w-2 h-2 bg-indigo-500 rounded-full'></span>{scope.replace('_', ' ').replace('-', ' ').title()}</li>"
        for scope in scopes
    )
    safe_token = escape(consent_token)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Authorize Access</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center">
        <div class="bg-white rounded-2xl shadow-xl p-10 max-w-lg w-full">
            <h1 class="text-2xl font-bold text-gray-900 mb-2">Authorize {app_name}</h1>
            <p class="text-gray-600 mb-4">
                This application is requesting access to the following information from your SSO profile:
            </p>
            <ul class="space-y-2 mb-6">
                {scope_items}
            </ul>
            <p class="text-sm text-gray-500 mb-6">
                You can manage granted permissions later from your dashboard. Grant access?
            </p>
            <form method="POST" action="/consent/decision" class="flex flex-col gap-3">
                <input type="hidden" name="consent_token" value="{safe_token}" />
                <button type="submit" name="decision" value="approve" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-lg font-semibold transition">
                    Allow Access
                </button>
                <button name="decision" value="deny" class="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 py-3 rounded-lg font-semibold transition" type="submit">
                    Deny
                </button>
            </form>
        </div>
    </body>
    </html>
    """