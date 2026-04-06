require("dotenv").config();
const {
  Client,
  GatewayIntentBits,
  Partials,
  EmbedBuilder,
  ActionRowBuilder,
  StringSelectMenuBuilder,
} = require("discord.js");
const Anthropic = require("@anthropic-ai/sdk").default;

// ─── Agent Definitions ───────────────────────────────────────────
const AGENTS = {
  strategist: {
    name: "Strategist",
    label: "브랜드 전략",
    emoji: "◆",
    color: 0xb8c4e8,
    system: `You are a senior Brand Strategist on a creative branding team. Your expertise covers brand positioning, target audience analysis, market differentiation, brand architecture, and strategic concept development.

Your role:
- Analyze market positioning and competitive landscape
- Define target audience personas and insights
- Develop brand concepts, values, and positioning statements
- Create strategic frameworks for brand development
- Provide data-informed strategic recommendations

Style: Sharp, analytical, confident. You think in frameworks but communicate with clarity. You challenge assumptions and push for distinctive positioning. Korean luxury/premium market savvy.

Always respond in the same language the user writes in (Korean or English). Keep responses focused and actionable — aim for 300 words max unless the topic demands more. If the user shares a brief, expand on strategic implications.`,
  },
  copywriter: {
    name: "Copywriter",
    label: "카피라이팅",
    emoji: "▲",
    color: 0xe8d4b8,
    system: `You are a senior Copywriter on a creative branding team. Your expertise covers brand naming, taglines, brand voice development, product copy, and editorial content.

Your role:
- Create brand names, taglines, and slogans
- Develop brand voice and tone guidelines
- Write product descriptions, about pages, and manifesto copy
- Craft social media copy and campaign headlines
- Adapt copy across Korean and English markets

Style: Poetic yet precise. You find the unexpected word. You understand rhythm, brevity, and emotional resonance. You write copy that sounds like it belongs on a museum wall, not a corporate brochure. Bilingual Korean/English fluency.

Always respond in the same language the user writes in. Provide multiple options when generating copy. Explain the intent behind word choices. Aim for 300 words max unless generating many options.`,
  },
  director: {
    name: "Director",
    label: "디자인 디렉션",
    emoji: "●",
    color: 0xd4e8b8,
    system: `You are a senior Design Director on a creative branding team. Your expertise covers visual identity systems, color theory, typography, packaging design, spatial design, and art direction.

Your role:
- Define visual direction and mood for brands
- Recommend color palettes, typography systems, and visual languages
- Guide packaging, print, and digital design decisions
- Create moodboard descriptions and visual references
- Advise on production materials, finishes, and print specifications

Style: Visually literate, opinionated, refined. You think in textures, materials, and light. You reference art, architecture, and fashion as much as graphic design. Your taste is contemporary but informed by history. You know Korean and global design markets.

Always respond in the same language the user writes in. Be specific about visual choices — hex codes, font names, material specs. Aim for 300 words max.`,
  },
  reviewer: {
    name: "Reviewer",
    label: "크리틱 & 리뷰",
    emoji: "■",
    color: 0xe8b8c4,
    system: `You are a senior Creative Reviewer / Art Director on a branding team. Your role is quality control and constructive critique.

Your role:
- Review and critique brand strategy, copy, and design direction
- Identify weaknesses, inconsistencies, and missed opportunities
- Rate work on clarity, distinctiveness, and market fit (1-10 scale)
- Suggest specific improvements with rationale
- Ensure brand coherence across all touchpoints

Style: Honest but constructive. You don't sugarcoat but you don't tear down without building up. You spot what others miss. You balance creative ambition with market reality.

Always respond in the same language the user writes in. Structure feedback: strengths → areas for improvement → specific suggestions. Use ratings (1-10) for different criteria. Aim for 300 words max.`,
  },
};

// ─── Channel name mapping ────────────────────────────────────────
const CHANNEL_MAP = {
  [process.env.CHANNEL_STRATEGIST || "strategist"]: "strategist",
  [process.env.CHANNEL_COPYWRITER || "copywriter"]: "copywriter",
  [process.env.CHANNEL_DIRECTOR || "director"]: "director",
  [process.env.CHANNEL_REVIEWER || "reviewer"]: "reviewer",
};

// ─── Conversation History (in-memory, per channel) ───────────────
const conversations = new Map();
const MAX_HISTORY = 20; // keep last 20 messages per channel

function getHistory(channelId) {
  if (!conversations.has(channelId)) {
    conversations.set(channelId, []);
  }
  return conversations.get(channelId);
}

function addToHistory(channelId, role, content) {
  const history = getHistory(channelId);
  history.push({ role, content });
  if (history.length > MAX_HISTORY) {
    history.splice(0, history.length - MAX_HISTORY);
  }
}

function clearHistory(channelId) {
  conversations.set(channelId, []);
}

// ─── Anthropic Client ────────────────────────────────────────────
const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

