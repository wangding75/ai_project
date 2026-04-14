# 智囊团 · 完整设计与开发文档

> AI Multi-Agent Discussion Platform  
> 完整原型 · 功能设计 · 技术架构 · 开发计划  
> Version 1.0 | 2026.04 | 基于产品方案 v4 定稿

---

## 文档说明

本文档面向参与智囊团项目的所有开发者，包含产品原型说明、功能规格、技术架构设计与完整开发计划。阅读本文档后，任何具备全栈开发能力的工程师应能独立理解并接手项目的任意模块。

- **开发语言**：TypeScript
- **前端框架**：React / Next.js 14
- **核心原型**：单文件 HTML（已验证可运行）

---

# 01 产品原型

## 1.1 产品定位

智囊团是一个角色化 AI 智囊团产品，用户以"老板/主角"身份参与多个 AI 角色的沉浸式讨论。不是 AI 问答工具，而是一种新的 AI 交互范式 —— Multi-Agent UX。

> **核心价值主张**：用户是老板，AI 是团队。在有冲突、有人设、有节奏的讨论过程中获得多维度分析和决策辅助。

| 对比维度 | ChatGPT 等 | 智囊团 |
|---------|-----------|--------|
| 交互方式 | 我问，AI 答 | 用户参与 + 旁观 + 指挥 |
| 输出形式 | 单一视角答案 | 多视角碰撞 + 收敛结论 |
| 体验感受 | 工具 | 像参加一场有趣的会议 |
| 情感连接 | 弱 | 角色人设带来记忆点和沉浸感 |

---

## 1.2 页面流程

应用分为 5 个核心页面，按线性流程串联：

| 页面 | 路由 | 功能描述 | 进入条件 |
|-----|------|---------|---------|
| 启动屏 | `/` | 加载上次配置，自动切换主题，1秒后跳转 | 冷启动 |
| 模板选择 | `/templates` | 选择讨论场景，支持分类筛选和 JSON 导入 | 启动后 |
| LLM 配置 | `/llm` | 配置模型、API Key、自定义接口、高级参数 | 选模板后 |
| 角色配置 | `/roles` | 查看/编辑/添加角色，配置人设、提示词、模型 | LLM 配置后 |
| 讨论主界面 | `/chat` | 核心体验，多角色对话流，爽点机制，用户参与 | 进入讨论后 |

---

## 1.3 页面规格：模板选择

### 布局

左右双栏布局：
- **左栏（固定 320px）**：品牌 Logo + 分类导航（全部/历史人文/商业决策/童话奇幻）+ 已选信息 + 操作按钮
- **右栏（自适应滚动）**：模板卡片网格（2列），底部导入区

### 模板卡片

- 顶部色带（5px）：代表绑定主题的视觉指纹
- 图标 + 名称 + 描述 + 角色 chip + 主题色点
- **选中态**：border 加粗变为 ink 色 + 右上角 ✓ 徽章（pop 动画）
- **悬停态**：translateY(-2px) + box-shadow 加深

### 模板导入

- 点击按钮 或 拖拽 JSON 文件到导入区
- 解析成功：自动注入为新卡片，角色信息导入角色配置页
- 解析失败：Toast 提示"JSON 格式错误"

### 主题自动切换

选中模板时，自动读取 `data-theme` 属性，切换全局主题变量。写入 localStorage，下次启动时恢复。

---

## 1.4 页面规格：LLM 配置

### 布局

左侧导航栏（200px）+ 右侧内容区，5 个子页签：

- **全局默认**：模型选择 + Temperature / MaxToken / 超时参数
- **自定义模型**：填写名称 / 模型ID / Base URL / API Key / 接口格式，支持添加多个、折叠/展开、删除
- **API Keys**：按供应商（OpenAI/Anthropic/Gemini/Deepseek/OpenRouter）填写 Key，显示连通状态
- **免费额度**：零配置启动入口，推荐免费模型列表（服务端动态下发）
- **高级设置**：重试次数 / 发言间隔 / 并发数 / 流式开关 / 自定义 Headers

> **自定义模型说明**：Base URL 支持任意 OpenAI 兼容接口，包括本地 Ollama（`http://localhost:11434/v1`）、自建代理、第三方中转。API Key 仅存在 localStorage，不上传服务器。

---

## 1.5 页面规格：角色配置

### 布局

左侧角色列表（220px）+ 右侧编辑区（滚动）。

### 角色列表

- 每个角色：彩色方形头像 + 角色名（对应颜色）+ 定位 + 主持人徽章
- 非主持人角色悬停时显示删除按钮（✕）
- 右上角 `+` 按钮：打开添加角色弹窗
- 激活态：左边框显示角色颜色

