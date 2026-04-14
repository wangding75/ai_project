# Phase 1-3: 讨论引擎实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现讨论引擎核心模块，包含状态机、意图识别、角色调度、导演逻辑、节奏控制和爽点机制。

**Architecture:** 讨论引擎完全运行在客户端，由 director.ts 作为决策核心，scheduler.ts 负责角色选择，intent.ts 通过 LLM 分类识别用户意图，events.ts 实现四种爽点机制。引擎通过事件驱动与 UI 层交互。

**Tech Stack:** TypeScript, Vercel AI SDK, Zustand

---

## File Structure

```
src/engine/
├── state.ts        # 引擎状态机定义、Phase 转换逻辑
├── intent.ts      # LLM 意图分类（interrupt/command/passive）
├── scheduler.ts   # 基于意图和 phase 选择下一个发言角色
├── director.ts    # 导演决策：开团、邀请、收束条件判断
├── rhythm.ts      # 发言字数限制、轮次间隔控制
└── events.ts      # 四种爽点机制实现
```

---

## Task 1: Engine State Machine

**Files:**
- Create: `src/engine/state.ts`
- Modify: `src/store/chat.ts` (添加 EngineState 引用)
- Test: `tests/engine/state.test.ts`

- [ ] **Step 1: Write state types and phase transitions**

```typescript
// src/engine/state.ts

export type Phase = 'idle' | 'opening' | 'developing' | 'climax' | 'closing'

export interface EngineState {
  sessionId: string
  templateId: string
  topic: string
  phase: Phase
  currentTurn: number
  maxTurns: number
  lastSpeakerId: string | null
  speakingQueue: string[]
  // 爽点状态
  slapCount: number
  campFormed: boolean
  voteTriggered: boolean
  reverseTriggered: boolean
  // 邀请状态
  inviteCount: number
  pendingInvite: boolean
  // 消息追踪
  messageHistory: Message[]
}

export const PHASE_TRANSITIONS: Record<Phase, Phase[]> = {
  idle: ['opening'],
  opening: ['developing'],
  developing: ['climax', 'closing'],
  climax: ['closing'],
  closing: []
}

export function canTransition(from: Phase, to: Phase): boolean {
  return PHASE_TRANSITIONS[from].includes(to)
}

export function getNextPhase(state: EngineState): Phase {
  const { phase, currentTurn, maxTurns, messageHistory } = state

  if (phase === 'idle') return 'opening'
  if (phase === 'opening') return 'developing'

  // developing → climax: 轮次过半 或 检测到重大分歧
  if (phase === 'developing') {
    const isHalfway = currentTurn >= maxTurns / 2
    const hasMajorConflict = detectMajorConflict(messageHistory)
    if (isHalfway || hasMajorConflict) return 'climax'
    return 'developing'
  }

  // climax → closing: 用户最终表态 或 轮次达到上限
  if (phase === 'climax') {
    const userFinalPosition = detectUserFinalPosition(messageHistory)
    if (userFinalPosition || currentTurn >= maxTurns) return 'closing'
    return 'climax'
  }

  return 'closing'
}

function detectMajorConflict(messages: Message[]): boolean {
  // 检测最近消息中是否存在方向分歧
  const recentMessages = messages.slice(-6)
  const positions = recentMessages
    .filter(m => m.role === 'character')
    .map(m => extractPosition(m.content))

  // 如果有角色明确反对其他角色的观点
  const contradictions = ['但是', '不对', '我不同意', '不一定', '此言差矣']
  return contradictions.some(word =>
    recentMessages.some(m => m.content.includes(word))
  )
}

function detectUserFinalPosition(messages: Message[]): boolean {
  const userMessages = messages.filter(m => m.role === 'user')
  const lastUserMsg = userMessages[userMessages.length - 1]
  if (!lastUserMsg) return false

  const conclusionKeywords = ['总结', '结束', '结论', '就这样', '决定了']
  return conclusionKeywords.some(kw => lastUserMsg.content.includes(kw))
}
```

- [ ] **Step 2: Create store integration**

```typescript
// src/store/chat.ts 新增
interface ChatState {
  engineState: EngineState
  setEngineState: (state: Partial<EngineState>) => void
  transitionPhase: () => void
}
```

- [ ] **Step 3: Write tests**

