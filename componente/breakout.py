import discord
from discord.ext import commands, tasks
import sqlite3
import aiohttp
from datetime import datetime, timedelta

COINGECKO_IDS = {
    "ada": "cardano", "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
    "bnb": "binancecoin", "xrp": "ripple", "doge": "dogecoin", "dot": "polkadot",
    "avax": "avalanche-2", "matic": "matic-network", "link": "chainlink",
    "uni": "uniswap", "ltc": "litecoin", "atom": "cosmos", "algo": "algorand",
    "near": "near", "ftm": "fantom", "sand": "the-sandbox", "mana": "decentraland",
}

COOLDOWN_MINUTES = 60
CHECK_INTERVAL = 5


def get_db():
    conn = sqlite3.connect("accounts.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS breakout_config (guild_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS breakout_tokens (guild_id TEXT, symbol TEXT, threshold REAL DEFAULT 3.0, last_alert TEXT, PRIMARY KEY (guild_id, symbol));
        CREATE TABLE IF NOT EXISTS breakout_prices (guild_id TEXT, symbol TEXT, high_24h REAL, low_24h REAL, price REAL, checked TEXT, PRIMARY KEY (guild_id, symbol));
    """)
    conn.commit()
    conn.close()


class Breakout(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()
        self.check_prices.start()

    def cog_unload(self):
        self.check_prices.cancel()

    breakout = discord.SlashCommandGroup("breakout", "Breakout-Benachrichtigungen")

    @breakout.command(description="Setzt den Channel für Breakout-Alerts")
    @commands.has_permissions(manage_guild=True)
    async def setup(self, ctx, channel: discord.Option(discord.TextChannel, "Alert-Channel")):
        conn = get_db()
        conn.execute("INSERT INTO breakout_config VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id", (str(ctx.guild_id), str(channel.id)))
        conn.commit()
        conn.close()
        await ctx.respond(f"✅ Breakout-Alerts werden in {channel.mention} gesendet.", ephemeral=True)

    @breakout.command(description="Fügt einen Token zur Watchlist hinzu")
    @commands.has_permissions(manage_guild=True)
    async def add(self, ctx, token: discord.Option(str, "Token-Symbol"), threshold: discord.Option(float, "Schwelle in %", required=False, default=3.0)):
        symbol = token.lower()
        if symbol not in COINGECKO_IDS:
            await ctx.respond(f"❌ Unbekannter Token `{symbol}`.", ephemeral=True)
            return
        conn = get_db()
        conn.execute("INSERT INTO breakout_tokens (guild_id, symbol, threshold) VALUES (?, ?, ?) ON CONFLICT(guild_id, symbol) DO UPDATE SET threshold = excluded.threshold", (str(ctx.guild_id), symbol, threshold))
        conn.commit()
        conn.close()
        await ctx.respond(f"✅ **{symbol.upper()}** hinzugefügt (±{threshold}%).", ephemeral=True)

    @breakout.command(description="Entfernt einen Token von der Watchlist")
    @commands.has_permissions(manage_guild=True)
    async def remove(self, ctx, token: discord.Option(str, "Token-Symbol")):
        conn = get_db()
        conn.execute("DELETE FROM breakout_tokens WHERE guild_id = ? AND symbol = ?", (str(ctx.guild_id), token.lower()))
        conn.commit()
        conn.close()
        await ctx.respond(f"🗑️ **{token.upper()}** entfernt.", ephemeral=True)

    @breakout.command(description="Zeigt alle überwachten Token")
    async def list(self, ctx):
        conn = get_db()
        rows = conn.execute("SELECT symbol, threshold FROM breakout_tokens WHERE guild_id = ?", (str(ctx.guild_id),)).fetchall()
        config = conn.execute("SELECT channel_id FROM breakout_config WHERE guild_id = ?", (str(ctx.guild_id),)).fetchone()
        conn.close()
        if not rows:
            await ctx.respond("📭 Keine Token auf der Watchlist.", ephemeral=True)
            return
        lines = "\n".join(f"• **{r['symbol'].upper()}** — ±{r['threshold']}%" for r in rows)
        embed = discord.Embed(title="📊 Breakout Watchlist", description=lines, color=0x5865F2)
        embed.add_field(name="Alert-Channel", value=f"<#{config['channel_id']}>" if config else "⚠️ Kein Channel gesetzt")
        await ctx.respond(embed=embed, ephemeral=True)

    @breakout.command(description="Zeigt den aktuellen Preis eines Tokens")
    async def price(self, ctx, token: discord.Option(str, "Token-Symbol")):
        symbol = token.lower()
        if symbol not in COINGECKO_IDS:
            await ctx.respond(f"❌ Unbekannter Token `{symbol}`.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        data = await self._fetch_prices([symbol])
        if not data or symbol not in data:
            await ctx.respond("❌ Preis konnte nicht abgerufen werden.", ephemeral=True)
            return
        d = data[symbol]
        change = d.get("usd_24h_change", 0) or 0
        embed = discord.Embed(title=f"{'📈' if change >= 0 else '📉'} {symbol.upper()}", color=0x57F287 if change >= 0 else 0xED4245)
        embed.add_field(name="Preis", value=f"${d['usd']:,.4f}")
        embed.add_field(name="24h Change", value=f"{change:+.2f}%")
        embed.set_footer(text="Quelle: CoinGecko")
        await ctx.respond(embed=embed, ephemeral=True)

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def check_prices(self):
        conn = get_db()
        for guild_row in conn.execute("SELECT guild_id, channel_id FROM breakout_config").fetchall():
            guild_id, channel_id = guild_row["guild_id"], guild_row["channel_id"]
            tokens = conn.execute("SELECT symbol, threshold, last_alert FROM breakout_tokens WHERE guild_id = ?", (guild_id,)).fetchall()
            if not tokens:
                continue
            price_data = await self._fetch_prices([t["symbol"] for t in tokens])
            if not price_data:
                continue
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                continue
            for token in tokens:
                symbol, threshold, last_alert_str = token["symbol"], token["threshold"], token["last_alert"]
                if symbol not in price_data:
                    continue
                d = price_data[symbol]
                price, high_24h, low_24h = d.get("usd"), d.get("usd_24h_high"), d.get("usd_24h_low")
                change_24h = d.get("usd_24h_change") or 0
                if not price:
                    continue
                if last_alert_str and datetime.utcnow() - datetime.fromisoformat(last_alert_str) < timedelta(minutes=COOLDOWN_MINUTES):
                    continue
                prev = conn.execute("SELECT high_24h, low_24h FROM breakout_prices WHERE guild_id = ? AND symbol = ?", (guild_id, symbol)).fetchone()
                breakout_type = None
                if prev and prev["high_24h"] and prev["low_24h"]:
                    if high_24h and price > prev["high_24h"]:
                        breakout_type = "bullish"
                    elif low_24h and price < prev["low_24h"]:
                        breakout_type = "bearish"
                if not breakout_type and abs(change_24h) >= threshold:
                    breakout_type = "bullish" if change_24h > 0 else "bearish"
                conn.execute("INSERT INTO breakout_prices VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(guild_id, symbol) DO UPDATE SET high_24h=excluded.high_24h, low_24h=excluded.low_24h, price=excluded.price, checked=excluded.checked", (guild_id, symbol, high_24h, low_24h, price, datetime.utcnow().isoformat()))
                if breakout_type:
                    conn.execute("UPDATE breakout_tokens SET last_alert = ? WHERE guild_id = ? AND symbol = ?", (datetime.utcnow().isoformat(), guild_id, symbol))
                    conn.commit()
                    await self._send_alert(channel, symbol, price, high_24h, low_24h, change_24h, breakout_type)
        conn.commit()
        conn.close()

    @check_prices.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def _fetch_prices(self, symbols):
        ids = ",".join(COINGECKO_IDS[s] for s in symbols if s in COINGECKO_IDS)
        if not ids:
            return None
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_high=true&include_24hr_low=true&include_24hr_change=true"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return None
                    raw = await resp.json()
        except Exception:
            return None
        id_to_symbol = {v: k for k, v in COINGECKO_IDS.items()}
        return {id_to_symbol[cg_id]: data for cg_id, data in raw.items() if cg_id in id_to_symbol}

    async def _send_alert(self, channel, symbol, price, high_24h, low_24h, change_24h, breakout_type):
        if breakout_type == "bullish":
            color, emoji, title, desc = 0x57F287, "🚀", f"Bullish Breakout — {symbol.upper()}", f"**{symbol.upper()}** hat das 24h-Hoch gebrochen!"
        else:
            color, emoji, title, desc = 0xED4245, "📉", f"Bearish Breakout — {symbol.upper()}", f"**{symbol.upper()}** hat das 24h-Tief gebrochen!"
        embed = discord.Embed(title=f"{emoji} {title}", description=desc, color=color)
        embed.add_field(name="Preis", value=f"${price:,.4f}", inline=True)
        embed.add_field(name="24h Change", value=f"{change_24h:+.2f}%", inline=True)
        embed.set_footer(text=f"Breakout erkannt • {datetime.utcnow().strftime('%H:%M UTC')}")
        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Breakout(bot))