### 编辑区字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| 角色名称 | text input | 显示名 |
| 角色定位 | text input | 分析视角描述，如"战略视角" |
| 头像字 | text input | 最多 2 个字，用于头像显示 |
| 角色颜色 | color picker | 6 种预设色：amber/blue/jade/rose/violet/muted |
| 是否主持人 | toggle | 开启后负责调度逻辑，角色名旁显示"主持"徽章 |
| 性格定义 | text input | 约束 LLM 整体性格走向的一句话描述 |
| 说话风格 | tag cloud | 多选标签，选中变为黑底白字 |
| 口头禅/标志表达 | text input | 用 `/` 分隔，LLM 在合适时机插入 |
| 对主公的态度 | select | 4 种预设：尊重不盲从 / 完全尊重 / 敬重挑战 / 平等对话 |
| 使用模型 | select | 跟随全局 或 单独指定模型 |
| Temperature | select | 跟随全局 或 单独指定（0.6 / 0.8 / 1.0 / 1.2） |
| 系统提示词 | textarea | 直接发给 LLM 的 system prompt |
| 发言风格预览 | display | 静态展示 2 条示例发言（斜体气泡样式） |

### 添加角色弹窗

- 字段：名称、定位、颜色选择、是否主持人
- 确认后加入角色列表，自动生成基础 system prompt
- 支持后续在编辑区完善所有字段

---

## 1.6 页面规格：讨论主界面

### 顶栏

- 左：场景名徽章（图标 + 名称）+ 当前话题 pill
- 右：讨论状态指示器（绿点 + "讨论进行中"）+ 角色/主题/新讨论按钮

### 角色栏

横向排列所有角色，主持人角色在最左侧，用户（主公）在最右侧。当前发言角色显示底部下划线指示器。

### 消息流

| 消息类型 | 视觉规格 | 说明 |
|---------|---------|------|
| 主持人发言 | 暖灰底 + 斜体 + 左对齐 | 调度说明和过渡语，字号稍小 |
| 角色发言 | 角色色调背景 + 角色色边框 + 左对齐 | 背景色为角色色 22% opacity |
| 用户发言 | 纯黑底 + 白字 + 右对齐 | 最高权重视觉 |
| 打脸事件卡 | 玫瑰红左边框 + 浅玫瑰背景 | fadeUp 动画入场 |
| 站队事件卡 | 琥珀色左边框 + 浅琥珀背景 | 阵营信息展示 |
| 主持人邀请卡 | 纯黑背景 + 白字 + 白色/透明按钮 | 视觉重心，两个操作：回应/跳过 |
| 打字中指示 | 三点动画 + 角色名 | fadeIn 动画入场 |

### 输入区

- 顶部提示：模式标签（插话/指挥/定夺）
- 自适应高度 textarea（min 42px，max 120px）
- 发送按钮：黑底白箭头，hover 上移 + 阴影加深
- 快捷指令 chips：点击填入 textarea，角色名动态生成

---

## 1.7 主题系统

内置 4 套主题，通过 CSS 变量实现，切换时 `transition: 0.35s`：

| 主题名 | data-theme | 背景色 | 强调色 | 适配模板 |
|-------|-----------|--------|--------|---------|
| 硅谷简洁 | （默认，不设 attr） | `#F7F6F3` | `#E8620A` | 创业/投资类 |
| 水墨暗色 | `ink` | `#1A1612` | `#C8A96E` | 三国/楚汉类 |
| 童话梦幻 | `fairy` | `#0E0818` | `#C084FC` | 白雪公主类 |
| 星际科技 | `space` | `#020509` | `#00C8FF` | 星际舰队类 |

主题与模板绑定通过 `data-theme` 属性在模板 JSON 中声明。进入会话前自动加载上次使用模板的主题；无历史记录时默认硅谷简洁。

---

# 02 功能设计

## 2.1 讨论引擎：核心能力

讨论引擎是产品的灵魂，运行在客户端。核心是"导演逻辑"而非"调度逻辑"——不是决定谁说话，而是决定什么时候制造冲突、什么时候收束、什么时候拉用户进来。

| 能力 | 描述 | 触发条件 |
|-----|------|---------|
| 识别用户意图 | 解析用户发言的方向、情绪、指令类型 | 用户每次发言后 |
| 定向调度 | 从角色列表中选 1-2 个最相关角色回应，不是全员出动 | 用户发言/轮次推进时 |
| 主动邀请用户 | 在关键节点发出邀请卡，带"回应"和"跳过"选项 | 见下方触发条件 |
| 制造冲突 | 识别可争论点，主动调度"反方"角色 | 出现明确分歧时 |
| 触发爽点 | 打脸/站队/投票/反转，见 2.3 节 | 满足触发条件时 |
| 控制节奏 | 限制单次发言长度，管理轮次密度 | 每轮发言生成时 |
| 话题转向 | 用户改变方向时重新组织讨论 | 用户发言偏离当前主题时 |
| 防止拍马屁 | 用户观点有明显问题时调度角色反驳 | 检测到角色全员附和时 |
| 收束总结 | 讨论达到轮次上限或用户发出结束信号时 | 轮次上限/用户指令 |

