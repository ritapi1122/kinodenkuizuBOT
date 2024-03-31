from discord.ext import commands
import random
import asyncio
import json
from collections import defaultdict
import time  # timeモジュールのインポート

# クイズのリストをファイルから読み込む
with open('data/quizzes.json', 'r', encoding='utf-8') as f:
    quizzes = json.load(f)

# クイズ出題中かどうかを管理する変数
is_quiz_running = False
# 参加者募集中かどうかを管理する変数
is_recruiting = False
# クイズをスキップするかどうかを管理する変数
skip_quiz_flag = False
# 各ユーザーの正解数を管理する辞書
correct_counts = defaultdict(int)
# 参加者リスト
participants_list = []

# クイズ出題関数
async def quiz_master(ctx, recruit=False):
    global is_quiz_running, participants_list, is_recruiting, skip_quiz_flag
    is_quiz_running = True
    correct_counts.clear()  # 正解数を初期化

    # required_correct_answers の初期化
    required_correct_answers = 3  # デフォルト値として先着3名まで正解者をカウント

    if recruit:
        is_recruiting = True
        participants_list = []
        await ctx.send("15秒間参加者を募集します。参加する方は「参加」と発言してください。")
        try:
            while is_recruiting:
                join_message = await ctx.bot.wait_for('message', timeout=15.0)
                if join_message.content == "参加" and join_message.author not in participants_list:
                    participants_list.append(join_message.author)
                    await ctx.send(f"{join_message.author.display_name}さんが参加しました。")
        except asyncio.TimeoutError:
            if is_recruiting:
                await ctx.send("参加受付が終了しました。")
        is_recruiting = False
        if not participants_list:
            await ctx.send("参加者がいません。クイズを終了します。")
            is_quiz_running = False
            return
        if len(participants_list) == 1:
            await ctx.send("1分間のタイムアタックモードを開始します。1分間にできるだけ多くの問題に正解してください。")
            start_time = time.time()  # 開始時刻を記録

        required_correct_answers = 1 if len(participants_list) <= 2 else 3  # 参加者が2人以下なら先着1名、3人以上なら先着3名まで正解者をカウント
    else:
        participants_list = []  # 自由参加の場合はリストを空にする

    if len(participants_list) == 1:
        selected_quizzes = random.sample(quizzes, len(quizzes))  # 全問題をランダムに選択
    else:
        selected_quizzes = random.sample(quizzes, min(10, len(quizzes)))  # ランダムに10問選択

    if len(participants_list) == 1: #基準時間の設定
        Reference_time =60
    else:
        Reference_time =20
    
    timeout = 60# タイムアタックの場合は60秒
    start_time = time.time()
    for i, quiz in enumerate(selected_quizzes, start=1):

        if len(participants_list) != 1:
            timeout = 20  # タイムアタック以外の場合クイズごとに初期化
            start_time = time.time() # タイムアタック以外の場合クイズごとに初期化
        

        if not is_quiz_running or skip_quiz_flag:
            skip_quiz_flag = False  # スキップフラグをリセット
            break  # クイズが強制終了された場合はループを抜ける(タイムアタックモードでのタイムアウトの場合もある)、またはスキップされた場合は待機を中断
        
        await ctx.send(f'クイズ{i}: {quiz["question"]}')
        correct_answers = 0
        correct_users = set()  # 各クイズごとに正解者を記録するセットを初期化

        def check(m):
            return m.channel == ctx.channel and (not participants_list or m.author in participants_list) and m.author not in correct_users

        while correct_answers < required_correct_answers and timeout > 0:
            try:
                # 経過時間を計算してtimeoutを更新
                elapsed_time = time.time() - start_time
                timeout = Reference_time - elapsed_time
                wait_for_message_task = asyncio.create_task(ctx.bot.wait_for('message', check=check, timeout=timeout))
                if timeout <= 0:
                    raise asyncio.TimeoutError  # タイムアウトを強制的に発生させる
                
                # wait_for_message_task = asyncio.create_task(ctx.bot.wait_for('message', check=check, timeout=timeout))
                done, pending = await asyncio.wait({wait_for_message_task}, return_when=asyncio.FIRST_COMPLETED)

                if not is_quiz_running or skip_quiz_flag:
                    skip_quiz_flag = False  # スキップフラグをリセット
                    break  # クイズが強制終了された場合、またはスキップされた場合は待機を中断

                if wait_for_message_task in done:
                    message = wait_for_message_task.result()
                    if message.content.lower() in [answer.lower() for answer in quiz["answers"]]:
                        correct_answers += 1
                        correct_users.add(message.author)
                        correct_counts[message.author] += 1
                        # リアクションを追加する処理を非同期で実行
                        asyncio.create_task(message.add_reaction("✅"))
                        if correct_answers >= required_correct_answers:
                            if len(participants_list) != 1: 
                                await asyncio.sleep(3)  # 必要な人数が正解したら3秒待機
                            break

                # タイムアウト処理
                if len(done) == 0:
                    raise asyncio.TimeoutError
                
            except asyncio.TimeoutError:
                if len(participants_list) == 1:
                    is_quiz_running = False # タイムアタックモードでのタイムアウト
                else:
                    if is_quiz_running:
                        if correct_answers < 1:
                            await ctx.send(f"時間切れです！正解は {quiz['answers']} でした。")
                break  # 制限時間が経過したら次のクイズへ

            # タスクが未完了の場合はキャンセル
            for task in pending:
                task.cancel()

    is_quiz_running = False
    # クイズ終了後、正解数を提示
    if len(participants_list) == 1:
        await ctx.send("タイムアタック終了！正解数は以下の通りです：")
    else:
        await ctx.send("クイズ終了！正解数は以下の通りです：")
    for user, count in correct_counts.items():
        await ctx.send(f"{user.mention}: {count}問正解")

def setup(bot):
    @bot.command(name='quizall')
    async def start_quiz_all(ctx):
        global is_recruiting
        if not is_quiz_running and not is_recruiting:
            await quiz_master(ctx, recruit=True)
        else:
            await ctx.send("既にクイズが進行中です。")

    @bot.command(name='quiz')
    async def start_quiz_free(ctx):
        if not is_quiz_running:
            await quiz_master(ctx, recruit=False)
        else:
            await ctx.send("既にクイズが進行中です。")

    @bot.command(name='endquiz')
    async def end_quiz(ctx):
        global is_quiz_running, is_recruiting
        if is_recruiting:
            is_recruiting = False
            await ctx.send("参加者の募集を強制終了しました。")
        if is_quiz_running:
            is_quiz_running = False
            await ctx.send("クイズが強制終了されました。結果発表までお待ちください。")
        else:
            await ctx.send("現在、クイズは進行中ではありません。")
    
    @bot.command(name='endsanka')
    async def end_recruit(ctx):
        global is_recruiting
        if is_recruiting:
            is_recruiting = False
            await ctx.send("参加受付を終了しました。")
        else:
            await ctx.send("現在、参加受付は行われていません。")
    
    @bot.command(name='skip')
    async def skip_quiz(ctx):
        global skip_quiz_flag, is_recruiting
        if is_recruiting:
            await ctx.send("参加者の募集中はスキップできません。")
        if is_quiz_running:
            if len(participants_list) == 1:
                skip_quiz_flag = True
                await ctx.send("現在のクイズをスキップしました。何か文字を送信してください。")
            else:
                await ctx.send("このモードではスキップできません。")
        else:
            await ctx.send("現在、クイズは進行中ではありません。")
