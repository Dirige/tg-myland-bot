import json
import os
from pathlib import Path

CONFIG_PATH = os.getenv('CONFIG_PATH', 'data/config.json')

def _load():
    path = Path(CONFIG_PATH)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}\n请复制 config.example.json 为 data/config.json 并填写配置")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

_cfg = _load()

BOT_TOKEN = _cfg.get('bot_token', '')
ADMIN_ID = _cfg.get('admin_id', 0)
NOTIFY_CHAT_ID = _cfg.get('notify_chat_id', 0)
CHECK_INTERVAL = _cfg.get('check_interval', 1800)
PROXY = _cfg.get('proxy', '')

GAME = _cfg.get('game', {})
BASE_URL = GAME.get('base_url', 'https://myland.somebyte.org')
USER_TOKEN = GAME.get('user_token', '')
PLAYER_ID = GAME.get('player_id', '')
MAP_ID = GAME.get('map_id', 11)
WHEAT_SEED_ID = GAME.get('wheat_seed_id', 1001)
SOW_QTY = GAME.get('sow_qty', 1)
STEAL_TIMEOUT = GAME.get('steal_timeout', 4)
MAX_STEAL = GAME.get('max_steal', 10)