```typescript
// tests/engine/state.test.ts
describe('Engine State Machine', () => {
  test('idle can transition to opening', () => {
    expect(canTransition('idle', 'opening')).toBe(true)
  })

  test('opening cannot transition to closing directly', () => {
    expect(canTransition('opening', 'closing')).toBe(false)
  })

  test('getNextPhase returns developing after opening', () => {
    const state = createMockEngineState({ phase: 'opening', currentTurn: 0 })
    expect(getNextPhase(state)).toBe('developing')
  })
})
```

- [ ] **Step 4: Commit**

---

## Task 2: Intent Recognition (LLM Classification)

**Files:**
- Create: `src/engine/intent.ts`
- Modify: `src/llm/client.ts` (添加 classifyIntent 调用)
- Test: `tests/engine/intent.test.ts`

- [ ] **Step 1: Write intent types and prompt**

```typescript
// src/engine/intent.ts

export type Intent = 'interrupt' | 'command' | 'passive'

interface IntentClassificationResult {
  intent: Intent
  reasoning: string
  targetCharacterId?: string
}

const INTENT_CLASSIFICATION_PROMPT = `
分析用户最新发言，判断其意图类型：

- interrupt：用户主动插话表达观点，想要参与讨论
- command：用户下达明确指令，如"让X反驳"、"投票"、"换话题"
- passive：用户旁观，等待邀请或继续

用户最新发言：{{userMessage}}

最近讨论上下文：
{{context}}

请返回JSON格式：
{
  "intent": "interrupt|command|passive",
  "reasoning": "判断理由",
  "targetCharacterId": "如果是指令型，指定目标角色ID"
}
`

export async function classifyIntent(
  userMessage: string,
  context: Message[],
  llmClient: LLMClient
): Promise<IntentClassificationResult> {
  const recentContext = context.slice(-10)
  const contextText = recentContext
    .map(m => `${m.role}: ${m.content}`)
    .join('\n')

  const prompt = INTENT_CLASSIFICATION_PROMPT
    .replace('{{userMessage}}', userMessage)
    .replace('{{context}}', contextText)

  const response = await llmClient.complete({
    prompt,
    temperature: 0.3,
    maxTokens: 200
  })

  return parseIntentResponse(response)
}

function parseIntentResponse(response: string): IntentClassificationResult {
  try {
    const jsonMatch = response.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0])
    }
  } catch (e) {
    // parsing failed
  }

  // Fallback
  return { intent: 'passive', reasoning: '解析失败，默认被动' }
}
```

- [ ] **Step 2: Write unit tests**

```typescript
// tests/engine/intent.test.ts
describe('Intent Classification', () => {
  test('classifies interrupt when user expresses opinion', async () => {
    const mockLLM = createMockLLMClient('{"intent":"interrupt","reasoning":"用户表达了明确观点"}')
    const result = await classifyIntent('我认为这个问题应该这样做', [], mockLLM)
    expect(result.intent).toBe('interrupt')
  })

  test('classifies command when user gives directive', async () => {
    const mockLLM = createMockLLMClient('{"intent":"command","reasoning":"用户要求投票","targetCharacterId":"zhangfei"}')
    const result = await classifyIntent('发起投票', [], mockLLM)
    expect(result.intent).toBe('command')
  })
})
```

- [ ] **Step 3: Commit**

---

## Task 3: Role Scheduler

**Files:**
- Create: `src/engine/scheduler.ts`
- Test: `tests/engine/scheduler.test.ts`

- [ ] **Step 1: Write scheduler logic**