---

## 2.2 主持人邀请机制

### 触发时机（不能机械定时）

- 出现明显的观点分歧（两个角色意见相反）
- 某角色直接质疑了用户之前的观点
- 讨论到了需要做决定的分叉点
- 出现意料之外的信息或反转
- 讨论即将收敛、需要用户最终定夺

### 邀请频率

一场讨论中 2-3 次邀请为宜。太频繁打断流畅感，太少则用户沦为纯旁观者。

### 邀请措辞要求

必须用角色化语言，不能用系统提示风格：

- ✅ 正确："主公，诸葛亮和庞统已经吵翻了，你站哪边？"
- ❌ 错误："请用户发表意见"

### 跳过处理

用户选择"让他们继续"后，讨论推进到下一轮，不影响流程。即使跳过，用户也感受到被尊重。

---

## 2.3 爽点机制规格

### 打脸机制

- **触发条件**：角色 B 的论据直接推翻了角色 A 之前的明确断言
- **展示**：玫瑰红事件卡，标题"[B名] 直接打脸 [A名]"，描述简短
- **后续**：被打脸角色用人设风格回应（不服/狡辩/尴尬），主持人放大戏剧性
- **频率**：一场讨论 0-2 次，不强制触发

### 站队/阵营对抗

- **触发条件**：出现重大方向分歧（如"打vs不打"、"做vs不做"）
- **展示**：琥珀色事件卡，展示两个阵营的角色构成
- **后续**：邀请用户表态站队，围绕分歧进行短轮次交锋
- **化解**：用户选边后自然推进到执行层讨论

### 投票/判定

- **触发条件**：某议题已争论 3+ 轮仍无定论
- **展示**：主持人发起投票，角色各自表态，最终统计
- **用户参与**：可参与投票，也可直接下达裁定

### 随机反转事件

- "探子来报"：临时引入新角色带来新信息
- "叛变"：某角色突然改变立场，必须给出理由
- "极端假设"：主持人抛出反事实命题，打破既有分析框架
- **频率**：一场讨论最多 1 次，不能连续触发

---

## 2.4 用户参与模式

| 模式 | 触发方式 | 处理逻辑 | 优先级 |
|-----|---------|---------|--------|
| 被动邀请 | 主持人在关键节点发出邀请卡 | 用户回应 → 调度 1-2 个角色响应；跳过 → 继续推进 | 最常见 |
| 主动插话 | 用户随时在输入框发言 | 主持人解析意图 → 定向调度相关角色 | 高 |
| 直接指挥 | 用户下达明确指令（"让X反驳他"） | 主持人执行指令，调度指定角色 | 最高 |

---

## 2.5 快捷指令

底部 chips 提供常用快捷指令，点击填入输入框：

- 让 [角色名] 反驳他（按角色列表动态生成）
- 发起投票
- 换个角度
- 总结一下

用户也可以直接输入自由文本，引擎处理后判断意图类型。

---

## 2.6 模板数据模型

模板以 JSON 格式存储，支持服务端下发和本地导入。完整 Schema：

```json
{
  "id": "sanguo",
  "name": "三国军师团",
  "version": "1.2.0",
  "icon": "⚔️",
  "description": "水镜先生主持，诸葛亮、庞统、关羽、曹操各持立场",
  "category": "history",
  "theme": "ink",
  "userIdentity": {
    "name": "主公",
    "avatar": "公"
  },
  "worldview": {
    "background": "三国乱世，群雄割据...",
    "tone": "dramatic",
    "entryMessage": "主公驾到，臣等候多时"
  },
  "roles": [
    {
      "id": "sima",
      "name": "司马徽",
      "char": "徽",
      "type": "圆桌主持",
      "isHost": true,
      "color": "amber",
      "personality": "看透一切但不轻易表态，话不多但每句都在点上",
      "tags": ["话少精准", "禅意", "白话文"],
      "catchphrase": "行了行了，听下一位",
      "attitude": "尊重但不盲从",
      "systemPrompt": "你是司马徽，是这场圆桌会议的主持人...",
      "model": "default",
      "temperature": "default",
      "preview": [
        "好了好了，诸葛亮说完了。庞统，你刚才那个表情说明你有不同意见，说吧。",
        "主公，他们两个意见完全相反，你站哪边？"
      ]
    }
  ],
  "events": {
    "inviteConditions": ["明显分歧", "决策分叉点"],
    "slapEnabled": true,
    "campEnabled": true,
    "voteEnabled": true,
    "reverseEnabled": false
  },
  "rhythm": {
    "maxTurnsPerRole": 4,
    "maxCharsPerTurn": 200,
    "inviteFrequency": 3,
    "speakerDelay": 800
  },
  "freeModels": [
    {
      "id": "gemini-1.5-flash",
      "name": "Gemini Flash",
      "provider": "google"
    }
  ]
}
```

