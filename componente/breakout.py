import discord
from discord.ext import commands, tasks
import sqlite3
import aiohttp
from datetime import datetime, timedelta

COINGECKO_IDS = {
    "ada":   "cardano",
    "btc":   "bitcoin",
    "eth":   "ethereum",
    "sol":   "solana",
    "bnb":   "binancecoin",
    "xrp":   "ripple",
    "doge":  "dogecoin",
    "dot":   "polkadot",
    "avax":  "avalanche-2",
    "matic": "matic-network",
    "link":  "chainlink",
    "uni":   "uniswap",
    "ltc":   "litecoin",
    "atom":  "cosmos",
    "algo":  "algorand",
    "near":  "near",
    "ftm":   "fantom",
    "sand":  "the-sandbox",
    "mana":  "decentraland",
}

COOLDOWN_MINUTES = 60
CHECK_INTERVAL   = 5   # minutes between price checks


def get_db():
    conn = sqlite3.connect("accounts.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS breakout_config (
            guild_id   TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS breakout_tokens (
            guild_id     TEXT,
            symbol       TEXT,
            threshold    REAL DEFAULT 3.0,
            last_alert   TEXT,
            PRIMARY KEY (guild_id, symbol)
        );
        CREATE TABLE IF NOT EXISTS breakout_prices (
            guild_id  TEXT,
            symbol    TEXT,
            high_24h  REAL,
            low_24h   REAL,
            price     REAL,
            checked   TEXT,
            PRIMARY KEY (guild_id, symbol)
        );
    """)
    conn.commit()
    conn.close()


class Breakout(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()
        self.check_prices.start()

    def cog_unload(self):
        self.check_prices.cancel()

    # ──────────────────────────────────────────────
    # Slash Commands
    # ──────────────────────────────────────────────

    breakout = discord.SlashCommandGroup("breakout", "Breakout-Benachrichtigungen")

    @breakout.command(description="Setzt den Channel für Breakout-Alerts")
    @commands.has_permissions(manage_guild=True)
    async def setup(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Alert-Channel"),
    ):
        conn = get_db()
        conn.execute(
            "INSERT INTO breakout_config VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id",
            (str(ctx.guild_id), str(channel.id)),
        )
        conn.commit()
        conn.close()
        await ctx.respond(f"✅ Breakout-Alerts werden in {channel.mention} gesendet.", ephemeral=True)

    @breakout.command(description="Fügt einen Token zur Watchlist hinzu")
    @commands.has_permissions(manage_guild=True)
    async def add(
        self,
        ctx: discord.ApplicationContext,
        token: discord.Option(str, "Token-Symbol (z.B. ada, btc, eth)"),
        threshold: discord.Option(float, "Breakout-Schwelle in % (Standard: 3.0)", required=False, default=3.0),
    ):
        symbol = token.lower()
        if symbol not in COINGECKO_IDS:
            supported = ", ".join(f"`{k}`" for k in sorted(COINGECKO_IDS))
            await ctx.respond(
                f"❌ Unbekannter Token `{symbol}`.\nUnterstützt: {supported}",
                ephemeral=True,
            )
            return

        conn = get_db()
        conn.execute(
            "INSERT INTO breakout_tokens (guild_id, symbol, threshold) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, symbol) DO UPDATE SET threshold = excluded.threshold",
            (str(ctx.guild_id), symbol, threshold),
        )
        conn.commit()
        conn.close()
        await ctx.respond(
            f"✅ **{symbol.upper()}** zur Watchlist hinzugefügt (Schwelle: ±{threshold}%).",
            ephemeral=True,
        )

    @breakout.command(description="Entfernt einen Token von der Watchlist")
    @commands.has_permissions(manage_guild=True)
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        token: discord.Option(str, "Token-Symbol"),
    ):
        symbol = token.lower()
        conn = get_db()
        conn.execute(
            "DELETE FROM breakout_tokens WHERE guild_id = ? AND symbol = ?",
            (str(ctx.guild_id), symbol),
        )
        conn.commit()
        conn.close()
        await ctx.respond(f"🗑️ **{symbol.upper()}** von der Watchlist entfernt.", ephemeral=True)

    @breakout.command(description="Zeigt alle überwachten Token")
    async def list(self, ctx: discord.ApplicationContext):
        conn = get_db()
        rows = conn.execute(
            "SELECT symbol, threshold FROM breakout_tokens WHERE guild_id = ?",
            (str(ctx.guild_id),),
        ).fetchall()
        config = conn.execute(
            "SELECT channel_id FROM breakout_config WHERE guild_id = ?",
            (str(ctx.guild_id),),
        ).fetchone()
        conn.close()

        if not rows:
            await ctx.respond("📭 Keine Token auf der Watchlist.", ephemeral=True)
            return

        channel_mention = (
            f"<#{config['channel_id']}>" if config else "⚠️ Kein Channel gesetzt (`/breakout setup`)"
        )

        lines = "\n".join(f"• **{r['symbol'].upper()}** — Schwelle: ±{r['threshold']}%" for r in rows)
        embed = discord.Embed(
            title="📊 Breakout Watchlist",
            description=lines,
            color=0x5865F2,
        )
        embed.add_field(name="Alert-Channel", value=channel_mention)
        await ctx.respond(embed=embed, ephemeral=True)

    @breakout.command(description="Zeigt den aktuellen Preis eines Tokens")
    async def price(
        self,
        ctx: discord.ApplicationContext,
        token: discord.Option(str, "Token-Symbol (z.B. ada, btc)"),
    ):
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
        color = 0x57F287 if change >= 0 else 0xED4245
        arrow = "📈" if change >= 0 else "📉"

        embed = discord.Embed(title=f"{arrow} {symbol.upper()}", color=color)
        embed.add_field(name="Preis",      value=f"${d['usd']:,.4f}")
        embed.add_field(name="24h Change", value=f"{change:+.2f}%")
        embed.add_field(name="24h High",   value=f"${d.get('usd_24h_high', '—'):,.4f}" if d.get('usd_24h_high') else "—")
        embed.add_field(name="24h Low",    value=f"${d.get('usd_24h_low', '—'):,.4f}" if d.get('usd_24h_low') else "—")
        embed.set_footer(text="Quelle: CoinGecko")
        await ctx.respond(embed=embed, ephemeral=True)

    # ──────────────────────────────────────────────
    # Background Task
    # ──────────────────────────────────────────────

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def check_prices(self):
        conn = get_db()
        guilds = conn.execute("SELECT guild_id, channel_id FROM breakout_config").fetchall()

        for guild_row in guilds:
            guild_id   = guild_row["guild_id"]
            channel_id = guild_row["channel_id"]

            tokens = conn.execute(
                "SELECT symbol, threshold, last_alert FROM breakout_tokens WHERE guild_id = ?",
                (guild_id,),
            ).fetchall()
            if not tokens:
                continue

            symbols  = [t["symbol"] for t in tokens]
            price_data = await self._fetch_prices(symbols)
            if not price_data:
                continue

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                continue

            for token in tokens:
                symbol    = token["symbol"]
                threshold = token["threshold"]
                last_alert_str = token["last_alert"]

                if symbol not in price_data:
                    continue

                d          = price_data[symbol]
                price      = d.get("usd")
                high_24h   = d.get("usd_24h_high")
                low_24h    = d.get("usd_24h_low")
                change_24h = d.get("usd_24h_change") or 0

                if not price:
                    continue

                # Cooldown check
                if last_alert_str:
                    last_alert = datetime.fromisoformat(last_alert_str)
                    if datetime.utcnow() - last_alert < timedelta(minutes=COOLDOWN_MINUTES):
                        continue

                # Load previous snapshot
                prev = conn.execute(
                    "SELECT high_24h, low_24h FROM breakout_prices WHERE guild_id = ? AND symbol = ?",
                    (guild_id, symbol),
                ).fetchone()

                breakout_type = None

                if prev and prev["high_24h"] and prev["low_24h"]:
                    # Bullish breakout: price exceeded previous 24h high
                    if high_24h and price > prev["high_24h"]:
                        breakout_type = "bullish"
                    # Bearish breakout: price broke below previous 24h low
                    elif low_24h and price < prev["low_24h"]:
                        breakout_type = "bearish"

                # Fallback: 24h momentum exceeds threshold
                if not breakout_type and abs(change_24h) >= threshold:
                    breakout_type = "bullish" if change_24h > 0 else "bearish"

                # Save current snapshot
                conn.execute(
                    "INSERT INTO breakout_prices VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(guild_id, symbol) DO UPDATE SET "
                    "high_24h = excluded.high_24h, low_24h = excluded.low_24h, "
                    "price = excluded.price, checked = excluded.checked",
                    (guild_id, symbol, high_24h, low_24h, price, datetime.utcnow().isoformat()),
                )

                if breakout_type:
                    conn.execute(
                        "UPDATE breakout_tokens SET last_alert = ? WHERE guild_id = ? AND symbol = ?",
                        (datetime.utcnow().isoformat(), guild_id, symbol),
                    )
                    conn.commit()
                    await self._send_alert(channel, symbol, price, high_24h, low_24h, change_24h, breakout_type)

        conn.commit()
        conn.close()

    @check_prices.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    async def _fetch_prices(self, symbols: list[str]) -> dict | None:
        ids = ",".join(COINGECKO_IDS[s] for s in symbols if s in COINGECKO_IDS)
        if not ids:
            return None

        url = (
            "https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids}"
            "&vs_currencies=usd"
            "&include_24hr_high=true"
            "&include_24hr_low=true"
            "&include_24hr_change=true"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return None
                    raw = await resp.json()
        except Exception:
            return None

        # Re-map CoinGecko IDs back to symbols
        id_to_symbol = {v: k for k, v in COINGECKO_IDS.items()}
        return {id_to_symbol[cg_id]: data for cg_id, data in raw.items() if cg_id in id_to_symbol}

    async def _send_alert(
        self,
        channel: discord.TextChannel,
        symbol: str,
        price: float,
        high_24h: float | None,
        low_24h: float | None,
        change_24h: float,
        breakout_type: str,
    ):
        if breakout_type == "bullish":
            color  = 0x57F287
            emoji  = "🚀"
            title  = f"Bullish Breakout — {symbol.upper()}"
            desc   = f"**{symbol.upper()}** hat das 24h-Hoch gebrochen!"
        else:
            color  = 0xED4245
            emoji  = "📉"
            title  = f"Bearish Breakout — {symbol.upper()}"
            desc   = f"**{symbol.upper()}** hat das 24h-Tief gebrochen!"

        embed = discord.Embed(title=f"{emoji} {title}", description=desc, color=color)
        embed.add_field(name="Aktueller Preis", value=f"${price:,.4f}", inline=True)
        embed.add_field(name="24h Change",      value=f"{change_24h:+.2f}%",  inline=True)
        if high_24h:
            embed.add_field(name="24h High", value=f"${high_24h:,.4f}", inline=True)
        if low_24h:
            embed.add_field(name="24h Low",  value=f"${low_24h:,.4f}",  inline=True)
        embed.set_footer(text=f"Breakout erkannt • {datetime.utcnow().strftime('%H:%M UTC')}")

        await channel.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Breakout(bot))
