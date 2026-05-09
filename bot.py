import discord
from discord.ext import commands
import sqlite3

# ================= INTENTS =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.guilds = True
intents.invites = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DB =================
db = sqlite3.connect("bot.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    guild_id INTEGER,
    invites INTEGER DEFAULT 0,
    warns INTEGER DEFAULT 0,
    messages INTEGER DEFAULT 0,
    UNIQUE(user_id, guild_id)
)
""")
db.commit()

# ================= CACHE =================
invite_cache = {}

# ================= READY =================
@bot.event
async def on_ready():
    print(f"Bot hazır: {bot.user}")

    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = await guild.invites()
        except:
            invite_cache[guild.id] = []

    await bot.tree.sync()
    print("Slash komutlar sync edildi")

# ================= MESSAGE COUNT =================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    cursor.execute("""
    INSERT INTO users (user_id, guild_id, messages, invites, warns)
    VALUES (?, ?, 1, 0, 0)
    ON CONFLICT(user_id, guild_id)
    DO UPDATE SET messages = messages + 1
    """, (message.author.id, message.guild.id))

    db.commit()

    await bot.process_commands(message)

# ================= PRESENCE ROLE =================
@bot.event
async def on_presence_update(before, after):

    if not after.guild:
        return

    if not getattr(after, "activities", None):
        return

    member = after.guild.get_member(after.id)
    if not member:
        return

    role = discord.utils.get(after.guild.roles, name=".gg/revelıa")
    if not role:
        return

    text = ""

    for a in after.activities:
        if not a:
            continue

        if hasattr(a, "state") and a.state:
            text += a.state.lower() + " "

        if hasattr(a, "name") and a.name:
            text += a.name.lower() + " "

    if ".gg/revelıa" in text or "discord.gg/revelıa" in text:
        if role not in member.roles:
            await member.add_roles(role)
    else:
        if role in member.roles:
            await member.remove_roles(role)

# ================= INVITE SYSTEM =================
@bot.event
async def on_member_join(member):

    guild = member.guild
    before = invite_cache.get(guild.id, [])

    try:
        after = await guild.invites()
    except:
        return

    inviter = None

    for new_inv in after:
        for old_inv in before:
            if new_inv.code == old_inv.code and new_inv.uses > old_inv.uses:
                inviter = new_inv.inviter
                break

    if inviter:
        cursor.execute("""
        INSERT INTO users (user_id, guild_id, invites, warns, messages)
        VALUES (?, ?, 1, 0, 0)
        ON CONFLICT(user_id, guild_id)
        DO UPDATE SET invites = invites + 1
        """, (inviter.id, guild.id))

        db.commit()

    invite_cache[guild.id] = after

# ================= WARN SYSTEM =================
def apply_warn_roles(member, warns):

    roles = ["U1", "U2", "U3", "CEZALI"]

    warns = max(0, min(warns, 4))

    for r in roles:
        role = discord.utils.get(member.guild.roles, name=r)
        if role and role in member.roles:
            bot.loop.create_task(member.remove_roles(role))

    if warns == 0:
        return

    target = roles[warns - 1]

    role = discord.utils.get(member.guild.roles, name=target)
    if role:
        bot.loop.create_task(member.add_roles(role))

# ================= COMMANDS =================

@bot.tree.command(name="uyar")
async def uyar(interaction: discord.Interaction, user: discord.Member):

    cursor.execute("""
    SELECT warns FROM users
    WHERE user_id=? AND guild_id=?
    """, (user.id, interaction.guild.id))

    data = cursor.fetchone()
    warns = (data[0] + 1) if data else 1
    warns = min(warns, 4)

    cursor.execute("""
    INSERT INTO users (user_id, guild_id, warns, invites, messages)
    VALUES (?, ?, ?, 0, 0)
    ON CONFLICT(user_id, guild_id)
    DO UPDATE SET warns=excluded.warns
    """, (user.id, interaction.guild.id, warns))

    db.commit()

    apply_warn_roles(user, warns)

    await interaction.response.send_message(
        embed=discord.Embed(
            title="⚠️ UYARI",
            description=f"{user.mention} → U{warns}",
            color=discord.Color.orange()
        )
    )

@bot.tree.command(name="af")
async def af(interaction: discord.Interaction, user: discord.Member):

    cursor.execute("""
    UPDATE users SET warns=0
    WHERE user_id=? AND guild_id=?
    """, (user.id, interaction.guild.id))

    db.commit()

    apply_warn_roles(user, 0)

    await interaction.response.send_message(
        embed=discord.Embed(
            title="🧼 SIFIRLANDI",
            description=user.mention,
            color=discord.Color.green()
        )
    )

@bot.tree.command(name="profil")
async def profil(interaction: discord.Interaction, user: discord.Member = None):

    user = user or interaction.user

    cursor.execute("""
    SELECT invites, warns, messages
    FROM users
    WHERE user_id=? AND guild_id=?
    """, (user.id, interaction.guild.id))

    data = cursor.fetchone()

    invites = data[0] if data else 0
    warns = data[1] if data else 0
    messages = data[2] if data else 0

    embed = discord.Embed(title="👤 Profil", color=discord.Color.greyple())
    embed.add_field(name="🎟 Invite", value=invites)
    embed.add_field(name="⚠️ Warn", value=warns)
    embed.add_field(name="💬 Mesaj", value=messages)

    await interaction.response.send_message(embed=embed)

# ================= MOD =================
@bot.tree.command(name="sil")
async def sil(interaction: discord.Interaction, sayi: int):
    await interaction.channel.purge(limit=sayi)
    await interaction.response.send_message("Silindi", ephemeral=True)

@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, user: discord.Member):
    await user.kick()
    await interaction.response.send_message("Kick")

@bot.tree.command(name="ban")
async def ban(interaction: discord.Interaction, user: discord.Member):
    await user.ban()
    await interaction.response.send_message("Ban")

@bot.tree.command(name="kilitle")
async def kilitle(interaction: discord.Interaction):

    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False

    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message("🔒 Kilitlendi")

@bot.tree.command(name="aç")
async def ac(interaction: discord.Interaction):

    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = True

    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    await interaction.response.send_message("🔓 Açıldı")

# ================= LEADERBOARDS =================

@bot.tree.command(name="topinvite")
async def topinvite(interaction: discord.Interaction):

    cursor.execute("""
    SELECT user_id, invites FROM users
    WHERE guild_id=?
    ORDER BY invites DESC
    LIMIT 10
    """, (interaction.guild.id,))

    rows = cursor.fetchall()

    embed = discord.Embed(title="🏆 Invite Leaderboard", color=discord.Color.gold())

    if not rows:
        embed.description = "Veri yok."
        return await interaction.response.send_message(embed=embed)

    medals = ["🥇", "🥈", "🥉"]

    text = ""
    for i, (uid, val) in enumerate(rows, 1):
        member = interaction.guild.get_member(uid)
        name = member.name if member else "Bilinmeyen"

        rank = medals[i-1] if i <= 3 else f"#{i}"
        text += f"{rank} **{name}** → `{val}`\n"

    embed.add_field(name="Sıralama", value=text, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="topaktif")
async def topaktif(interaction: discord.Interaction):

    cursor.execute("""
    SELECT user_id, messages FROM users
    WHERE guild_id=?
    ORDER BY messages DESC
    LIMIT 10
    """, (interaction.guild.id,))

    rows = cursor.fetchall()

    embed = discord.Embed(title="🔥 Aktivite Leaderboard", color=discord.Color.blue())

    if not rows:
        embed.description = "Veri yok."
        return await interaction.response.send_message(embed=embed)

    medals = ["🥇", "🥈", "🥉"]

    text = ""
    for i, (uid, val) in enumerate(rows, 1):
        member = interaction.guild.get_member(uid)
        name = member.name if member else "Bilinmeyen"

        rank = medals[i-1] if i <= 3 else f"#{i}"
        text += f"{rank} **{name}** → `{val}`\n"

    embed.add_field(name="Sıralama", value=text, inline=False)

    await interaction.response.send_message(embed=embed)

# ================= RUN =================
bot.run("MTQ5NjkwNTY5MTc3NTExMTE4OA.GbZ6YS.Wiw1qDIsjB-iI34wyD2DzyWrms7oFVWuCV9xYo")
