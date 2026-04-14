# Phase 1-2: Configuration Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现模板选择页、LLM 配置页、角色配置页三个配置页面

**Architecture:** Next.js 14 App Router，Tailwind CSS，左侧导航 + 右侧内容区布局

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, Zustand, React Hook Form

---

## File Structure

```
src/app/templates/page.tsx
src/app/llm/page.tsx  
src/app/roles/page.tsx
src/components/template/
src/components/llm/
src/components/role/
src/components/ui/
```

## Tasks

### Task 1: UI 组件库

**Files:**
- Create: src/components/ui/Button.tsx
- Create: src/components/ui/Input.tsx
- Create: src/components/ui/Select.tsx
- Create: src/components/ui/Toggle.tsx
- Create: src/components/ui/TagCloud.tsx
- Create: src/components/ui/ColorPicker.tsx

- [ ] **Step 1: Create Button component**

```tsx
// src/components/ui/Button.tsx
import { ButtonHTMLAttributes, forwardRef } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'primary', children, ...props }, ref) => {
    const baseStyles = 'px-4 py-2 rounded-lg font-medium transition-all'
    const variants = {
      primary: 'bg-[var(--ink)] text-[var(--white)] hover:opacity-90',
      secondary: 'bg-[var(--line)] text-[var(--ink)] hover:bg-[var(--line2)]',
      ghost: 'bg-transparent text-[var(--ink)] hover:bg-[var(--line)]'
    }
    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${className}`}
        {...props}
      >
        {children}
      </button>
    )
  }
)
Button.displayName = 'Button'
```

Continue with similar patterns for Input, Select, Toggle, TagCloud, ColorPicker components. Each should use CSS variables for theming.

### Task 2: 模板选择页

Full implementation with:
- Left sidebar (320px): Logo, category navigation, selected info
- Right content: Template card grid (2 columns)
- Category filter (全部/历史人文/商业决策/童话奇幻)
- Template card: color bar, icon, name, description, role chips, theme dot
- Selected state: thick border + checkmark badge
- Hover state: translateY(-2px) + shadow
- Theme auto-switch on template selection
- JSON import: click button or drag file

**Files:**
- Create: src/app/templates/page.tsx
- Create: src/components/template/TemplateCard.tsx
- Create: src/components/template/CategoryNav.tsx
- Create: src/components/template/TemplateGrid.tsx
- Create: src/components/template/ImportZone.tsx

### Task 3: LLM 配置页

Full implementation with:
- Left navigation (200px) with 5 tabs
- Tab content areas
- Provider-specific fields
- Custom model support (BaseURL + Key + ModelList)
- API key management per provider
- Advanced settings: retry count, interval, concurrency, streaming toggle

**Files:**
- Create: src/app/llm/page.tsx
- Create: src/components/llm/LLMNav.tsx
- Create: src/components/llm/ProviderConfig.tsx
- Create: src/components/llm/CustomModelForm.tsx
- Create: src/components/llm/ApiKeyManager.tsx

### Task 4: 角色配置页

Full implementation with:
- Left role list (220px)
- Right editor area (scrollable)
- Role card: colored square avatar + name + role type + host badge
- Delete button on hover
- Add role button (+ icon)
- All editor fields per PRD specification

**Files:**
- Create: src/app/roles/page.tsx
- Create: src/components/role/RoleList.tsx
- Create: src/components/role/RoleCard.tsx
- Create: src/components/role/RoleEditor.tsx
- Create: src/components/role/AddRoleModal.tsx

### Task 5: 页面导航与状态持久化

- Step indicator showing 5 steps
- Navigation guards (can't skip steps)
- State persistence to Zustand + IndexedDB

**Files:**
- Modify: src/app/templates/page.tsx
- Modify: src/app/llm/page.tsx
- Modify: src/app/roles/page.tsx
- Create: src/components/StepIndicator.tsx
- Create: src/store/navigation.ts

### Task 6: 三国军师团模板数据

Hardcoded initial template data.

**Files:**
- Create: src/data/templates/sanguo.ts

---

## Self-Review

1. All components use CSS variables for theming
2. All forms have proper validation
3. State persistence is implemented
4. Navigation guards prevent skipping steps