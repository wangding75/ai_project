# Phase 1-4: Discussion UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现讨论主界面 UI，包括消息流、事件卡、邀请卡、输入区

**Architecture:** React 组件化设计，消息类型驱动渲染，CSS 变量主题系统

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, Zustand

## File Structure

```
src/components/chat/
├── MessageBubble.tsx    - 消息气泡
├── EventCard.tsx       - 事件卡 (打脸/站队/投票/反转)
├── InviteCard.tsx       - 主持人邀请卡
├── TypingIndicator.tsx - 打字中指示器
├── RosterBar.tsx        - 角色栏
├── InputArea.tsx        - 输入区
├── TopBar.tsx           - 顶栏
└── ChatContainer.tsx    - 聊天容器
```

---

## Task 1: 消息气泡组件 (MessageBubble)

### Component Spec

**File:** `src/components/chat/MessageBubble.tsx`

**Props Interface:**
```typescript
interface MessageBubbleProps {
  id: string;
  type: 'host' | 'character' | 'user' | 'system';
  content: string;
  character?: {
    name: string;
    color: string;
    avatar?: string;
  };
  isStreaming?: boolean;
  timestamp?: Date;
}
```

**Visual Styles (per type):**

| Type | Background | Text | Alignment | Extra |
|------|-----------|------|-----------|-------|
| host | `var(--color-host-bg)` | `var(--color-host-text)` | left | italic |
| character | `var(--color-character-bg)` | white | left | `border-left: 3px solid var(--color-character)` |
| user | `var(--color-user-bg)` | white | right | — |
| system | transparent | `var(--color-muted)` | center | italic |

**States:**
- Default: static render
- Streaming: cursor blink animation at end of text
- Entering: `animate-fadeIn` (200ms ease-out)

**Animation:**
```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fadeIn { animation: fadeIn 200ms ease-out forwards; }
```

**Streaming cursor:**
```css
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
.streaming-cursor::after {
  content: '|';
  animation: blink 1s infinite;
  color: inherit;
}
```

---

## Task 2: 事件卡组件 (EventCard)

### Component Spec

**File:** `src/components/chat/EventCard.tsx`

**Props Interface:**
```typescript
type EventType = 'faceSlap' | 'standUp' | 'vote' | 'twist';

interface EventCardProps {
  id: string;
  eventType: EventType;
  title: string;
  description: string;
  actor?: string;      // who triggered it
  target?: string;     // affected character
  votes?: number;       // for vote type
  timestamp?: Date;
}
```

**Visual Styles (per event type):**

| Event Type | Left Border | Background | Accent Color |
|------------|------------|------------|--------------|
| faceSlap (打脸) | `4px solid var(--color-face-slap)` | `var(--color-face-slap-bg)` | rose |
| standUp (站队) | `4px solid var(--color-stand-up)` | `var(--color-stand-up-bg)` | amber |
| vote (投票) | `4px solid var(--color-vote)` | `var(--color-vote-bg)` | blue |
| twist (反转) | `4px solid var(--color-twist)` | `var(--color-twist-bg)` | purple |

**Structure:**
```
┌─────────────────────────────────────┐
│ [ICON] 标题                    时间  │
│ 描述文字...                          │
│ [可选: 投票数 / 角色标签]            │
└─────────────────────────────────────┘
```

**Animation:** `animate-fadeUp` (300ms ease-out)

```css
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fadeUp { animation: fadeUp 300ms ease-out forwards; }
```

---

## Task 3: 邀请卡组件 (InviteCard)

### Component Spec

**File:** `src/components/chat/InviteCard.tsx`

**Props Interface:**
```typescript
interface InviteCardProps {
  id: string;
  hostName: string;
  topic: string;
  onRespond: () => void;
  onSkip: () => void;
}
```

**Visual Styles:**
- Background: `var(--color-invite-bg)` (pure black `#0a0a0a`)
- Text: white
- Buttons:
  - Primary (回应): white bg, black text, `hover:-translate-y-0.5 hover:shadow-lg`
  - Secondary (跳过): transparent bg, white border, white text

**Structure:**
```
┌─────────────────────────────────────┐
│  [HOST NAME] 邀请你参与讨论           │
│                                     │
│  话题: [TOPIC]                      │
│                                     │
│  [  回应  ]      [  跳过  ]          │
└─────────────────────────────────────┘
```