---

# 03 技术设计

## 3.1 整体架构

> **架构原则**：客户端优先 + 极简服务器。核心讨论引擎完全在客户端运行，服务器仅做模板分发和版本管理。LLM 调用由客户端通过用户 Key 直连。

架构分三层：

- **客户端层**（React/Next.js）：UI 渲染、讨论引擎、LLM 调用、本地存储
- **服务端层**（极简）：模板 JSON 存储/分发（CDN）、版本管理、推荐模型列表
- **外部服务层**：各 LLM API（OpenAI/Anthropic/Gemini/Deepseek/OpenRouter 等）

---

## 3.2 技术选型

| 层面 | 技术选型 | 选择理由 |
|-----|---------|---------|
| 框架 | Next.js 14 (App Router) | React 生态，SSG 静态部署，零服务器成本 |
| 语言 | TypeScript 5.x | 类型安全，接口文档即代码 |
| 样式 | Tailwind CSS + CSS Variables | 主题系统需要 CSS 变量，Tailwind 处理通用样式 |
| 状态管理 | Zustand | 轻量，适合客户端优先架构，无需 Redux 复杂度 |
| 本地存储 | IndexedDB (via idb) | 存储会话历史和模板缓存，容量远大于 localStorage |
| LLM 调用 | 统一抽象层（自实现） | 屏蔽不同供应商差异，支持流式输出 |
| 流式处理 | ReadableStream API | 原生浏览器 API，无需额外依赖 |
| 部署 | Vercel（前端）+ CDN（模板） | 零运维，极低成本 |

---

## 3.3 目录结构

```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx
│   ├── page.tsx            # 启动屏，重定向逻辑
│   ├── templates/page.tsx
│   ├── llm/page.tsx
│   ├── roles/page.tsx
│   └── chat/page.tsx
│
├── components/
│   ├── ui/                 # 原子组件（Button/Input/Toggle/Tag...）
│   ├── template/           # 模板选择相关组件
│   ├── llm/                # LLM 配置相关组件
│   ├── role/               # 角色配置相关组件
│   └── chat/               # 讨论界面相关组件
│       ├── MessageBubble.tsx
│       ├── EventCard.tsx
│       ├── InviteCard.tsx
│       ├── TypingIndicator.tsx
│       ├── RosterBar.tsx
│       └── InputArea.tsx
│
├── engine/                 # 讨论引擎（核心）
│   ├── director.ts         # 主持人导演逻辑
│   ├── scheduler.ts        # 角色调度
│   ├── rhythm.ts           # 节奏控制
│   ├── events.ts           # 爽点机制触发
│   └── intent.ts           # 用户意图识别
│
├── llm/                    # LLM 服务抽象层
│   ├── client.ts           # 统一客户端接口
│   ├── providers/
│   │   ├── openai.ts
│   │   ├── anthropic.ts
│   │   ├── gemini.ts
│   │   ├── deepseek.ts
│   │   └── openrouter.ts
│   └── stream.ts           # 流式输出处理
│
├── store/                  # Zustand 状态
│   ├── template.ts
│   ├── llm.ts
│   ├── role.ts
│   ├── chat.ts
│   └── theme.ts
│
├── db/                     # IndexedDB 封装
│   ├── sessions.ts
│   ├── templates.ts
│   └── settings.ts
│
├── types/                  # TypeScript 类型定义
│   ├── template.ts
│   ├── role.ts
│   ├── message.ts
│   ├── llm.ts
│   └── engine.ts
│
└── styles/
    ├── globals.css         # CSS 变量主题系统
    └── themes/             # 各主题变量文件
```

---

## 3.4 核心类型定义

### Message

```typescript
type MessageRole = 'host' | 'character' | 'user' | 'system'

interface Message {
  id: string
  role: MessageRole
  characterId?: string       // 对应角色 ID
  content: string
  timestamp: number
  isStreaming?: boolean       // 流式输出中
  eventType?: 'slap' | 'camp' | 'vote' | 'reverse'
}
```

### EngineState

```typescript
interface EngineState {
  sessionId: string
  templateId: string
  topic: string
  messages: Message[]
  currentTurn: number
  phase: 'opening' | 'developing' | 'climax' | 'closing'
  slapCount: number
  campFormed: boolean
  inviteCount: number
  lastSpeakerId: string
  pendingInvite: boolean
}
```

### LLMConfig

