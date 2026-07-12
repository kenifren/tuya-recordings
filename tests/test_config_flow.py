from types import SimpleNamespace

import pytest
from voluptuous_serialize import convert

from homeassistant.helpers import config_validation as cv

from custom_components.tuya_recordings.config_flow import (
    _options_schema,
    _user_schema,
    _validate_form_input,
)
from custom_components.tuya_recordings.const import CONF_MEDIA_STORAGE_PATH


def test_user_schema_is_frontend_serializable():
    converted = convert(_user_schema({}), custom_serializer=cv.custom_serializer)

    assert any(field["name"] == CONF_MEDIA_STORAGE_PATH for field in converted)


def test_options_schema_is_frontend_serializable():
    config_entry = SimpleNamespace(data={}, options={})

    converted = convert(_options_schema(config_entry), custom_serializer=cv.custom_serializer)

    assert any(field["name"] == CONF_MEDIA_STORAGE_PATH for field in converted)


def test_media_storage_path_validation_returns_field_error():
    errors = _validate_form_input({CONF_MEDIA_STORAGE_PATH: "/config/www/tuya_recordings"})

    assert errors == {CONF_MEDIA_STORAGE_PATH: "path_not_allowed"}


@pytest.mark.parametrize("path", ["/media/tuya_recordings", " /media/tuya_recordings "])
def test_media_storage_path_validation_normalizes_valid_path(path):
    user_input = {CONF_MEDIA_STORAGE_PATH: path}

    assert _validate_form_input(user_input) == {}
    assert user_input[CONF_MEDIA_STORAGE_PATH] == "/media/tuya_recordings"
