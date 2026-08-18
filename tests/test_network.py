import ssl

from playlist_builder.network import TLS12Adapter, create_requests_session


def test_requests_session_uses_tls_12_without_disabling_certificate_validation() -> None:
    session = create_requests_session()
    adapter = session.get_adapter("https://")

    assert isinstance(adapter, TLS12Adapter)
    assert adapter.ssl_context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert adapter.ssl_context.maximum_version == ssl.TLSVersion.TLSv1_2
    assert adapter.ssl_context.verify_mode == ssl.CERT_REQUIRED
