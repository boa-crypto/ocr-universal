"""Transport Baidu interne : réponses bornées, pas redirections ni diagnostic brut."""
from __future__ import annotations

import json

TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_TOKEN_CHARS = 8192
MAX_WORDS = 10_000


def post_json(url: str, *, params: dict, data: dict | None = None, read_timeout: int) -> dict:
    """Les exceptions restent internes : l'adaptateur renvoie un message constant."""
    import requests

    if url not in (TOKEN_URL, OCR_URL):
        raise ValueError("endpoint refusé")
    with requests.post(url, params=params, data=data, timeout=(5, read_timeout),
                       allow_redirects=False, verify=True, stream=True) as response:
        if response.status_code != 200:
            raise ValueError("statut HTTP refusé")
        content = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            if len(content) + len(chunk) > MAX_RESPONSE_BYTES:
                raise ValueError("réponse trop grande")
            content.extend(chunk)
        result = json.loads(content.decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("objet JSON requis")
        return result