**Animation:** `animate-fadeIn` (250ms ease-out)

---

## Task 4: 打字指示器 (TypingIndicator)

### Component Spec

**File:** `src/components/chat/TypingIndicator.tsx`

**Props Interface:**
```typescript
interface TypingIndicatorProps {
  characterName: string;
  characterColor?: string;
}
```

**Visual:**
- Three dots with staggered bounce/pulse animation
- Shows character name label above or beside dots
- Dots color matches character color

**Animation:**
```css
@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}
.dot-1 { animation: bounce 1.4s infinite 0ms; }
.dot-2 { animation: bounce 1.4s infinite 160ms; }
.dot-3 { animation: bounce 1.4s infinite 320ms; }
```

**Animation:** `animate-fadeIn` (150ms ease-out)

---

## Task 5: 角色栏 (RosterBar)

### Component Spec

**File:** `src/components/chat/RosterBar.tsx`

**Props Interface:**
```typescript
interface RosterBarProps {
  characters: Array<{
    id: string;
    name: string;
    color: string;
    avatar?: string;
    role: 'host' | 'character' | 'user';
  }>;
  activeSpeakerId?: string;   // id of currently speaking character
}
```

**Visual:**
- Horizontal scrollable bar
- Host (主持人) first, then characters, User (用户) last
- Active speaker: bottom border `3px solid var(--color-active)` + subtle glow
- Character pills show avatar + name
- Divider dots between items

**Layout:**
```
[👤 主持人] ● [👤 角色A] ● [👤 角色B] ● [👤 用户]
```

**Active state:**
```css
.active-speaker {
  border-bottom: 3px solid var(--color-active);
  box-shadow: 0 2px 8px var(--color-active-glow);
}
```

---

## Task 6: 输入区 (InputArea)

### Component Spec

**File:** `src/components/chat/InputArea.tsx`

**Props Interface:**
```typescript
interface InputAreaProps {
  mode: 'interrupt' | 'direct' | 'decide';
  onModeChange: (mode: 'interrupt' | 'direct' | 'decide') => void;
  onSend: (content: string) => void;
  quickCommands?: string[];   // dynamically generated chips
  disabled?: boolean;
}
```

**Mode Tabs (顶部标签):**
- 插话 (Interrupt): violet accent
- 指挥 (Direct): amber accent
- 定夺 (Decide): emerald accent

**Textarea:**
- Min height: 42px
- Max height: 120px
- Auto-resize based on content
- Placeholder: "输入你的回复..."
- Border: `var(--color-border)`, focus: `var(--color-focus-ring)`

