import os
import discord
from discord import app_commands
import anthropic
from collections import defaultdict

# ─── Agent Definitions ───────────────────────────────────────────────

AGENTS = {
    "strategist": {
        "name": "◆ Strategist",
        "color": 0xB8C4E8,
        "system": """You are a senior Brand Strategist on a creative branding team. Your expertise covers brand positioning, target audience analysis, market differentiation, brand architecture, and strategic concept development.

Your role:
- Analyze market positioning and competitive landscape
- Define target audience personas and insights
- Develop brand concepts, values, and positioning statements
- Create strategic frameworks for brand development
- Provide data-informed strategic recommendations

Style: Sharp, analytical, confident. You think in frameworks but communicate with clarity. You challenge assumptions and push for distinctive positioning. Korean luxury/premium market savvy.

Always respond in the same language the user writes in (Korean or English). Keep responses focused and actionable. Reference relevant brand case studies when useful. Keep responses under 1500 characters for chat readability.""",
    },
    "copywriter": {
        "name": "▲ Copywriter",
        "color": 0xE8D4B8,
        "system": """You are a senior Copywriter on a creative branding team. Your expertise covers brand naming, taglines, brand voice development, product copy, and editorial content.

Your role:
- Create brand names, taglines, and slogans
- Develop brand voice and tone guidelines
- Write product descriptions, about pages, and manifesto copy
- Craft social media copy and campaign headlines
- Adapt copy across Korean and English markets

Style: Poetic yet precise. You find the unexpected word. You understand rhythm, brevity, and emotional resonance. Bilingual Korean/English fluency.

Always respond in the same language the user writes in. Provide multiple options when generating copy. Push beyond safe, generic phrasing. Keep responses under 1500 characters for chat readability.""",
    },
    "director": {
        "name": "● Director",
        "color": 0xD4E8B8,
        "system": """You are a senior Design Director on a creative branding team. Your expertise covers visual identity systems, color theory, typography, packaging design, spatial design, and art direction.

Your role:
- Define visual direction and mood for brands
- Recommend color palettes, typography systems, and visual languages
- Guide packaging, print, and digital design decisions
- Create moodboard descriptions and visual references
- Advise on production materials, finishes, and print specifications

Style: Visually literate, opinionated, refined. You think in textures, materials, and light. You reference art, architecture, and fashion as much as graphic design. You know Korean and global design markets.

Always respond in the same language the user writes in. Be specific — hex codes, font names, material specs. Keep responses under 1500 characters for chat readability.""",
    },
    "reviewer": {
        "name": "■ Reviewer",
        "color": 0xE8B8C4,
        "system": """You are a senior Creative Reviewer / Art Director on a branding team. Your role is quality control and constructive critique.

Your role:
- Review and critique brand strategy, copy, and design direction
- Identify weaknesses, inconsistencies, and missed opportunities
- Rate work on clarity, distinctiveness, and market fit (1-10 scale)
- Suggest specific improvements with rationale
- Ensure brand coherence across all touchpoints

Style: Honest but constructive. You don't sugarcoat but you don't tear down without building up. You spot what others miss.

Always respond in the same language the user writes in. Structure feedback: strengths → improvements → suggestions. Keep responses under 1500 characters for chat readability.""",
    },
}

# Channel name → agent mapping
CHANNEL_MAP = {
    "strategist": "strategist",
    "strategy": "strategist",
    "copywriter": "copywriter",
    "copy": "copywriter",
    "director": "director",
    "design": "director",
    "reviewer": "reviewer",
    "review": "reviewer",
}

# ─── Conversation History ────────────────────────────────────────────

conversation_history = defaultdict(list)
MAX_HISTORY = 20


def add_message(user_id, agent_id, role, content):
    key = (user_id, agent_id)
    conversation_history[key].append({"role": role, "content": content})
    if len(conversation_history[key]) > MAX_HISTORY:
        conversation_history[key] = conversation_history[key][-MAX_HISTORY:]


def get_messages(user_id, agent_id):
    return conversation_history[(user_id, agent_id)]


def clear_history(user_id, agent_id=None):
    if agent_id:
        conversation_history[(user_id, agent_id)] = []
    else:
        for k in [k for k in conversation_history if k[0] == user_id]:
            conversation_history[k] = []


# ─── Claude API ──────────────────────────────────────────────────────

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


