from custom_components.tuya_recordings.lib.openapi import (
    TuyaOpenApiError,
    TuyaOpenApiClient,
    _normalize_mqtt_config,
    _normalize_webrtc_config,
    _sign,
)


def test_openapi_error_uses_tuya_code_and_message():
    error = TuyaOpenApiError("/v1/test", {"code": "NOPE", "msg": "bad"})

    assert "/v1/test: NOPE bad" == str(error)


def test_openapi_sign_uses_uppercase_hmac_sha256():
    assert _sign("payload", "secret") == "B82FCB791ACEC57859B989B430A826488CE2E479FDF92326BD0A2E8375A42BA4"


def test_normalize_webrtc_config_adds_legacy_keys_for_ipc_backend():
    config = _normalize_webrtc_config(
        {
            "auth": "auth",
            "moto_id": "moto",
            "p2p_type": 4,
            "protocol_version": "2.3",
            "support_webrtc_record": True,
            "supports_webrtc": True,
            "p2p_config": {"ices": [{"urls": "stun:example"}]},
        }
    )

    assert config["motoId"] == "moto"
    assert config["p2pType"] == 4
    assert config["protocolVersion"] == "2.3"
    assert config["supportWebrtcRecord"] is True
    assert config["supportsWebrtc"] is True
    assert config["p2pConfig"]["ices"] == [{"urls": "stun:example"}]


def test_normalize_mqtt_config_extracts_msid_from_source_topic():
    mqtt = _normalize_mqtt_config(
        {
            "client_id": "client",
            "username": "user",
            "password": "pass",
            "url": "ssl://m1.tuyaus.com:8883",
            "source_topic": {"ipc": "/av/u/source-id"},
            "sink_topic": {"ipc": "/av/moto/moto_id/u/{device_id}"},
        }
    )

    assert mqtt["msid"] == "source-id"
    assert mqtt["client_id"] == "client"
    assert mqtt["password"] == "pass"


def test_open_iot_hub_config_is_cached_until_expiry(monkeypatch):
    client = TuyaOpenApiClient(region="us", client_id="id", client_secret="secret", user_id="uid")
    calls = []

    def fake_post(path, body):
        calls.append((path, body))
        return {
            "client_id": "client",
            "username": "user",
            "password": "pass",
            "url": "ssl://m1.tuyaus.com:8883",
            "source_topic": {"ipc": "/av/u/source-id"},
            "sink_topic": {"ipc": "/av/moto/moto_id/u/{device_id}"},
            "expire_time": 3600,
        }

    monkeypatch.setattr(client, "post", fake_post)

    first = client.get_open_iot_hub_config()
    second = client.get_open_iot_hub_config()

    assert first["msid"] == "source-id"
    assert second["msid"] == "source-id"
    assert len(calls) == 1


def test_get_devices_accepts_list_result(monkeypatch):
    client = TuyaOpenApiClient(region="us", client_id="id", client_secret="secret", user_id="uid")
    monkeypatch.setattr(client, "get", lambda path: [{"id": "cam1"}, {"id": "cam2"}])

    devices = client.get_devices()

    assert devices == [{"id": "cam1"}, {"id": "cam2"}]


def test_get_devices_normalizes_wrapped_result(monkeypatch):
    client = TuyaOpenApiClient(region="us", client_id="id", client_secret="secret", user_id="uid")
    responses = [
        {"result": [{"id": "cam1", "name": "Camera 1"}]},
        {"list": [{"id": "cam2", "name": "Camera 2"}]},
        {"devices": [{"id": "cam3", "name": "Camera 3"}]},
    ]

    call = {"count": 0}

    def fake_get(path: str):
        idx = call["count"]
        if idx >= len(responses):
            return []
        call["count"] += 1
        return responses[idx]

    monkeypatch.setattr(client, "get", fake_get)

    assert client.get_devices() == [{"id": "cam1", "name": "Camera 1"}]
    assert client.get_devices() == [{"id": "cam2", "name": "Camera 2"}]
    assert client.get_devices() == [{"id": "cam3", "name": "Camera 3"}]
    assert client.get_devices() == []
