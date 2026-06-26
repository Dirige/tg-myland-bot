# 一亩三分地 Telegram Bot

自动农场助手：收获、播种、偷菜、定时执行

## 部署

### 1. 克隆项目

```bash
git clone <仓库地址>
cd tg-myland-bot
```

### 2. 创建配置文件

```bash
mkdir -p data
cp config.example.json data/config.json
```

编辑 `data/config.json`，填写你的 Bot Token、管理员 ID 和游戏账号信息：

```json
{
  "bot_token": "你的Bot Token",
  "admin_id": 你的Telegram ID,
  "notify_chat_id": 0,
  "check_interval": 1800,
  "proxy": "",
  "game": {
    "user_token": "游戏Token",
    "player_id": "玩家ID"
  }
}
```

### 3. 启动

```bash
docker compose up -d --build
```

### 4. 查看日志

```bash
docker logs -f tg-myland-bot
```

## 命令

| 命令 | 说明 |
|------|------|
| /status | 查看状态 |
| /farm | 全部执行（收获+播种+偷菜） |
| /harvest | 收获 |
| /plant | 播种 |
| /steal | 偷菜 |
| /pause | 暂停自动执行 |
| /resume | 恢复自动执行 |

## 配置说明

| 字段 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| bot_token | 是 | Bot Token | - |
| admin_id | 是 | 管理员 Telegram ID | - |
| notify_chat_id | 否 | 通知群 ID，有收获/偷菜时自动通知 | 0 |
| check_interval | 否 | 自动执行间隔（秒） | 1800 |
| proxy | 否 | 代理地址 | 空 |
| game.user_token | 是 | 游戏 Token | - |
| game.player_id | 是 | 玩家 ID | - |
| game.map_id | 否 | 地图 ID | 11 |
| game.max_steal | 否 | 单次最大偷菜数 | 10 |

## 许可证

MIT License