```typescript
interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'gemini' | 'deepseek' | 'openrouter' | 'custom'
  model: string
  apiKey: string
  baseUrl?: string           // 自定义接口地址
  temperature: number
  maxTokens: number
  timeout: number
  stream: boolean
  headers?: Record<string, string>  // 自定义请求头
}
```

### Role

```typescript
interface Role {
  id: string
  name: string
  char: string               // 头像字（最多2字）
  type: string               // 分析视角
  isHost: boolean
  color: 'amber' | 'blue' | 'jade' | 'rose' | 'violet' | 'muted'
  personality: string
  tags: string[]             // 说话风格标签
  catchphrase: string        // 口头禅，/ 分隔
  attitude: string
  systemPrompt: string
  model: string              // 'default' 或具体模型ID
  temperature: string        // 'default' 或具体值
  preview: string[]          // 示例发言
}
```

### Template

```typescript
interface Template {
  id: string
  name: string
  version: string
  icon: string
  description: string
  category: 'history' | 'biz' | 'fairy' | 'custom'
  theme: 'silicon' | 'ink' | 'fairy' | 'space'
  userIdentity: { name: string; avatar: string }
  worldview: {
    background: string
    tone: 'dramatic' | 'humorous' | 'serious' | 'dark'
    entryMessage: string
  }
  roles: Role[]
  events: {
    inviteConditions: string[]
    slapEnabled: boolean
    campEnabled: boolean
    voteEnabled: boolean
    reverseEnabled: boolean
  }
  rhythm: {
    maxTurnsPerRole: number
    maxCharsPerTurn: number
    inviteFrequency: number
    speakerDelay: number
  }
  freeModels?: { id: string; name: string; provider: string }[]
}
```

---

## 3.5 LLM 服务抽象层

所有 LLM 调用通过统一接口，屏蔽供应商差异：

```typescript
interface LLMClient {
  chat(params: ChatParams): Promise<ChatResponse>
  stream(params: ChatParams): AsyncGenerator<string>
  test(): Promise<{ ok: boolean; latency: number; error?: string }>
}

interface ChatParams {
  systemPrompt: string
  messages: { role: 'user' | 'assistant'; content: string }[]
  config: LLMConfig
}

interface ChatResponse {
  content: string
  usage?: { promptTokens: number; completionTokens: number }
}

// 工厂函数，根据配置返回对应 Provider
function createLLMClient(config: LLMConfig): LLMClient
```

> **关键设计**：每个角色调用 LLM 时，系统提示词 = 角色 systemPrompt + 引擎注入的上下文（当前话题、已有观点摘要、导演指令）。不同角色可使用不同 Provider，互相不知道对方的存在。

---

## 3.6 讨论引擎数据流

一轮完整的讨论推进流程：

```
1. 用户发言或系统推进
   └─ 写入 messages，触发引擎

2. intent.ts 识别用户意图类型
   └─ 插话 / 指挥 / 被动

3. director.ts 判断当前 phase 和 engineState
   └─ 评估是否需要邀请用户、触发爽点、推进话题

4. events.ts 检查爽点触发条件
   └─ 打脸 / 站队 / 投票 / 反转

5. scheduler.ts 决定调度哪个角色（0-2个）
   └─ 基于意图 + phase + 角色关系 + 上次发言者

6. rhythm.ts 设置发言字数上限和等待时间
   └─ 注入到 prompt 和延迟参数

7. 构建该角色的完整 prompt
   └─ systemPrompt + 上下文摘要 + 导演指令

8. 调用 LLM，流式写入 messages（isStreaming: true）
   └─ 打字指示器显示，内容逐字出现

9. 流式结束
   └─ isStreaming → false，更新 engineState，进入下一轮判断
```

---

## 3.7 本地存储策略

| 数据 | 存储位置 | 过期策略 | 说明 |
|-----|---------|---------|------|
| API Keys | localStorage（加密） | 永久 | 用户手动删除，不上传 |
| LLM 全局配置 | localStorage | 永久 | 模型、参数等 |
| 主题/上次模板 | localStorage | 永久 | 启动时读取 |
| 模板缓存 | IndexedDB | 7 天 | 服务端下发的模板 JSON |
| 会话历史 | IndexedDB | 30 天 | 最近 50 条会话，按时间清理 |
| 角色配置 | IndexedDB | 永久 | 用户自定义的角色信息 |

---

## 3.8 服务端（极简）

服务端只需要 3 个接口，部署在 CDN + Vercel Functions：

### `GET /api/templates`

```typescript
// 返回模板列表（含版本号，不含完整内容）
Response: {
  templates: Array<{
    id: string
    name: string
    version: string
    theme: string
    category: string
    icon: string
  }>
  updatedAt: string
}
```

### `GET /api/templates/:id`

```typescript
// 返回完整模板 JSON，支持 ETag 缓存
Response: Template  // 完整 Template 对象
```