```typescript
// src/engine/scheduler.ts

interface ScheduleResult {
  nextSpeakerId: string
  reasoning: string
  shouldInviteUser: boolean
}

export function selectNextSpeaker(
  intent: Intent,
  state: EngineState,
  roles: Role[],
  userMessage?: string
): ScheduleResult {
  const { lastSpeakerId, speakingQueue, phase } = state

  // command 类型：直接调度指定角色
  if (intent === 'command' && userMessage) {
    const targetId = extractTargetFromCommand(userMessage, roles)
    if (targetId) {
      return {
        nextSpeakerId: targetId,
        reasoning: `用户指令：调度 ${targetId}`,
        shouldInviteUser: false
      }
    }
  }

  // passive 类型：正常轮转
  if (intent === 'passive') {
    return selectByRoundRobin(state, roles)
  }

  // interrupt 类型：调度与用户观点相关的角色
  if (intent === 'interrupt' && userMessage) {
    const relevantRole = selectRelevantRole(userMessage, roles, lastSpeakerId)
    return {
      nextSpeakerId: relevantRole,
      reasoning: '用户插话，选择相关角色回应',
      shouldInviteUser: false
    }
  }

  // 默认：轮转
  return selectByRoundRobin(state, roles)
}

function selectByRoundRobin(state: EngineState, roles: Role[]): ScheduleResult {
  const { lastSpeakerId, speakingQueue } = state
  const activeRoles = roles.filter(r => !r.isHost)

  if (!lastSpeakerId) {
    // 第一个发言：主持人
    const host = roles.find(r => r.isHost)
    return { nextSpeakerId: host!.id, reasoning: '开场', shouldInviteUser: false }
  }

  // 维护一个简单的轮转队列
  const currentIndex = speakingQueue.indexOf(lastSpeakerId)
  const nextIndex = (currentIndex + 1) % activeRoles.length
  const nextSpeakerId = speakingQueue[nextIndex] || activeRoles[0].id

  return {
    nextSpeakerId,
    reasoning: `轮转到 ${nextSpeakerId}`,
    shouldInviteUser: false
  }
}

function selectRelevantRole(
  userMessage: string,
  roles: Role[],
  lastSpeakerId: string | null
): string {
  // 简化实现：根据消息情感选择角色
  const activeRoles = roles.filter(r => !r.isHost)
  const lastSpeaker = roles.find(r => r.id === lastSpeakerId)

  // 如果上一个发言者与用户观点相反，选择对立方
  if (lastSpeaker) {
    const opposite = findOppositeRole(lastSpeaker, activeRoles)
    if (opposite) return opposite.id
  }

  // 否则随机选择下一个
  const available = activeRoles.filter(r => r.id !== lastSpeakerId)
  return available[Math.floor(Math.random() * available.length)].id
}

function findOppositeRole(role: Role, others: Role[]): Role | undefined {
  // 简化：根据角色属性查找对立方
  return others.find(r => r.name !== role.name)
}

function extractTargetFromCommand(command: string, roles: Role[]): string | null {
  // 从命令中提取目标角色名
  const roleNames = roles.map(r => r.name)
  const mentioned = roleNames.find(name => command.includes(name))
  if (mentioned) {
    return roles.find(r => r.name === mentioned)?.id || null
  }

  // 通用指令检测
  if (command.includes('投票')) return 'vote'
  if (command.includes('反驳')) return 'opponent'
  return null
}
```

- [ ] **Step 2: Write tests**

```typescript
// tests/engine/scheduler.test.ts
describe('Role Scheduler', () => {
  test('selects host for first turn', () => {
    const result = selectNextSpeaker('passive', createMockState({ lastSpeakerId: null }), mockRoles)
    expect(result.nextSpeakerId).toBe('host')
  })

  test('command intent extracts target role', () => {
    const result = selectNextSpeaker('command', createMockState({}), mockRoles, '让诸葛亮反驳')
    expect(result.nextSpeakerId).toBe('zhugeliang')
  })
})
```

- [ ] **Step 3: Commit**

---

## Task 4: Director Logic

**Files:**
- Create: `src/engine/director.ts`
- Modify: `src/engine/scheduler.ts` (集成导演判断)
- Test: `tests/engine/director.test.ts`

- [ ] **Step 1: Write director decision logic**

