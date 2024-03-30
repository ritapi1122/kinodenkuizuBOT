import discord
from discord.ext import commands
import json
from handlers import quiz_handler

# ボットの設定を読み込む
with open('config.json', 'r') as f:
    config = json.load(f)

# インテントの設定
intents = discord.Intents.default()
intents.messages = True  # メッセージイベントを受け取るために必要
intents.message_content = True  # メッセージの内容を受け取るために必要 (Discord.py v2.0以降)

# ボットのインスタンスを作成
bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

# コマンド実行前にメッセージを削除する処理
async def delete_command_message(ctx):
    try:
        await ctx.message.delete()
    except discord.errors.NotFound:
        pass  # メッセージがすでに削除されている場合は無視

# コマンド実行前後のフックを設定
bot.before_invoke(delete_command_message)
bot.after_invoke(delete_command_message)

# クイズハンドラーを追加
quiz_handler.setup(bot)

# ボットの起動
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(config['token'])