### `GET /api/models`

```typescript
// 返回推荐免费模型列表（动态更新，无需发版）
Response: {
  freeModels: Array<{
    id: string
    name: string
    provider: string
    rateLimit: string
    quality: 'good' | 'fair' | 'limited'
    chineseSupport: boolean
  }>
  updatedAt: string
}
```

---

## 3.9 CSS 变量主题系统

全部颜色通过 CSS 变量定义，切换主题只需切换 `data-theme` 属性：

```css
/* 硅谷简洁（默认） */
:root {
  --white:    #ffffff;
  --off:      #f7f6f3;
  --off2:     #f0ede8;
  --ink:      #0f0e0c;
  --ink2:     #1c1a17;
  --ink3:     #2e2b26;
  --muted:    #8a8478;
  --faint:    #c8c4bc;
  --line:     #e8e4de;
  --line2:    #d4cfc8;
  --accent:   #e8620a;
  --amber:    #e8620a;  --amber-l: #fff0e8;
  --blue:     #1a6bdc;  --blue-l:  #e8f0ff;
  --jade:     #0f7c5a;  --jade-l:  #e8f5f0;
  --rose:     #c42b4a;  --rose-l:  #ffe8ed;
  --violet:   #6b38c4;  --violet-l:#f0e8ff;
}

/* 水墨暗色 */
[data-theme="ink"] {
  --white:    #1a1612;
  --off:      #201d18;
  --ink:      #f5f0e8;
  --accent:   #c8a96e;
  /* ... */
}

/* 童话梦幻 */
[data-theme="fairy"] {
  --white:    #0e0818;
  --ink:      #f0e8ff;
  --accent:   #c084fc;
  /* ... */
}

/* 星际科技 */
[data-theme="space"] {
  --white:    #020509;
  --ink:      #c8e8ff;
  --accent:   #00c8ff;
  /* ... */
}
```

---

# 04 完整开发计划

## 4.1 开发原则

- 客户端优先，服务端极简，月运营成本控制在百元以内
- 先跑通一个完整模板，再扩展，不追求矩阵覆盖
- 每个 Phase 结束都有可测试的真实产物
- 讨论引擎和 Prompt 工程是最大时间变量，预留充足缓冲

---

## 4.2 Phase 1 · MVP（第 1-8 周）

> **目标**：验证"这种交互有没有人喜欢"。只做三国军师团一个模板，打通完整主链路，第 8 周末做第一次真实用户测试。

### Week 1-2：基础框架

- [ ] Next.js 14 项目初始化，TypeScript 严格模式，ESLint + Prettier
- [ ] 目录结构搭建（按 3.3 节规范），路径别名配置（`@/`）
- [ ] CSS 变量主题系统（4 套主题 + `transition: 0.35s`），全局样式
- [ ] Zustand store 骨架（template / llm / role / chat / theme 各模块）
- [ ] LLM 服务抽象层：统一接口定义 + OpenAI Provider 实现（含流式）
- [ ] IndexedDB 封装（idb 库），sessions / templates / settings 三张表
- [ ] 部署到 Vercel，域名配置，CI/CD 自动部署

### Week 3-4：配置页面

- [ ] 模板选择页：左右布局，模板卡片，分类筛选，主题自动切换，JSON 导入（点击+拖拽）
- [ ] LLM 配置页：5 个子页签，全局模型选择，API Key 管理，自定义模型（Base URL / 模型 ID / 接口格式）
- [ ] 角色配置页：角色列表侧栏，编辑表单（所有字段），添加/删除角色，主持人 toggle
- [ ] 页面间导航，步骤条，状态持久化到 store + IndexedDB
- [ ] 模板 JSON 格式最终确定，硬编码三国军师团初始数据

### Week 5-7：讨论引擎（核心，最大工作量）

- [ ] Engine 状态机：`EngineState` 定义，phase 转换逻辑（opening → developing → climax → closing）
- [ ] `intent.ts`：用户意图识别（插话/指挥/被动，用 LLM 分类或关键词匹配）
- [ ] `scheduler.ts`：基于意图和当前 phase 选择下一个发言角色
- [ ] `director.ts`：主持人 prompt 生成，邀请时机判断，爽点触发检测
- [ ] `rhythm.ts`：发言字数限制注入 prompt，轮次间隔计时
- [ ] `events.ts`：打脸机制（基于关键词检测）+ 站队机制
- [ ] 流式输出接入：消息实时更新，打字指示器，光标动画
- [ ] 错误处理：超时重试，rate limit 友好提示，网络异常兜底

### Week 7-8：讨论 UI + Prompt 调试