```typescript
// src/engine/director.ts

export interface DirectorDecision {
  action: 'continue' | 'invite_user' | 'trigger_event' | 'conclude'
  eventType?: 'slap' | 'camp' | 'vote' | 'reverse'
  reasoning: string
}

export function makeDirectorDecision(
  state: EngineState,
  latestMessage?: Message
): DirectorDecision {
  const { phase, inviteCount, messageHistory } = state

  // Phase 转换判断
  if (phase === 'opening' && messageHistory.length >= 3) {
    return { action: 'continue', reasoning: '开场完成，进入发展阶段' }
  }

  // 收束条件
  if (shouldConclude(state)) {
    return { action: 'conclude', reasoning: '满足收束条件' }
  }

  // 邀请用户时机判断
  if (shouldInviteUser(state)) {
    return {
      action: 'invite_user',
      reasoning: '检测到邀请时机',
      eventType: undefined
    }
  }

  // 爽点检测
  const event = detectSparkleEvent(state, latestMessage)
  if (event) {
    return { action: 'trigger_event', eventType: event, reasoning: `触发爽点: ${event}` }
  }

  return { action: 'continue', reasoning: '正常推进' }
}

function shouldConclude(state: EngineState): boolean {
  const { currentTurn, maxTurns, messageHistory } = state

  // 轮次达到上限
  if (currentTurn >= maxTurns) return true

  // 用户发出结束信号
  const lastUserMsg = messageHistory.filter(m => m.role === 'user').pop()
  if (lastUserMsg) {
    const conclusionKeywords = ['总结', '结束', '结论', '就这样', '决定了']
    if (conclusionKeywords.some(kw => lastUserMsg.content.includes(kw))) {
      return true
    }
  }

  // 角色一致同意（无分歧）
  if (currentTurn > 3 && hasConsensus(messageHistory)) {
    return true
  }

  return false
}

function shouldInviteUser(state: EngineState): boolean {
  const { inviteCount, messageHistory, phase } = state

  // 最多邀请3次
  if (inviteCount >= 3) return false

  // 只在 developing 和 climax 阶段邀请
  if (phase !== 'developing' && phase !== 'climax') return false

  const recentMessages = messageHistory.slice(-6)

  // 出现观点分歧
  if (hasDivergence(recentMessages)) return true

  // 角色质疑用户观点
  if (hasCharacterQuestioningUser(recentMessages)) return true

  // 讨论到达分叉点
  if (hasForkPoint(recentMessages)) return true

  // 出现反转或意外信息
  if (hasReversal(recentMessages)) return true

  return false
}

function hasDivergence(messages: Message[]): boolean {
  const contradictions = ['但是', '不对', '我不同意', '不一定', '此言差矣', '值得商榷']
  return messages.some(m => contradictions.some(c => m.content.includes(c)))
}

function hasCharacterQuestioningUser(messages: Message[]): boolean {
  const questionPatterns = ['你怎么看', '主公以为', '将军意下如何', '以为如何']
  return messages.some(m =>
    m.role === 'character' &&
    questionPatterns.some(p => m.content.includes(p))
  )
}

function hasForkPoint(messages: Message[]): boolean {
  const forkPatterns = ['有两条路', '可以选择', '要么...要么', '两个方案', '甲乙丙丁']
  return messages.some(m =>
    forkPatterns.some(p => m.content.includes(p))
  )
}

function hasReversal(messages: Message[]): boolean {
  const reversalPatterns = ['忽然', '意外', '传来', '不曾想', '变故', '突变']
  return messages.some(m =>
    reversalPatterns.some(p => m.content.includes(p))
  )
}

function hasConsensus(messages: Message[]): boolean {
  // 简化：连续3轮无反对意见视为共识
  const recent = messages.slice(-6).filter(m => m.role === 'character')
  const contradictions = ['但是', '不对', '我不同意', '不一定']
  const hasContradiction = recent.some(m =>
    contradictions.some(c => m.content.includes(c))
  )
  return !hasContradiction && recent.length >= 3
}
```

- [ ] **Step 2: Write director tests**

```typescript
// tests/engine/director.test.ts
describe('Director Decision Logic', () => {
  test('invites user when divergence detected', () => {
    const state = createMockState({
      phase: 'developing',
      inviteCount: 0,
      messageHistory: [
        { role: 'character', content: '我认为应该进攻' },
        { role: 'character', content: '但是敌人实力强大' }
      ]
    })
    const decision = makeDirectorDecision(state)
    expect(decision.action).toBe('invite_user')
  })

  test('concludes when max turns reached', () => {
    const state = createMockState({ currentTurn: 20, maxTurns: 20 })
    const decision = makeDirectorDecision(state)
    expect(decision.action).toBe('conclude')
  })
})
```

- [ ] **Step 3: Commit**

---

## Task 5: Rhythm Control

**Files:**
- Create: `src/engine/rhythm.ts`
- Modify: `src/engine/director.ts` (注入节奏约束)
- Test: `tests/engine/rhythm.test.ts`

- [ ] **Step 1: Write rhythm control**

```typescript
// src/engine/rhythm.ts

export interface RhythmConfig {
  maxCharsPerTurn: number
  minCharsPerTurn: number
  speakerDelay: number
  maxTurnsPerRole: number
}

export const DEFAULT_RHYTHM: RhythmConfig = {
  maxCharsPerTurn: 200,
  minCharsPerTurn: 30,
  speakerDelay: 800,
  maxTurnsPerRole: 4
}

export function injectRhythmConstraints(
  systemPrompt: string,
  config: RhythmConfig,
  role: Role
): string {
  return `${systemPrompt}

