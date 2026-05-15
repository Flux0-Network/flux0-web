import discord
from discord.ext import commands
import sqlite3
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
ROLE_ID = 1459177962707484723

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(intents=intents)

conn = sqlite3.connect("accounts.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    discord_id TEXT PRIMARY KEY,
    account_id TEXT,
    code TEXT,
    verified INTEGER DEFAULT 0,
    created_at TEXT
)
""")
conn.commit()


class CodeModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Code eingeben")
        self.code = discord.ui.InputText(label="Dein Code", placeholder="ABC123", required=True)
        self.add_item(self.code)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        entered_code = self.code.value.upper()
        cursor.execute("SELECT code, verified FROM users WHERE discord_id = ?", (user_id,))
        result = cursor.fetchone()
        if not result:
            await interaction.response.send_message("❌ Kein Account.", ephemeral=True)
            return
        saved_code, verified = result
        if verified:
            await interaction.response.send_message("✅ Schon verifiziert.", ephemeral=True)
            return
        if entered_code != saved_code:
            await interaction.response.send_message("❌ Falscher Code!", ephemeral=True)
            return
        cursor.execute("UPDATE users SET verified = 1 WHERE discord_id = ?", (user_id,))
        conn.commit()
        role = interaction.guild.get_role(ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
        await interaction.response.send_message("🎉 Erfolgreich verifiziert!", ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Code eingeben", style=discord.ButtonStyle.blurple, custom_id="VerifyView_enter_code")
    async def enter_code(self, button, interaction: discord.Interaction):
        await interaction.response.send_modal(CodeModal())


class AccountView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Account", style=discord.ButtonStyle.green, custom_id="create_account")
    async def create_account(self, button, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        cursor.execute("SELECT * FROM users WHERE discord_id = ?", (user_id,))
        if cursor.fetchone():
            await interaction.response.send_message("❌ Du hast bereits einen Account!", ephemeral=True)
            return
        account_id = str(uuid.uuid4())[:8]
        code = str(uuid.uuid4())[:6].upper()
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, 0, ?)", (user_id, account_id, code, str(datetime.utcnow())))
        conn.commit()
        try:
            await interaction.user.send(f"🔐 Dein Verifizierungs-Code:\n`{code}`")
            dm_status = "📩 Code wurde dir per DM geschickt!"
        except Exception:
            dm_status = "⚠️ Konnte dir keine DM schicken!"
        await interaction.response.send_message(f"✅ Account erstellt!\n{dm_status}\n\n➡️ Jetzt Code eingeben:", view=VerifyView(), ephemeral=True)

    @discord.ui.button(label="Code eingeben", style=discord.ButtonStyle.blurple, custom_id="CodeModal")
    async def enter_code(self, button, interaction: discord.Interaction):
        await interaction.response.send_modal(CodeModal())

    @discord.ui.button(label="🔄", style=discord.ButtonStyle.gray, custom_id="CodeResend")
    async def resend_code(self, button, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        cursor.execute("SELECT code FROM users WHERE discord_id=?", (user_id,))
        result = cursor.fetchone()
        if not result:
            await interaction.response.send_message("❌ Du hast keinen Account!", ephemeral=True)
            return
        code = result[0]
        try:
            await interaction.user.send(f"🔐 Dein Code: `{code}`")
            await interaction.response.send_message("📩 Code wurde dir erneut geschickt!", ephemeral=True)
        except Exception:
            await interaction.response.send_message("❌ Ich kann dir keine DM schicken!", ephemeral=True)


@bot.slash_command(description="Sendet den Account Button")
async def setup(ctx: discord.ApplicationContext):
    embed = discord.Embed(description=("# <:account:1474536531061379113> Account\n\n> Drück auf denn Button um dein Account zu erstellen.\n> -# Achtung: Aktiviere DMs, um den Code zu erhalten.\n"), color=0x36393F)
    await ctx.respond(embed=embed, view=AccountView())


@bot.slash_command(description="Zeigt deinen Account")
async def account(ctx: discord.ApplicationContext):
    cursor.execute("SELECT account_id, verified FROM users WHERE discord_id = ?", (str(ctx.user.id),))
    user = cursor.fetchone()
    if not user:
        await ctx.respond("❌ Kein Account.", ephemeral=True)
        return
    status = "✅ Verifiziert" if user[1] else "❌ Nicht verifiziert"
    await ctx.respond(f"🆔 ID: `{user[0]}`\n🔐 Status: {status}", ephemeral=True)


@bot.event
async def on_ready():
    bot.add_view(AccountView())
    bot.add_view(VerifyView())
    print(f"Bot online als {bot.user}")
    await bot.sync_commands()


for filename in os.listdir("./componente"):
    if filename.endswith(".py"):
        bot.load_extension(f"componente.{filename[:-3]}")

bot.run(TOKEN)
