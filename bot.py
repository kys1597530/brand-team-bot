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
    "team-chat": "all",
    "team": "all",
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

    # Team chat: all agents respond
    if agent_id == "all":
        for aid, agent in AGENTS.items():
            async with message.channel.typing():
                reply = await get_response(message.author.id, aid, message.content)
            for i in range(0, len(reply), 1900):
                chunk = reply[i : i + 1900]
                embed = discord.Embed(description=chunk, color=agent["color"])
                if i == 0:
                    embed.set_author(name=agent["name"])
                await message.channel.send(embed=embed)
        return

    # Single agent response
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
        ("team-chat", "All team members respond together"),
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


# ─── Brainstorm Mode ─────────────────────────────────────────────────

brainstorm_active = {}  # {channel_id: True}


@tree.command(name="brainstorm", description="팀 자동 브레인스토밍 (30분)")
@app_commands.describe(
    topic="브레인스토밍 주제",
    rounds="라운드 수 (기본 15, 최대 30)",
)
async def brainstorm_command(
    interaction,
    topic: str,
    rounds: int = 15,
):
    rounds = min(rounds, 30)
    channel = interaction.channel
    channel_id = channel.id

    if brainstorm_active.get(channel_id):
        await interaction.response.send_message(
            "이미 브레인스토밍 진행 중입니다! `/stop` 으로 중지하세요.",
            ephemeral=True,
        )
        return

    brainstorm_active[channel_id] = True
    await interaction.response.send_message(
        f"🧠 **브레인스토밍 시작!**\n"
        f"주제: **{topic}**\n"
        f"라운드: **{rounds}** (10라운드마다 요약)\n"
        f"중지하려면 `/stop`"
    )

    agent_order = ["strategist", "copywriter", "director", "reviewer"]
    conversation_log = []
    summary_so_far = ""

    for round_num in range(1, rounds + 1):
        if not brainstorm_active.get(channel_id):
            break

        # Round header
        header = discord.Embed(
            description=f"**라운드 {round_num}/{rounds}**",
            color=0x333333,
        )
        await channel.send(embed=header)

        for agent_id in agent_order:
            if not brainstorm_active.get(channel_id):
                break

            agent = AGENTS[agent_id]

            # Build full context for this agent
            if round_num == 1 and agent_id == "strategist":
                prompt = f"[브레인스토밍 주제]: {topic}\n\n이 주제에 대해 브랜드 전략 관점에서 시작해줘. 핵심 포지셔닝과 타겟을 제안해."
            else:
                # Use up to last 12 messages for rich context
                recent_count = min(len(conversation_log), 12)
                recent = conversation_log[-recent_count:]
                context = "\n\n---\n\n".join(
                    [f"[{e['agent']}] (Round {e.get('round', '?')}):\n{e['content']}" for e in recent]
                )

                continuity_instruction = (
                    f"⚠️ 중요: 이것은 진행 중인 브레인스토밍의 라운드 {round_num}입니다. "
                    f"아래 팀원들의 기존 논의를 반드시 읽고, 그 내용을 기반으로 발전시켜야 합니다. "
                    f"절대 새로운 주제를 시작하지 마세요. 기존 아이디어를 구체화하거나, 빠진 부분을 보완하거나, 개선점을 제안하세요."
                )

                if summary_so_far:
                    prompt = (
                        f"[브레인스토밍 주제]: {topic}\n\n"
                        f"{continuity_instruction}\n\n"
                        f"===== 이전 라운드 요약 =====\n{summary_so_far}\n\n"
                        f"===== 요약 이후 최근 대화 =====\n{context}\n\n"
                        f"위 논의를 바탕으로 너의 전문 분야({agent['name']}) 관점에서 기존 아이디어를 더 발전시켜줘."
                    )
                else:
                    prompt = (
                        f"[브레인스토밍 주제]: {topic}\n\n"
                        f"{continuity_instruction}\n\n"
                        f"===== 팀 대화 기록 =====\n{context}\n\n"
                        f"위 논의를 바탕으로 너의 전문 분야({agent['name']}) 관점에서 기존 아이디어를 더 발전시켜줘."
                    )

            try:
                async with channel.typing():
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=800,
                        system=agent["system"],
                        messages=[{"role": "user", "content": prompt}],
                    )
                    reply = response.content[0].text

                conversation_log.append({"agent": agent["name"], "content": reply, "round": round_num})

                embed = discord.Embed(description=reply, color=agent["color"])
                embed.set_author(name=agent["name"])
                embed.set_footer(text=f"Round {round_num}")
                await channel.send(embed=embed)

            except Exception as e:
                embed = discord.Embed(
                    description=f"Error: {str(e)[:200]}",
                    color=0xFF0000,
                )
                embed.set_author(name=agent["name"])
                await channel.send(embed=embed)

        # Summary every 10 rounds
        if round_num % 10 == 0 and brainstorm_active.get(channel_id):
            summary_embed = discord.Embed(
                description="📋 **중간 요약 생성 중...**",
                color=0xFFFFFF,
            )
            await channel.send(embed=summary_embed)

            all_content = "\n\n".join(
                [f"[{e['agent']}]: {e['content']}" for e in conversation_log]
            )

            try:
                summary_response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    system="당신은 브레인스토밍 세션의 기록자입니다. 팀 대화를 다음 구조로 정리하세요:\n1. 확정된 결정사항 (브랜드명, 타겟, 포지셔닝 등)\n2. 제안된 카피/슬로건 후보\n3. 디자인 방향 (컬러, 폰트, 소재 등 구체적으로)\n4. 리뷰어 피드백 요점\n5. 아직 미결정 사항\n\n⚠️ 구체적인 이름, 수치, 컬러코드, 문구 등은 반드시 그대로 보존하세요. 다음 라운드가 이 요약을 기반으로 이어가야 합니다. 한국어로 작성하세요.",
                    messages=[
                        {
                            "role": "user",
                            "content": f"다음 브레인스토밍 대화를 요약해주세요:\n\n{all_content}",
                        }
                    ],
                )
                summary_so_far = summary_response.content[0].text

                # Reset log to save tokens
                conversation_log = []

                s_embed = discord.Embed(
                    title=f"📋 {round_num}라운드 요약",
                    description=summary_so_far,
                    color=0xFFFFFF,
                )
                await channel.send(embed=s_embed)

            except Exception as e:
                await channel.send(
                    embed=discord.Embed(
                        description=f"요약 생성 실패: {str(e)[:200]}", color=0xFF0000
                    )
                )

    # Final summary
    if brainstorm_active.get(channel_id) and conversation_log:
        all_content = "\n\n".join(
            [f"[{e['agent']}]: {e['content']}" for e in conversation_log]
        )
        context_for_final = (
            f"이전 요약:\n{summary_so_far}\n\n최근 대화:\n{all_content}"
            if summary_so_far
            else all_content
        )

        try:
            final_response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system="당신은 브레인스토밍 세션의 기록자입니다. 전체 세션의 최종 결과를 정리해주세요: 1) 핵심 결정사항 2) 브랜드 전략 요약 3) 카피 후보 4) 디자인 방향 5) 다음 단계. 한국어로 작성하세요.",
                messages=[
                    {
                        "role": "user",
                        "content": f"전체 브레인스토밍 최종 요약:\n\n{context_for_final}",
                    }
                ],
            )

            final_embed = discord.Embed(
                title="✅ 브레인스토밍 완료! 최종 요약",
                description=final_response.content[0].text,
                color=0x00FF88,
            )
            await channel.send(embed=final_embed)

        except Exception as e:
            await channel.send(
                embed=discord.Embed(
                    description=f"최종 요약 실패: {str(e)[:200]}", color=0xFF0000
                )
            )

    brainstorm_active.pop(channel_id, None)

    if brainstorm_active.get(channel_id) is None:
        done_embed = discord.Embed(
            description="🏁 **브레인스토밍 종료!** 위 요약을 확인하세요.",
            color=0x333333,
        )
        await channel.send(embed=done_embed)


@tree.command(name="stop", description="브레인스토밍 중지")
async def stop_command(interaction):
    channel_id = interaction.channel.id
    if brainstorm_active.get(channel_id):
        brainstorm_active[channel_id] = False
        await interaction.response.send_message("⏹ 브레인스토밍을 중지합니다...")
    else:
        await interaction.response.send_message(
            "진행 중인 브레인스토밍이 없습니다.", ephemeral=True
        )


bot.run(os.environ.get("DISCORD_TOKEN"))