## 发言约束
- 字数限制：${config.minCharsPerTurn}-${config.maxCharsPerTurn} 字
- 简洁有力，避免冗长
- 间隔 ${config.speakerDelay}ms 后下一位发言
- 每个角色最多连续发言 ${config.maxTurnsPerRole} 轮
`
}

export function shouldSkipRole(
  roleId: string,
  state: EngineState,
  config: RhythmConfig
): boolean {
  const recentSpeakers = state.messageHistory
    .slice(-config.maxTurnsPerRole * 2)
    .filter(m => m.characterId === roleId)

  // 该角色连续发言超过限制
  if (recentSpeakers.length >= config.maxTurnsPerRole) {
    return true
  }

  return false
}

export function getSpeakerDelay(state: EngineState): number {
  // climax 阶段加快节奏
  if (state.phase === 'climax') {
    return DEFAULT_RHYTHM.speakerDelay * 0.7
  }
  return DEFAULT_RHYTHM.speakerDelay
}
```

- [ ] **Step 2: Write tests**

- [ ] **Step 3: Commit**

---

## Task 6: Sparkle Events (爽点机制)

**Files:**
- Create: `src/engine/events.ts`
- Modify: `src/engine/director.ts` (集成爽点检测)
- Test: `tests/engine/events.test.ts`

- [ ] **Step 1: Write all four sparkle mechanisms**