**Send Button:**
- Background: `var(--color-send-btn)` (#0a0a0a)
- Icon: white arrow up
- Hover: `-translate-y-0.5 + shadow-lg`
- Disabled: opacity 50%, no hover

**Quick Command Chips:**
- Horizontal scrollable
- Chips: `border var(--color-chip-border)`, bg transparent
- Tap to insert command text into textarea

**Structure:**
```
┌─────────────────────────────────────────┐
│ [插话]  [指挥]  [定夺]                    │
├─────────────────────────────────────────┤
│ [chip1] [chip2] [chip3] ...             │
├─────────────────────────────────────────┤
│                                         │
│  textarea                               │
│                                         │
├─────────────────────────────────────────┤
│                              [ ↑ 发送 ] │
└─────────────────────────────────────────┘
```

---

## Task 7: 顶栏 (TopBar)

### Component Spec

**File:** `src/components/chat/TopBar.tsx`

**Props Interface:**
```typescript
interface TopBarProps {
  sceneName: string;
  currentTopic: string;
  discussionStatus: 'idle' | 'active' | 'paused';
  onNewDiscussion: () => void;
  onChangeTopic: () => void;
  onViewCharacters: () => void;
}
```

**Layout:**

```
┌────────────────────────────────────────────────────────────┐
│ [SCENE BADGE]  话题: [CURRENT TOPIC]    [状态] [👤] [📋] [+] │
└────────────────────────────────────────────────────────────┘
```

**Left side:**
- Scene badge: pill shape with scene name
- Topic pill: "话题: {currentTopic}"

**Right side:**
- Status indicator:
  - idle: gray dot
  - active: pulsing green dot
  - paused: amber dot
- Character button (view/manage)
- Theme button (settings)
- New discussion button (+ icon)

**Styling:**
- Background: `var(--color-topbar-bg)` with bottom border
- Height: 56px
- Sticky top position

---

## Task 8: 聊天容器 (ChatContainer)

### Component Spec

**File:** `src/components/chat/ChatContainer.tsx`

**Props Interface:**
```typescript
interface ChatContainerProps {
  messages: Array<MessageBubbleProps | EventCardProps | InviteCardProps>;
  isTyping?: boolean;
  typingCharacter?: string;
  activeSpeakerId?: string;
  currentUserId: string;
}
```

**Responsibilities:**
1. Render scrollable message list
2. Auto-scroll to bottom on new messages (smooth scroll)
3. Handle empty state (show welcome illustration + prompt)
4. Integrate RosterBar at top
5. Integrate TopBar
6. Integrate InputArea at bottom

**Empty State:**
```
┌─────────────────────────────────────┐
│                                     │
│        [illustration]                │
│                                     │
│   还没有消息，开始讨论吧             │
│                                     │
│   [开始新讨论]                       │
│                                     │
└─────────────────────────────────────┘
```

**Scroll Behavior:**
- Use `ref` + `scrollIntoView({ behavior: 'smooth' })` on new message
- Detect if user is scrolled up (don't auto-scroll if user is reading history)

**Layout (full height):**
```
┌─────────────────────────────────────┐
│           TopBar                    │
├─────────────────────────────────────┤
│           RosterBar                 │
├─────────────────────────────────────┤
│                                     │
│                                     │
│         Message List                │
│         (scrollable)                │
│                                     │
│                                     │
├─────────────────────────────────────┤
│           InputArea                 │
└─────────────────────────────────────┘
```

---

## Theme CSS Variables (Reference)

Add to `src/styles/globals.css` or theme file:

```css
:root {
  /* Message types */
  --color-host-bg: #f5f0eb;
  --color-host-text: #4a3728;
  --color-character-bg: #1a1a1a;
  --color-character-text: #ffffff;
  --color-user-bg: #0a0a0a;
  --color-user-text: #ffffff;
  --color-system-text: #888888;

  /* Event cards */
  --color-face-slap: #e11d48;
  --color-face-slap-bg: #fff1f2;
  --color-stand-up: #f59e0b;
  --color-stand-up-bg: #fffbeb;
  --color-vote: #3b82f6;
  --color-vote-bg: #eff6ff;
  --color-twist: #8b5cf6;
  --color-twist-bg: #f5f3ff;

  /* Invite card */
  --color-invite-bg: #0a0a0a;
  --color-send-btn: #0a0a0a;

  /* UI chrome */
  --color-topbar-bg: #ffffff;
  --color-border: #e5e5e5;
  --color-focus-ring: #3b82f6;
  --color-muted: #888888;
  --color-active: #22c55e;
  --color-active-glow: rgba(34, 197, 94, 0.3);

  /* Chips */
  --color-chip-border: #d4d4d4;
}
```

---

## Implementation Order

1. **MessageBubble** — base component, no dependencies
2. **EventCard** — independent card component
3. **InviteCard** — independent card component
4. **TypingIndicator** — simple animated component
5. **RosterBar** — uses character data, no message deps
6. **InputArea** — form component with state
7. **TopBar** — layout chrome
8. **ChatContainer** — integrates all above

---

## Testing Checklist

- [ ] All 4 message types render with correct styles
- [ ] Streaming message shows blinking cursor
- [ ] All 4 event card types render with correct colors
- [ ] InviteCard buttons are functional
- [ ] TypingIndicator dots animate with stagger
- [ ] RosterBar shows active speaker underline
- [ ] InputArea textarea auto-resizes
- [ ] Mode tabs switch correctly
- [ ] Quick command chips insert text
- [ ] TopBar buttons are functional
- [ ] ChatContainer auto-scrolls on new messages
- [ ] Empty state displays correctly
- [ ] All animations play smoothly (60fps)
- [ ] CSS variables theme correctly
