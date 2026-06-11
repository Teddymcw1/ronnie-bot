from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import re

TOKEN = "8601584327:AAEPDoI_kqJYCclAsSudm_SOdrL1ETQPriI"

players = {}
pot = 0.0
stake = 5.0


# =========================
# PLAYER SYSTEM
# =========================
def get_player(user):
    if user.id not in players:
        players[user.id] = {
            "name": user.first_name,
            "bets": {},
            "wins": 0,
            "losses": 0,
            "profit": 0.0,
            "named": False
        }
    return players[user.id]


def set_nickname(user, name):
    players[user.id]["name"] = name
    players[user.id]["named"] = True


# =========================
# HELPERS
# =========================
def is_ronnie(text):
    return "ronnie" in text.lower()


def extract_round(text):
    match = re.search(r"\b(r1|r2|r3|l32|l16|qf|sf|f)\b", text.lower())
    return match.group(1).upper() if match else None


def extract_odds(text):
    match = re.search(r"@\s*([0-9]*\.?[0-9]+)", text)
    if match:
        return float(match.group(1))

    nums = re.findall(r"[0-9]*\.?[0-9]+", text)
    if nums:
        return float(nums[-1])

    return None


def detect_result(text):
    t = text.lower()
    if any(x in t for x in ["win", "won", "winner"]):
        return "win"
    if any(x in t for x in ["lose", "lost", "loser"]):
        return "lose"
    return None


# =========================
# NAME SYSTEM
# =========================
def extract_name(text):
    t = text.lower()
    t = re.sub(r"ronnie", "", t).strip()

    patterns = [
        r"my name is (.+)",
        r"name is (.+)",
        r"call me (.+)",
        r"i am (.+)",
        r"set name (.+)"
    ]

    for p in patterns:
        m = re.search(p, t)
        if m:
            return m.group(1).strip().title()

    return None


# =========================
# QUERY DETECTION
# =========================
def is_pot_query(text):
    t = text.lower()
    return any(x in t for x in [
        "pot", "session pot", "bank", "money", "cash",
        "what's the pot", "whats the pot", "how much"
    ])


def is_table_query(text):
    t = text.lower()
    return any(x in t for x in [
        "table", "leaderboard", "standings", "rank",
        "status", "who's winning", "who is winning", "how am i doing"
    ])


# =========================
# AVERAGE ODDS
# =========================
def calculate_avg_odds(player):
    odds = [b["odds"] for b in player["bets"].values()]
    return sum(odds) / len(odds) if odds else 0.0


# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_player(update.message.from_user)
    await update.message.reply_text("Ronnie Whelan online.")


# =========================
# MAIN HANDLER
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pot

    user = update.message.from_user
    text = update.message.text

    if not is_ronnie(text):
        return

    player = get_player(user)
    round_name = extract_round(text)

    # =========================
    # 1. NAME (TOP PRIORITY)
    # =========================
    name = extract_name(text)
    if name:
        set_nickname(user, name)
        await update.message.reply_text(f"🏷️ Name set: {name}")
        return

    # =========================
    # 2. RESULT
    # =========================
    result = detect_result(text)
    if result:

        if not round_name:
            await update.message.reply_text("Ronnie: couldn't detect round.")
            return

        if round_name not in player["bets"]:
            await update.message.reply_text("Ronnie: no bet found for that round.")
            return

        bet = player["bets"][round_name]

        if bet["result"] != "pending":
            await update.message.reply_text("Ronnie: result already recorded.")
            return

        total_return = bet["return"]
        profit = bet["profit"]

        if result == "win":
            bet["result"] = "win"
            player["wins"] += 1
            player["profit"] += profit
            pot += total_return

            await update.message.reply_text(f"✅ WIN {round_name} (+€{profit:.2f})")
            return

        if result == "lose":
            bet["result"] = "loss"
            player["losses"] += 1
            player["profit"] -= stake

            await update.message.reply_text(f"❌ LOSS {round_name}")
            return

    # =========================
    # 3. POT
    # =========================
    if is_pot_query(text):
        await update.message.reply_text(f"💰 💰 Session Pot: €{pot:.2f} 💰 💰")
        return

    # =========================
    # 4. TABLE
    # =========================
    if is_table_query(text):

        sorted_players = sorted(players.items(), key=lambda x: x[1]["profit"], reverse=True)

        msg = "📊 LEAGUE TABLE\n\n"
        pos = 1

        for _, p in sorted_players:
            avg_odds = calculate_avg_odds(p)

            msg += (
                f"{pos}. {p['name']}\n"
                f"🛥️ {p['wins']} | ⛔ {p['losses']} | 🎯 {avg_odds:.2f} | 💰 €{p['profit']:.2f}\n\n"
            )
            pos += 1

        await update.message.reply_text(msg)
        return

    # =========================
    # 5. BET
    # =========================
    if "@" in text.lower() or "bet" in text.lower() or "punt" in text.lower():

        if not round_name:
            await update.message.reply_text("Ronnie: couldn't detect round.")
            return

        odds = extract_odds(text)

        if odds is None:
            await update.message.reply_text("Ronnie: couldn't detect odds.")
            return

        total_return = stake * odds
        profit = total_return - stake

        player["bets"][round_name] = {
            "odds": odds,
            "stake": stake,
            "return": total_return,
            "profit": profit,
            "result": "pending"
        }

        await update.message.reply_text(
            f"📝 Bet logged\n{player['name']} | {round_name} | odds {odds}"
        )
        return

    # =========================
    # FALLBACK
    # =========================
    await update.message.reply_text("Ronnie: I didn't understand that.")


# =========================
# BOT SETUP
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Ronnie is running...")
app.run_polling()