- [ ] 聊天界面完整实现：所有消息类型，事件卡，邀请卡，动画
- [ ] 快捷指令动态生成，输入框自适应高度
- [ ] 三国军师团完整 Prompt 调试：5 个角色各自人设验证，白话文强制，发言长度控制
- [ ] 主持人导演逻辑调试：邀请时机、打脸触发、节奏感
- [ ] E2E 测试：3 个不同话题各跑一遍，验证稳定性
- [ ] **第 8 周末**：找 3-5 个真实用户面对面测试，观察"想不想继续"的行为

---

## 4.3 Phase 2 · 完善（第 9-13 周）

### Week 9-10：爽点机制完整实现

- [ ] 投票机制：主持人发起，角色各自表态，统计结果展示
- [ ] 随机反转事件：探子来报 / 叛变 / 极端假设，各一种实现
- [ ] 爽点频率调优：基于 Phase 1 用户测试反馈

### Week 10-11：免费模型接入

- [ ] OpenRouter Provider 实现（含免费模型路由）
- [ ] Gemini Provider 实现（含免费额度支持）
- [ ] Rate limit 处理：指数退避重试，友好错误提示
- [ ] 服务端 `/api/models` 接口，动态推荐免费模型列表
- [ ] 免费模型体验预期管理：UI 上明确标注能力限制

### Week 11-12：模板动态下发

- [ ] 服务端模板接口实现（Vercel Functions + 静态 JSON on CDN）
- [ ] 客户端拉取、版本对比、ETag 缓存、离线可用
- [ ] 新模板 2：创业公司董事会（硅谷主题），验证模板扩展能力
- [ ] 新模板 3：白雪公主智囊（童话主题），验证不同世界观

### Week 12-13：打磨与发布

- [ ] 多模型 Prompt 适配框架：不同模型的指令遵循差异，在 prompt 层标准化处理
- [ ] 性能优化：首屏加载、流式渲染性能
- [ ] 移动端响应式适配
- [ ] 错误监控接入（Sentry）
- [ ] 正式发布，用户数据埋点（完成率/继续率/发言率）

---

## 4.4 Phase 3 · 生态（第 14 周+）

以下模块在 Phase 2 数据验证产品方向后推进：

- [ ] 模板格式标准开放（考虑开源），社区创作者可提交自定义模板
- [ ] 模板市场前端（浏览/预览/一键导入）
- [ ] 内置 LLM 路由（平台代理，按量收费），替代用户自带 Key 模式
- [ ] 企业版入口（私有部署，自定义品牌）
- [ ] 更多供应商：Mistral / Cohere / 本地 Llama

---

## 4.5 工作量估算

| 模块 | 估算工时 | 难度 | 风险说明 |
|-----|---------|------|---------|
| 基础框架 + 配置页面 | 3-4 周 | 中 | 工作量确定，无技术风险 |
| 讨论引擎 | 3-4 周 | 高 | 节奏逻辑和意图识别需大量调试，是最大不确定项 |
| Prompt 调试 | 2-3 周 | 高 | 让角色真正"活"起来需要大量迭代，不可压缩 |
| 讨论 UI | 1-2 周 | 中 | 工作量确定，动画效果可裁剪 |
| 免费模型接入 | 1 周 | 低 | 实现确定，主要工作是 rate limit 处理 |
| 模板动态下发 | 1 周 | 低 | 服务端极简，工作量小 |
| 额外模板制作 | 1-2 周/个 | 高 | Prompt 工程为主，每个模板需独立调试 |

**总计 Phase 1+2**：10-13 周（单人全栈）。乐观 10 周，保守 13 周。

---

## 4.6 完整验收标准

### 角色人设

- [ ] 四个角色说话风格有明显差异，盲测能分辨是谁说的
- [ ] 同一角色在多轮对话中人设保持一致，不飘移
- [ ] 全程白话文，无文言文词汇（测试 10 轮随机话题）
- [ ] 角色之间有化学反应：盟友互相呼应，对手互相较劲

### 讨论引擎

- [ ] 不出现"轮流念稿"感（主持人真的在调度，不是顺序循环）
- [ ] 讨论有 开场→发展→高潮→收敛 的完整弧线
- [ ] 一场讨论中稳定触发 1 次以上爽点
- [ ] 连续跑 3 个不同话题不崩溃，不出现上下文混乱

### 用户参与

- [ ] 用户发言后讨论方向真实改变（不是假响应继续既定流程）
- [ ] 主持人邀请在自然时机触发，不是机械定时
- [ ] "让X反驳他"等直接指挥能被正确执行
- [ ] 用户跳过邀请后讨论能继续推进，不卡住

### 稳定性

- [ ] LLM 返回格式异常时有兜底，不白屏
- [ ] 网络超时有友好提示 + 重试按钮
- [ ] API Key 错误有明确错误信息
- [ ] 连续使用 30 分钟无内存泄漏（Chrome DevTools 验证）

