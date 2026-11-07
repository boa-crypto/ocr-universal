"""Doubles HTTP uniquement, aucune clé réelle ni appel Baidu."""
import json
from dataclasses import asdict
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from PIL import Image

from unocr import baidu_http
from unocr.ocr_engines import BaiduOCREngine

KEY = "TEST65-KEY?x=1&y=2"
SECRET = "TEST65-SECRET&fake=value"
TOKEN = "TEST65-TOKEN+/=&value"
PRIVATE = "TEST65-PRIVATE-REMOTE"
NAMES = ["BAIDU_OCR_API_KEY", "BAIDU_API_KEY", "BAIDU_OCR_SECRET_KEY", "BAIDU_SECRET_KEY"]


class Response:
    def __init__(self, value=None, *, body=None, status=200, failure=None):
        self.body = body if body is not None else json.dumps(value).encode()
        self.status_code = status
        self.closed = False
        self.failure = failure

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def iter_content(self, chunk_size):
        if self.failure:
            raise self.failure
        for start in range(0, len(self.body), chunk_size):
            yield self.body[start:start + chunk_size]


@pytest.fixture
def transport(monkeypatch):
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(NAMES[0], KEY)
    monkeypatch.setenv(NAMES[2], SECRET)
    replies, calls = [], []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        assert replies, "appel HTTP supplémentaire non attendu"
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(requests, "post", post)
    return replies, calls


def recognize():
    return BaiduOCREngine().recognize(Image.new("RGBA", (50, 30), "white"), page_num=7)


def private_failure(output, caplog):
    assert not output.ok
    assert output.text == "" and output.words == [] and output.raw == {}
    exposed = json.dumps(asdict(output), ensure_ascii=False) + caplog.text
    for value in (KEY, SECRET, TOKEN, PRIVATE, "client_secret=", "access_token="):
        assert value not in exposed
    assert output.error.startswith("Baidu :")


def test_success_structured_encoding_tls_no_redirect_and_closed(transport):
    replies, calls = transport
    auth = Response({"access_token": TOKEN})
    ocr = Response({"words_result": [{"words": "Bonjour", "location": {
        "left": 1, "top": 2, "width": 10, "height": 5}}]})
    replies.extend([auth, ocr])
    output = recognize()
    assert output.ok and output.text == "Bonjour"
    assert output.words[0].page_num == 7
    assert output.words[0].bbox.x1 == 11
    assert auth.closed and ocr.closed
    assert [url for url, _ in calls] == [baidu_http.TOKEN_URL, baidu_http.OCR_URL]
    for url, kwargs in calls:
        assert "?" not in url
        assert kwargs["allow_redirects"] is False
        assert kwargs["verify"] is True and kwargs["stream"] is True
        encoded = requests.Request("POST", url, params=kwargs["params"]).prepare().url
        query = parse_qs(urlsplit(encoded).query)
        if url == baidu_http.TOKEN_URL:
            assert query["client_id"] == [KEY] and query["client_secret"] == [SECRET]
            assert kwargs["timeout"] == (5, 10)
        else:
            assert query["access_token"] == [TOKEN]
            assert kwargs["timeout"] == (5, 15)
            assert kwargs["data"]["image"]


@pytest.mark.parametrize("status", [301, 302, 307, 308, 400, 401, 403, 429, 500])
@pytest.mark.parametrize("phase", ["auth", "ocr"])
def test_http_error_or_redirect_never_becomes_success(transport, caplog, status, phase):
    replies, calls = transport
    bad = Response({"error_msg": PRIVATE, "access_token": TOKEN}, status=status)
    if phase == "ocr":
        replies.append(Response({"access_token": TOKEN}))
    replies.append(bad)
    private_failure(recognize(), caplog)
    assert bad.closed
    assert len(calls) == (1 if phase == "auth" else 2)


@pytest.mark.parametrize("error", [
    requests.Timeout(PRIVATE + SECRET), requests.ConnectionError(PRIVATE + KEY),
    ValueError(PRIVATE + TOKEN),
])
@pytest.mark.parametrize("phase", ["auth", "ocr"])
def test_exception_details_are_never_disclosed(transport, caplog, error, phase):
    replies, _ = transport
    if phase == "ocr":
        replies.append(Response({"access_token": TOKEN}))
    replies.append(error)
    private_failure(recognize(), caplog)