```typescript
// src/engine/events.ts

export type SparkleEvent = 'slap' | 'camp' | 'vote' | 'reverse'

interface SparkleResult {
  event: SparkleEvent
  triggered: boolean
  details: Record<string, unknown>
}

// ============ 打脸机制 ============
// 触发：角色B的论据直接推翻角色A之前的明确断言
export function detectSlap(
  currentMessage: Message,
  messageHistory: Message[]
): SparkleResult {
  const recentHistory = messageHistory.slice(-10).filter(m => m.role === 'character')

  // 查找当前消息反驳的内容
  const contradictions = ['但是', '不对', '此言差矣', '错了', '事实并非如此']
  const hasSlap = contradictions.some(c => currentMessage.content.includes(c))

  if (!hasSlap) {
    return { event: 'slap', triggered: false, details: {} }
  }

  // 检查是否有明确断言被反驳
  const previousAssertions = recentHistory
    .filter(m => containsAssertion(m.content))
    .pop()

  if (!previousAssertions) {
    return { event: 'slap', triggered: false, details: {} }
  }

  return {
    event: 'slap',
    triggered: true,
    details: {
      targetCharacter: previousAssertions.characterId,
      targetContent: previousAssertions.content
    }
  }
}

function containsAssertion(content: string): boolean {
  // 判断消息是否包含明确断言
  const assertionPatterns = ['应该', '必须', '一定', '肯定', '必然', '确是']
  return assertionPatterns.some(p => content.includes(p))
}

// ============ 站队机制 ============
// 触发：出现重大方向分歧，形成阵营
export function detectCampFormation(
  messageHistory: Message[]
): SparkleResult {
  const recent = messageHistory.slice(-8).filter(m => m.role === 'character')

  // 统计正反方关键词
  const proKeywords = ['支持', '赞成', '应该', '可行', '同意']
  const conKeywords = ['反对', '不行', '不可', '不应', '不同意']

  let proCount = 0
  let conCount = 0
  const proSpeakers: string[] = []
  const conSpeakers: string[] = []

  recent.forEach(m => {
    const isPro = proKeywords.some(k => m.content.includes(k))
    const isCon = conKeywords.some(k => m.content.includes(k))

    if (isPro && !isCon) {
      proCount++
      if (m.characterId) proSpeakers.push(m.characterId)
    }
    if (isCon && !isPro) {
      conCount++
      if (m.characterId) conSpeakers.push(m.characterId)
    }
  })

  // 双方各有人发言且超过2次
  if (proCount >= 2 && conCount >= 2) {
    return {
      event: 'camp',
      triggered: true,
      details: { proSpeakers, conSpeakers, proCount, conCount }
    }
  }

  return { event: 'camp', triggered: false, details: {} }
}

// ============ 投票机制 ============
// 触发：某议题争论3+轮仍无定论
export function detectVoteTrigger(
  messageHistory: Message[]
): SparkleResult {
  const recent = messageHistory.slice(-12).filter(m => m.role === 'character')

  // 检测是否围绕同一议题反复争论
  const topicMentions = countTopicMentions(recent)

  // 3+轮无定论
  if (topicMentions >= 3 && !hasConclusion(recent)) {
    return {
      event: 'vote',
      triggered: true,
      details: { roundsWithoutConclusion: topicMentions }
    }
  }

  return { event: 'vote', triggered: false, details: {} }
}

function countTopicMentions(messages: Message[]): number {
  // 简化：连续讨论超过3条消息视为反复争论
  return Math.floor(messages.length / 2)
}

function hasConclusion(messages: Message[]): boolean {
  const conclusionPatterns = ['结论是', '总之', '所以', '因此', '一言以蔽之']
  return messages.some(m =>
    conclusionPatterns.some(p => m.content.includes(p))
  )
}

// ============ 反转机制 ============
// 触发：探子来报/叛变/极端假设
export function detectReverse(
  messageHistory: Message[]
): SparkleResult {
  const recent = messageHistory.slice(-6)

  const reversePatterns = [
    { pattern: '探子来报', type: 'spy_report' },
    { pattern: '忽然', type: 'sudden_change' },
    { pattern: '不曾想', type: 'unexpected' },
    { pattern: '意外', type: 'accident' },
    { pattern: '叛变', type: 'betrayal' },
    { pattern: '假设', type: 'hypothesis' }
  ]

  for (const msg of recent) {
    for (const { pattern, type } of reversePatterns) {
      if (msg.content.includes(pattern)) {
        return {
          event: 'reverse',
          triggered: true,
          details: { reverseType: type, triggerWord: pattern }
        }
      }
    }
  }

  return { event: 'reverse', triggered: false, details: {} }
}

// ============ 统一入口 ============
export function detectSparkleEvent(
  state: EngineState,
  currentMessage?: Message
): SparkleEvent | null {
  const { messageHistory, slapCount, campFormed, voteTriggered, reverseTriggered } = state

  // 每个事件最多触发一次
  if (currentMessage && slapCount === 0) {
    const slapResult = detectSlap(currentMessage, messageHistory)
    if (slapResult.triggered) return 'slap'
  }

  if (!campFormed) {
    const campResult = detectCampFormation(messageHistory)
    if (campResult.triggered) return 'camp'
  }

  if (!voteTriggered) {
    const voteResult = detectVoteTrigger(messageHistory)
    if (voteResult.triggered) return 'vote'
  }

  if (!reverseTriggered) {
    const reverseResult = detectReverse(messageHistory)
    if (reverseResult.triggered) return 'reverse'
  }

  return null
}
```

- [ ] **Step 2: Write tests for each mechanism**

```typescript
// tests/engine/events.test.ts
describe('Sparkle Events', () => {
  describe('Slap Detection', () => {
    test('triggers when contradiction detected', () => {
      const currentMsg = { role: 'character' as const, content: '此言差矣，事实并非如此', characterId: 'zhangfei' }
      const history = [
        { role: 'character' as const, content: '将军应该速攻', characterId: 'zhugeliang' }
      ]
      const result = detectSlap(currentMsg, history)
      expect(result.triggered).toBe(true)
    })
  })

  describe('Camp Formation', () => {
    test('triggers when both sides have 2+ statements', () => {
      const history = [
        { role: 'character', content: '我支持这个方案', characterId: 'a' },
        { role: 'character', content: '我反对', characterId: 'b' },
        { role: 'character', content: '我觉得可行', characterId: 'a' },
        { role: 'character', content: '我仍然反对', characterId: 'b' }
      ]
      const result = detectCampFormation(history)
      expect(result.triggered).toBe(true)
    })
  })

  describe('Vote Trigger', () => {
    test('triggers after 3+ rounds without conclusion', () => {
      const history = Array(6).fill({ role: 'character' as const, content: '我觉得...', characterId: 'a' })
      const result = detectVoteTrigger(history)
      expect(result.triggered).toBe(true)
    })
  })
})
```

- [ ] **Step 3: Commit**

---

## Task 7: Engine Integration

