---
name: typescript
description: TypeScript 开发技能，提供 TypeScript 最佳实践、类型定义和代码模式
license: MIT
metadata:
  file_patterns:
    - "**/*.ts"
    - "**/*.tsx"
  triggers:
    - "TypeScript"
    - "类型定义"
    - "接口"
    - "泛型"
  priority: 10
---

# TypeScript 开发技能

此技能帮助你编写高质量的 TypeScript 代码。

## 概述

TypeScript 是 JavaScript 的超集，添加了静态类型检查。此技能提供 TypeScript 开发的最佳实践。

## 使用场景

- 定义类型和接口
- 使用泛型
- 配置 tsconfig
- 代码组织和模块化

## 最佳实践

### 1. 类型定义

优先使用 `interface` 定义对象类型：

```typescript
interface User {
    id: string;
    name: string;
    email: string;
}
```

使用 `type` 定义联合类型、交叉类型：

```typescript
type Status = 'pending' | 'active' | 'inactive';
type UserWithStatus = User & { status: Status };
```

### 2. 泛型

```typescript
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
    return obj[key];
}
```

### 3. 严格模式

在 `tsconfig.json` 中启用严格模式：

```json
{
    "compilerOptions": {
        "strict": true,
        "noImplicitAny": true,
        "strictNullChecks": true
    }
}
```

### 4. 避免使用 any

使用 `unknown` 代替 `any`：

```typescript
function parseJSON(json: string): unknown {
    return JSON.parse(json);
}
```

## 代码组织

```
src/
├── types/
│   ├── index.ts
│   └── models.ts
├── utils/
│   └── helpers.ts
├── services/
│   └── api.ts
└── index.ts
```
