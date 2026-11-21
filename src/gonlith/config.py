# Gonlith 설정 로더: 패키지 기본값 위에 데이터 폴더의 config.toml을 덮어 읽고 데이터 폴더 위치를 정한다
import os
import tomllib
from importlib.resources import files
from pathlib import Path

from platformdirs import user_data_path

HOME_ENV = "GONLITH_HOME"
APP_NAME = "gonlith"
DEFAULTS_RESOURCE = "defaults.toml"
USER_CONFIG_FILE = "config.toml"


def data_home():
    configured = os.environ.get(HOME_ENV)
    return Path(configured).expanduser() if configured else user_data_path(APP_NAME)


def load_settings(home):
    settings = tomllib.loads(files("gonlith").joinpath(DEFAULTS_RESOURCE).read_text(encoding="utf-8"))
    user_file = Path(home) / USER_CONFIG_FILE
    if user_file.is_file():
        for section, values in tomllib.loads(user_file.read_text(encoding="utf-8")).items():
            settings.setdefault(section, {}).update(values)
    return settings