**Files:**
- Create: `src/engine/index.ts` (统一导出)
- Create: `src/engine/Engine.ts` (引擎主类)
- Modify: `src/store/chat.ts` (引擎状态同步)
- Test: `tests/engine/integration.test.ts`

- [ ] **Step 1: Create Engine class**

```typescript
// src/engine/Engine.ts

export class DiscussionEngine {
  private state: EngineState
  private llmClient: LLMClient
  private roles: Role[]
  private rhythmConfig: RhythmConfig

  constructor(config: EngineConfig) {
    this.state = createInitialState(config)
    this.llmClient = config.llmClient
    this.roles = config.roles
    this.rhythmConfig = config.rhythm || DEFAULT_RHYTHM
  }

  async onUserMessage(message: string): Promise<EngineDecision> {
    // 1. 识别用户意图
    const intentResult = await classifyIntent(message, this.state.messageHistory, this.llmClient)

    // 2. 导演决策
    const directorDecision = makeDirectorDecision(this.state, {
      role: 'user',
      content: message,
      timestamp: Date.now()
    })

    // 3. 更新状态
    this.state.messageHistory.push({
      id: generateId(),
      role: 'user',
      content: message,
      timestamp: Date.now()
    })
    this.state.currentTurn++

    // 4. 处理导演决策
    if (directorDecision.action === 'conclude') {
      return { type: 'conclude', reasoning: directorDecision.reasoning }
    }

    if (directorDecision.action === 'invite_user') {
      this.state.inviteCount++
      this.state.pendingInvite = true
      return { type: 'invite', reasoning: directorDecision.reasoning }
    }

    if (directorDecision.action === 'trigger_event') {
      this.markEventTriggered(directorDecision.eventType!)
      return { type: 'event', eventType: directorDecision.eventType!, reasoning: directorDecision.reasoning }
    }

    // 5. 调度下一个角色
    const scheduleResult = selectNextSpeaker(
      intentResult.intent,
      this.state,
      this.roles,
      message
    )

    // 6. 检查是否该用户发言
    if (scheduleResult.shouldInviteUser) {
      this.state.inviteCount++
      return { type: 'invite', reasoning: scheduleResult.reasoning }
    }

    // 7. 推进到下一个 phase
    const nextPhase = getNextPhase(this.state)
    if (nextPhase !== this.state.phase) {
      this.state.phase = nextPhase
    }

    return {
      type: 'speak',
      characterId: scheduleResult.nextSpeakerId,
      reasoning: scheduleResult.reasoning
    }
  }

  private markEventTriggered(event: SparkleEvent): void {
    switch (event) {
      case 'slap': this.state.slapCount++; break
      case 'camp': this.state.campFormed = true; break
      case 'vote': this.state.voteTriggered = true; break
      case 'reverse': this.state.reverseTriggered = true; break
    }
  }

  getState(): EngineState {
    return { ...this.state }
  }
}
```

- [ ] **Step 2: Create index export**

```typescript
// src/engine/index.ts
export * from './state'
export * from './intent'
export * from './scheduler'
export * from './director'
export * from './rhythm'
export * from './events'
export { DiscussionEngine } from './Engine'
```

- [ ] **Step 3: Integration test**

```typescript
// tests/engine/integration.test.ts
describe('Engine Integration', () => {
  test('full discussion flow', async () => {
    const engine = new DiscussionEngine(mockConfig)

    // Opening phase
    let decision = await engine.onUserMessage('开始讨论')
    expect(decision.type).toBe('speak')

    // User participates
    decision = await engine.onUserMessage('我认为应该进攻')
    expect(['speak', 'invite', 'event']).toContain(decision.type)
  })
})
```

- [ ] **Step 4: Commit**

---

## 验收标准

- [ ] 状态机正确转换：idle → opening → developing → climax → closing
- [ ] 意图识别正确分类 interrupt/command/passive 三种类型
- [ ] 角色调度正确处理轮转和指令
- [ ] 导演决策正确判断邀请时机和收束条件
- [ ] 打脸机制在检测到反驳时触发
- [ ] 站队机制在双方各2+发言时触发
- [ ] 投票机制在3+轮无定论时触发
- [ ] 反转机制在检测到特定关键词时触发
- [ ] 节奏控制正确限制字数和轮次
- [ ] 引擎与 store 正确同步状态

---

*Phase 1-3 计划版本：v1.0 | 创建日期：2026-04-06*