async function askAgent(agentId, channelId, userMessage) {
  const agent = AGENTS[agentId];
  if (!agent) return "알 수 없는 에이전트입니다.";

  addToHistory(channelId, "user", userMessage);
  const messages = getHistory(channelId).map((m) => ({
    role: m.role,
    content: m.content,
  }));

  try {
    const response = await anthropic.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1024,
      system: agent.system,
      messages,
    });

    const text =
      response.content
        .filter((c) => c.type === "text")
        .map((c) => c.text)
        .join("\n") || "응답을 생성할 수 없습니다.";

    addToHistory(channelId, "assistant", text);
    return text;
  } catch (err) {
    console.error("Anthropic API error:", err.message);
    return "⚠ API 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
  }
}

// ─── Discord Client ──────────────────────────────────────────────
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
  partials: [Partials.Channel],
});

// ─── Build Embed ─────────────────────────────────────────────────
function buildEmbed(agent, content) {
  // Discord embeds have a 4096 char limit for description
  const truncated =
    content.length > 4000 ? content.slice(0, 4000) + "\n\n..." : content;

  return new EmbedBuilder()
    .setColor(agent.color)
    .setAuthor({
      name: `${agent.emoji}  ${agent.name} — ${agent.label}`,
    })
    .setDescription(truncated)
    .setFooter({ text: "Brand Team AI" })
    .setTimestamp();
}

// ─── Slash Command Handler ───────────────────────────────────────
client.on("interactionCreate", async (interaction) => {
  // Handle select menu
  if (interaction.isStringSelectMenu() && interaction.customId === "agent_select") {
    const agentId = interaction.values[0];
    const agent = AGENTS[agentId];
    await interaction.reply({
      content: `${agent.emoji} **${agent.name}** 채널로 이동하거나, \`/ask\` 명령어에서 선택해서 사용하세요!\n\n> ${agent.label} 담당`,
      ephemeral: true,
    });
    return;
  }

  if (!interaction.isChatInputCommand()) return;

  const { commandName } = interaction;

  // /ask <agent> <message>
  if (commandName === "ask") {
    const agentId = interaction.options.getString("agent");
    const message = interaction.options.getString("message");
    const agent = AGENTS[agentId];

    await interaction.deferReply();

    const response = await askAgent(agentId, interaction.channelId, message);
    const embed = buildEmbed(agent, response);

    await interaction.editReply({ embeds: [embed] });
  }

  // /team — show team overview
  if (commandName === "team") {
    const embed = new EmbedBuilder()
      .setColor(0x0a0a0a)
      .setTitle("Brand Team AI")
      .setDescription(
        Object.values(AGENTS)
          .map(
            (a) =>
              `${a.emoji} **${a.name}** — ${a.label}\n> \`/ask agent:${
                Object.keys(AGENTS).find((k) => AGENTS[k] === a)
              } message:...\``
          )
          .join("\n\n")
      )
      .addFields({
        name: "전용 채널",
        value:
          "채널 이름이 `#strategist`, `#copywriter`, `#director`, `#reviewer`이면\n명령어 없이 바로 대화할 수 있어요!",
      })
      .setFooter({ text: "/clear 로 대화 기록 초기화" });

    await interaction.reply({ embeds: [embed] });
  }

  // /clear — reset conversation
  if (commandName === "clear") {
    clearHistory(interaction.channelId);
    await interaction.reply({
      content: "🗑️ 이 채널의 대화 기록이 초기화되었습니다.",
      ephemeral: true,
    });
  }

  // /brief — submit a brand brief to all agents
  if (commandName === "brief") {
    const briefText = interaction.options.getString("content");

    await interaction.deferReply();

    const results = await Promise.all(
      Object.entries(AGENTS).map(async ([id, agent]) => {
        const response = await askAgent(
          id,
          `brief-${interaction.channelId}-${id}`,
          briefText
        );
        return { id, agent, response };
      })
    );

    const embeds = results.map(({ agent, response }) =>
      buildEmbed(agent, response)
    );

    await interaction.editReply({
      content: `📋 **브리프 결과** — 4명의 팀원이 동시에 분석했습니다.`,
      embeds,
    });
  }
});

// ─── Auto-respond in dedicated channels ──────────────────────────
client.on("messageCreate", async (message) => {
  if (message.author.bot) return;

  const channelName = message.channel.name;
  const agentId = CHANNEL_MAP[channelName];

  if (!agentId) return;

  const agent = AGENTS[agentId];
  const userMessage = message.content;

  if (!userMessage.trim()) return;

  await message.channel.sendTyping();

  const response = await askAgent(agentId, message.channelId, userMessage);
  const embed = buildEmbed(agent, response);

  await message.reply({ embeds: [embed] });
});

// ─── Ready ───────────────────────────────────────────────────────
client.once("ready", () => {
  console.log(`✓ Brand Team Bot online — ${client.user.tag}`);
  console.log(`✓ Serving ${Object.keys(AGENTS).length} agents`);
  console.log(`✓ Listening on channels: ${Object.keys(CHANNEL_MAP).join(", ")}`);
});

client.login(process.env.DISCORD_TOKEN);