> **最终验收（一句话）**：找一个完全不知道这个产品的人，给他 5 分钟不加任何引导地使用，看完之后问他"想不想再来一场"。答案是想，Phase 1 验收通过。

---

## 4.7 关键验证指标

| 指标 | 定义 | 目标值 | 测量方式 |
|-----|------|--------|---------|
| "下一轮"继续率 | 用户看完一场后主动发起第二场的比率 | **>30%**（最关键） | 埋点统计 |
| 完成率 | 用户是否看完整场讨论（>80% 的消息） | >50% | 消息滚动深度 |
| 用户主动发言率 | 用户从旁观变为发言的比率 | >40% | 消息来源统计 |
| 二次使用率 | 次日回访率 | >20% | 设备 ID 统计 |
| 自发分享率 | 用户截图/分享链接 | >5% | 分享事件埋点 |

---

# 05 开发者接手指南

## 5.1 快速上手

```bash
# 1. 克隆仓库，安装依赖
git clone <repo>
npm install

# 2. 配置环境变量
cp .env.example .env.local
# 填入开发用 API Key（至少一个即可）

# 3. 启动开发服务器
npm run dev

# 4. 访问 http://localhost:3000
# 首次启动默认加载三国军师团模板（硬编码），无需服务端
# 在 LLM 配置页填入 API Key，或启用免费模型，即可进入讨论
```

---

## 5.2 模块边界说明

| 模块 | 职责 | 不负责 |
|-----|------|--------|
| `engine/director.ts` | 决策：调度谁、何时邀请、触发什么事件 | LLM 调用、UI 渲染 |
| `engine/scheduler.ts` | 角色选择算法，输入 EngineState 输出角色 ID | 与 LLM 直接交互 |
| `llm/client.ts` | 统一 LLM 接口，流式处理 | 业务逻辑、角色人设 |
| `store/chat.ts` | 消息列表状态，EngineState 同步 | 引擎逻辑 |
| `components/chat/*` | UI 渲染，只消费 store 数据 | 业务逻辑 |
| `db/*` | IndexedDB 读写封装 | 数据格式定义（在 types/ 中） |

---

## 5.3 关键注意事项

### Prompt 工程

- 所有角色 systemPrompt **必须**包含白话文强制约束，这是产品核心体验之一
- 主持人的 prompt 需要注入动态上下文（当前已有哪些观点，谁和谁有分歧），不能静态
- 发言字数限制要写进 prompt，不能只靠 `maxTokens` 截断（截断会导致句子不完整）
- 不同模型对 system prompt 的遵循能力差异很大，需要分别测试和调优

### 流式输出

- 每个角色的发言**独立流式**，不能并发（并发会打乱顺序）
- 流式写入时消息的 `isStreaming: true`，流结束后改为 `false` 并移除光标
- 网络中断时要有 fallback：显示已收到的部分内容 + 重试提示

### 主题系统

- 所有颜色值只能用 CSS 变量（`var(--white)`），**不能硬编码色值**
- 主题切换通过 `data-theme` 属性，不要用 className 切换
- 新增主题时，所有变量都必须同时提供（约 20 个变量）

### API Key 安全

- Key 只存在 localStorage，加密后存储（推荐 AES-GCM，用设备指纹作为密钥材料）
- Key **绝不能**出现在任何网络请求之外的地方（日志、错误信息、URL 等）
- LLM 请求必须从客户端直接发出，不能经过自己的服务器中转

---

## 5.4 测试重点

按优先级排序：

1. **主持人邀请触发时机**：在 10 个不同话题下测试，确保不是定时触发
2. **打脸机制**：用明确的"A断言X不可能、B证明X可能"场景触发，检验识别准确率
3. **用户直接指挥**：测试"让诸葛亮反驳他"等 10 种不同指令格式
4. **LLM 异常处理**：模拟 rate limit / 超时 / Key 错误 / 返回空内容各场景
5. **长对话稳定性**：跑满 30 轮，检验上下文累积不乱，节奏不退化

---

## 5.5 已知限制与 TODO

| 限制 | 原因 | 计划解决 |
|-----|------|---------|
| 无多设备同步 | 客户端优先架构，会话历史在 IndexedDB | Phase 3 按需加服务端同步 |
| Key 模式限制普通用户 | 普通用户不熟悉 API Key 配置 | 内置 LLM 路由（Phase 3） |
| Prompt 被复制风险 | 模板 JSON 可被导出，prompt 可见 | 长期靠社区生态建壁垒 |
| 免费模型能力有限 | rate limit + 质量不稳定 | 动态推荐列表 + 预期管理 UI |
| 暂无离线 LLM | 需要网络连接访问各供应商 | 支持本地 Ollama（自定义 Base URL） |

---

*文档版本：v1.0 | 最后更新：2026.04 | 基于产品方案 v4 定稿生成*