async def get_response(user_id, agent_id, user_message):
    agent = AGENTS[agent_id]
    add_message(user_id, agent_id, "user", user_message)
    messages = get_messages(user_id, agent_id)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=agent["system"],
            messages=messages,
        )
        reply = response.content[0].text
        add_message(user_id, agent_id, "assistant", reply)
        return reply
    except Exception as e:
        conversation_history[(user_id, agent_id)].pop()
        return f"Error: {str(e)[:200]}"


# ─── Discord Bot ─────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    await tree.sync()
    print(f"Brand Team Bot online as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="Brand Projects"
        )
    )


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    channel_name = message.channel.name.lower()
    agent_id = None
    for keyword, aid in CHANNEL_MAP.items():
        if keyword in channel_name:
            agent_id = aid
            break

    if agent_id is None:
        return

    agent = AGENTS[agent_id]
    async with message.channel.typing():
        reply = await get_response(message.author.id, agent_id, message.content)

    for i in range(0, len(reply), 1900):
        chunk = reply[i : i + 1900]
        embed = discord.Embed(description=chunk, color=agent["color"])
        if i == 0:
            embed.set_author(name=agent["name"])
        await message.reply(embed=embed, mention_author=False)


@tree.command(name="ask", description="Ask a team member")
@app_commands.describe(agent="Team member", message="Your message")
@app_commands.choices(
    agent=[
        app_commands.Choice(name="Strategist", value="strategist"),
        app_commands.Choice(name="Copywriter", value="copywriter"),
        app_commands.Choice(name="Director", value="director"),
        app_commands.Choice(name="Reviewer", value="reviewer"),
    ]
)
async def ask_command(interaction, agent: app_commands.Choice[str], message: str):
    agent_data = AGENTS[agent.value]
    await interaction.response.defer()
    reply = await get_response(interaction.user.id, agent.value, message)
    for i in range(0, len(reply), 1900):
        chunk = reply[i : i + 1900]
        embed = discord.Embed(description=chunk, color=agent_data["color"])
        if i == 0:
            embed.set_author(name=agent_data["name"])
        await interaction.followup.send(embed=embed)


@tree.command(name="clear", description="Clear chat history")
@app_commands.choices(
    agent=[
        app_commands.Choice(name="Strategist", value="strategist"),
        app_commands.Choice(name="Copywriter", value="copywriter"),
        app_commands.Choice(name="Director", value="director"),
        app_commands.Choice(name="Reviewer", value="reviewer"),
        app_commands.Choice(name="All", value="all"),
    ]
)
async def clear_command(interaction, agent: app_commands.Choice[str]):
    if agent.value == "all":
        clear_history(interaction.user.id)
        await interaction.response.send_message("Cleared all history.", ephemeral=True)
    else:
        clear_history(interaction.user.id, agent.value)
        await interaction.response.send_message(
            f"Cleared {AGENTS[agent.value]['name']} history.", ephemeral=True
        )


@tree.command(name="setup", description="Create brand team channels")
@app_commands.default_permissions(administrator=True)
async def setup_command(interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if not guild:
        await interaction.followup.send("Server only.")
        return

    category = discord.utils.get(guild.categories, name="BRAND TEAM")
    if not category:
        category = await guild.create_category("BRAND TEAM")

    created = []
    for name, topic in [
        ("strategist", "Brand strategy channel"),
        ("copywriter", "Copywriting channel"),
        ("director", "Design direction channel"),
        ("reviewer", "Review & critique channel"),
    ]:
        if not discord.utils.get(guild.text_channels, name=name):
            ch = await guild.create_text_channel(name, category=category, topic=topic)
            created.append(ch.mention)

    if created:
        await interaction.followup.send(f"Created: {', '.join(created)}")
    else:
        await interaction.followup.send("All channels already exist!")


@tree.command(name="team", description="Show team members")
async def team_command(interaction):
    embed = discord.Embed(title="Brand Team", color=0x0A0A0A)
    for aid, agent in AGENTS.items():
        count = len(get_messages(interaction.user.id, aid))
        embed.add_field(
            name=agent["name"],
            value=f"{count} messages" if count else "Ready",
            inline=True,
        )
    await interaction.response.send_message(embed=embed)


bot.run(os.environ.get("DISCORD_TOKEN"))
