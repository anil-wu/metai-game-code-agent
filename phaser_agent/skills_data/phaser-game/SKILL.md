---
name: phaser-game
description: Phaser 游戏开发技能，用于创建和管理 Phaser 游戏项目，包括场景、精灵、动画和游戏逻辑
license: MIT
metadata:
  file_patterns:
    - "**/*.ts"
    - "**/phaser*.js"
    - "**/game/**/*.ts"
    - "**/scenes/**/*.ts"
  triggers:
    - "创建游戏场景"
    - "添加精灵"
    - "游戏动画"
    - "Phaser"
    - "游戏开发"
  priority: 5
  dependencies:
    - typescript
  allowed_tools:
    - read_file
    - write_file
    - edit_file
    - run_npm
---

# Phaser 游戏开发技能

此技能帮助你开发基于 Phaser 框架的 HTML5 游戏。

## 概述

Phaser 是一个快速、免费、开源的 HTML5 游戏框架。此技能提供 Phaser 游戏开发的最佳实践和模板。

## 使用场景

- 创建新的游戏场景
- 添加精灵和动画
- 处理用户输入
- 管理游戏状态
- 实现物理效果

## 工作流程

### 1. 创建场景

使用 `assets/scene-template.ts` 作为起点：

```typescript
import Phaser from 'phaser';

export class MyScene extends Phaser.Scene {
    constructor() {
        super({ key: 'MyScene' });
    }

    preload() {
        // 加载资源
    }

    create() {
        // 创建游戏对象
    }

    update() {
        // 游戏循环
    }
}
```

### 2. 添加精灵

在 `preload()` 中加载资源，在 `create()` 中创建精灵：

```typescript
preload() {
    this.load.image('player', 'assets/player.png');
}

create() {
    this.player = this.physics.add.sprite(100, 100, 'player');
}
```

### 3. 处理输入

```typescript
create() {
    this.cursors = this.input.keyboard.createCursorKeys();
}

update() {
    if (this.cursors.left.isDown) {
        this.player.setVelocityX(-160);
    }
}
```

## 最佳实践

1. **资源管理**: 始终在 `preload` 中加载资源
2. **对象池**: 使用对象池管理频繁创建的对象
3. **场景组织**: 按功能划分场景（菜单、游戏、结束等）
4. **状态管理**: 使用 Phaser 的场景数据传递状态

## 文件结构

```
src/
├── scenes/
│   ├── BootScene.ts
│   ├── MenuScene.ts
│   ├── GameScene.ts
│   └── GameOverScene.ts
├── objects/
│   ├── Player.ts
│   └── Enemy.ts
├── config/
│   └── gameConfig.ts
└── main.ts
```
