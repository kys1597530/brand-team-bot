require("dotenv").config();
const { REST, Routes, SlashCommandBuilder } = require("discord.js");

const commands = [
  new SlashCommandBuilder()
    .setName("ask")
    .setDescription("AI 팀원에게 질문하기")
    .addStringOption((opt) =>
      opt
        .setName("agent")
        .setDescription("팀원 선택")
        .setRequired(true)
        .addChoices(
          { name: "◆ Strategist — 브랜드 전략", value: "strategist" },
          { name: "▲ Copywriter — 카피라이팅", value: "copywriter" },
          { name: "● Director — 디자인 디렉션", value: "director" },
          { name: "■ Reviewer — 크리틱 & 리뷰", value: "reviewer" }
        )
    )
    .addStringOption((opt) =>
      opt
        .setName("message")
        .setDescription("메시지 내용")
        .setRequired(true)
    ),

  new SlashCommandBuilder()
    .setName("brief")
    .setDescription("브리프를 4명의 팀원에게 동시에 보내기")
    .addStringOption((opt) =>
      opt
        .setName("content")
        .setDescription("브랜드 브리프 내용")
        .setRequired(true)
    ),

  new SlashCommandBuilder()
    .setName("team")
    .setDescription("팀원 소개 & 사용법 보기"),

  new SlashCommandBuilder()
    .setName("clear")
    .setDescription("이 채널의 대화 기록 초기화"),
].map((cmd) => cmd.toJSON());

const rest = new REST({ version: "10" }).setToken(process.env.DISCORD_TOKEN);

(async () => {
  try {
    console.log("⏳ 슬래시 명령어 등록 중...");
    await rest.put(Routes.applicationCommands(process.env.DISCORD_APP_ID), {
      body: commands,
    });
    console.log("✓ 슬래시 명령어 등록 완료!");
    console.log("  /ask — 팀원에게 질문");
    console.log("  /brief — 전체 팀에게 브리프");
    console.log("  /team — 팀원 소개");
    console.log("  /clear — 대화 초기화");
  } catch (err) {
    console.error("명령어 등록 실패:", err);
  }
})();
