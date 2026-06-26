import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config
from farm import run_farm, check_status, get_chronicle, get_currency

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fmt_result(r, with_chronicle=False):
    lines = ["一亩三分地", "时间: " + r.game_time, ""]
    for l in r.lands:
        s = l["status"]
        p = f'{l["x"]},{l["y"]}'
        labels = {
            "harvestable": "可收获",
            "harvested": "已收获 已补种",
            "planted": "已播种",
            "growing": f'生长中 {l.get("remain_str", "?")}',
            "empty": "空地",
        }
        lines.append(f'{labels.get(s, s)} Land {l["id"]} ({p})')
    lines.append("")
    lines.append(f'粮食: {r.grain}  灵石: {r.stone}  种子: {r.seeds}')
    stats = []
    if r.harvested > 0: stats.append(f'收获:{r.harvested}({r.harvested_grain}粮食)')
    if r.planted > 0: stats.append(f'播种:{r.planted}')
    if r.stolen > 0: stats.append(f'偷菜:{r.stolen}({r.stolen_grain}粮食)')
    if r.stealable > 0: stats.append(f'可偷:{r.stealable}')
    if stats:
        lines.append("  ".join(stats))
    if r.errors:
        lines.append("错误: " + "; ".join(r.errors))
    if with_chronicle:
        chronicle = get_chronicle(3)
        if chronicle:
            lines.extend(["", "编年史"] + chronicle)
    return "\n".join(lines)

def fmt_no_op(action):
    grain, stone = get_currency()
    r = check_status()
    lines = [action, "", f'没有可{action.replace("执行", "")}的项目',
             f'粮食: {grain}  灵石: {stone}  种子: {r.seeds}']
    chronicle = get_chronicle(3)
    if chronicle:
        lines.extend(["", "编年史"] + chronicle)
    return "\n".join(lines)

KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("收获", callback_data="harvest"),
     InlineKeyboardButton("播种", callback_data="plant")],
    [InlineKeyboardButton("偷菜", callback_data="steal"),
     InlineKeyboardButton("状态", callback_data="status")],
    [InlineKeyboardButton("暂停", callback_data="pause"),
     InlineKeyboardButton("继续", callback_data="resume")],
])

HELP_TEXT = (
    "一亩三分地助手\n\n"
    "/status 查看状态\n"
    "/farm 全部执行\n"
    "/harvest 收获\n"
    "/plant 播种\n"
    "/steal 偷菜\n"
    "/pause 暂停自动\n"
    "/resume 恢复自动\n\n"
    f'每{config.CHECK_INTERVAL // 60}分钟自动执行'
)

ACTION_MAP = {
    "harvest": (True, True, False, "harvested", "收获"),
    "plant": (False, True, False, "planted", "播种"),
    "steal": (False, False, True, "stolen", "偷菜"),
}

def _is_admin(user_id):
    return user_id == config.ADMIN_ID

async def cmd_start(update, context):
    if not _is_admin(update.effective_user.id): return
    await update.message.reply_text(HELP_TEXT, reply_markup=KEYBOARD)

async def cmd_status(update, context):
    if not _is_admin(update.effective_user.id): return
    await update.message.reply_text(fmt_result(check_status(), True), reply_markup=KEYBOARD)

async def cmd_farm(update, context):
    if not _is_admin(update.effective_user.id): return
    r = run_farm(True, True, True)
    await update.message.reply_text(fmt_result(r, True), reply_markup=KEYBOARD)

async def cmd_harvest(update, context):
    if not _is_admin(update.effective_user.id): return
    r = run_farm(True, True, False)
    text = fmt_no_op("收获") if r.harvested == 0 else fmt_result(r, True)
    await update.message.reply_text(text, reply_markup=KEYBOARD)

async def cmd_plant(update, context):
    if not _is_admin(update.effective_user.id): return
    r = run_farm(False, True, False)
    text = fmt_no_op("播种") if r.planted == 0 else fmt_result(r, True)
    await update.message.reply_text(text, reply_markup=KEYBOARD)

async def cmd_steal(update, context):
    if not _is_admin(update.effective_user.id): return
    r = run_farm(False, False, True)
    text = fmt_no_op("偷菜") if r.stolen == 0 else fmt_result(r, True)
    await update.message.reply_text(text, reply_markup=KEYBOARD)

async def cmd_pause(update, context):
    if not _is_admin(update.effective_user.id): return
    context.bot_data["paused"] = True
    await update.message.reply_text("自动农场已暂停")

async def cmd_resume(update, context):
    if not _is_admin(update.effective_user.id): return
    context.bot_data["paused"] = False
    await update.message.reply_text("自动农场已恢复")

async def callback_handler(update, context):
    q = update.callback_query
    if not _is_admin(q.from_user.id):
        await q.answer()
        return
    data = q.data
    await q.answer()
    if data in ACTION_MAP:
        h, p, s, attr, label = ACTION_MAP[data]
        r = run_farm(h, p, s)
        text = fmt_no_op(label) if getattr(r, attr) == 0 else fmt_result(r, True)
        await q.edit_message_text(text, reply_markup=KEYBOARD)
    elif data == "status":
        await q.edit_message_text(fmt_result(check_status(), True), reply_markup=KEYBOARD)
    elif data == "pause":
        context.bot_data["paused"] = True
        await q.edit_message_text("自动农场已暂停")
    elif data == "resume":
        context.bot_data["paused"] = False
        await q.edit_message_text("自动农场已恢复")

async def auto_farm(context):
    if context.bot_data.get("paused", False): return
    r = run_farm(True, True, True)
    if r.harvested > 0 or r.stolen > 0:
        await context.bot.send_message(chat_id=config.NOTIFY_CHAT_ID, text=fmt_result(r, True), reply_markup=KEYBOARD)

def main():
    builder = Application.builder().token(config.BOT_TOKEN)
    if config.PROXY:
        builder = builder.proxy(config.PROXY).get_updates_proxy(config.PROXY)
    app = builder.build()
    for cmd, f in [('start', cmd_start), ('status', cmd_status), ('farm', cmd_farm),
                   ('harvest', cmd_harvest), ('plant', cmd_plant), ('steal', cmd_steal),
                   ('pause', cmd_pause), ('resume', cmd_resume)]:
        app.add_handler(CommandHandler(cmd, f))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.job_queue.run_repeating(auto_farm, interval=config.CHECK_INTERVAL, first=10)
    logger.info(f'MyLand Bot started, interval={config.CHECK_INTERVAL}s')
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