@pytest.mark.parametrize("payload", [
    {}, [], None, {"access_token": 12}, {"access_token": ""},
    {"access_token": "bad\nvalue"}, {"access_token": "é"},
    {"access_token": "x" * (baidu_http.MAX_TOKEN_CHARS + 1)},
    {"error": PRIVATE, "error_description": SECRET},
    {"error_code": 1, "access_token": TOKEN},
])
def test_invalid_auth_response_is_private_and_blocks_ocr(transport, caplog, payload):
    replies, calls = transport
    reply = Response(payload)
    replies.append(reply)
    private_failure(recognize(), caplog)
    assert reply.closed and len(calls) == 1


@pytest.mark.parametrize("payload", [
    None, [], {}, {"error_code": 17, "error_msg": PRIVATE + SECRET},
    {"error": PRIVATE}, {"words_result": None}, {"words_result": "wrong"},
    {"words_result": [PRIVATE]}, {"words_result": [{"words": {"private": TOKEN}}]},
    {"words_result": [{"words": "valid", "location": {"left": PRIVATE}}]},
])
def test_invalid_ocr_response_is_private_and_not_partial(transport, caplog, payload):
    replies, _ = transport
    replies.extend([Response({"access_token": TOKEN}), Response(payload)])
    private_failure(recognize(), caplog)


@pytest.mark.parametrize("phase", ["auth", "ocr"])
@pytest.mark.parametrize("body", [b'{"invalid":"TEST65-PRIVATE-REMOTE"', b'\xffTEST65-PRIVATE-REMOTE'])
def test_invalid_json_and_encoding_are_private(transport, caplog, phase, body):
    replies, _ = transport
    bad = Response(body=body)
    if phase == "ocr":
        replies.append(Response({"access_token": TOKEN}))
    replies.append(bad)
    private_failure(recognize(), caplog)
    assert bad.closed


@pytest.mark.parametrize("phase", ["auth", "ocr"])
def test_response_size_bounded_and_closed(transport, caplog, monkeypatch, phase):
    replies, _ = transport
    monkeypatch.setattr(baidu_http, "MAX_RESPONSE_BYTES", 100)
    bad = Response(body=b"x" * 101)
    if phase == "ocr":
        replies.append(Response({"access_token": TOKEN}))
    replies.append(bad)
    private_failure(recognize(), caplog)
    assert bad.closed


def test_stream_exception_is_private_and_closed(transport, caplog):
    replies, _ = transport
    bad = Response(failure=requests.ConnectionError(PRIVATE + SECRET))
    replies.append(bad)
    private_failure(recognize(), caplog)
    assert bad.closed


def test_word_count_bounded(transport, caplog, monkeypatch):
    monkeypatch.setattr(baidu_http, "MAX_WORDS", 1)
    replies, _ = transport
    replies.extend([Response({"access_token": TOKEN}), Response({"words_result": [
        {"words": "one"}, {"words": "two"}]})])
    private_failure(recognize(), caplog)


def test_missing_credentials_performs_no_request(transport, monkeypatch):
    _, calls = transport
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)
    assert not recognize().ok
    assert calls == []


def test_available_reason_cleared_after_configuration(transport, monkeypatch):
    engine = BaiduOCREngine()
    monkeypatch.delenv(NAMES[0])
    assert not engine.is_available()
    monkeypatch.setenv(NAMES[0], KEY)
    assert engine.is_available() and engine.unavailable_reason == ""


def test_unknown_endpoint_is_refused_before_request(transport):
    _, calls = transport
    with pytest.raises(ValueError, match="endpoint refusé"):
        baidu_http.post_json("https://example.org", params={}, read_timeout=10)
    assert calls == []


def test_missing_optional_dependency_blocks_availability(transport, monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "requests", None)
    engine = BaiduOCREngine()
    assert not engine.is_available()
    assert "unocr[baidu]" in engine.unavailable_reason
    assert transport[1] == []


def test_exception_string_is_never_evaluated(transport, caplog):
    class SensitiveException(Exception):
        def __str__(self):
            pytest.fail("conversion d'exception sensible interdite")

    transport[0].append(SensitiveException())
    private_failure(recognize(), caplog)


def test_legacy_environment_names_are_supported(transport, monkeypatch):
    monkeypatch.delenv(NAMES[0])
    monkeypatch.delenv(NAMES[2])
    monkeypatch.setenv(NAMES[1], KEY)
    monkeypatch.setenv(NAMES[3], SECRET)
    transport[0].extend([Response({"access_token": TOKEN}), Response({"words_result": []})])
    output = recognize()
    assert output.ok and output.text == "" and output.mean_confidence == 0
    assert transport[1][0][1]["params"]["client_secret"] == SECRET
