import pytest

pytest.importorskip("opentelemetry.exporter.otlp.proto.http.trace_exporter")

from app import tracing


def test_normalize_otlp_endpoint_appends_traces_path():
    assert tracing._normalize_otlp_endpoint(None) is None
    assert (
        tracing._normalize_otlp_endpoint("https://otlp.example")
        == "https://otlp.example/v1/traces"
    )
    assert (
        tracing._normalize_otlp_endpoint("https://otlp.example/v1/traces")
        == "https://otlp.example/v1/traces"
    )


def test_parse_otlp_headers_parses_key_value_pairs():
    assert tracing._parse_otlp_headers(None) is None
    parsed = tracing._parse_otlp_headers("Authorization=Bearer abc, X-Org=123")
    assert parsed == {"Authorization": "Bearer abc", "X-Org": "123"}
