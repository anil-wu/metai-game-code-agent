---
name: web-build
description: Web 构建技能，提供 Vite/Webpack 配置和构建优化最佳实践
license: MIT
metadata:
  file_patterns:
    - "**/vite.config.*"
    - "**/webpack.config.*"
    - "**/package.json"
    - "**/tsconfig.json"
  triggers:
    - "构建"
    - "打包"
    - "Vite"
    - "Webpack"
    - "bundle"
  priority: 15
---

# Web 构建技能

此技能帮助你配置和优化 Web 项目构建。

## 概述

现代 Web 项目使用构建工具来打包、压缩和优化代码。此技能提供 Vite 和 Webpack 的配置最佳实践。

## 使用场景

- 配置 Vite 项目
- 配置 Webpack 项目
- 优化构建性能
- 配置开发服务器

## Vite 配置

### 基础配置

```typescript
import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 3000,
        open: true,
    },
    build: {
        outDir: 'dist',
        sourcemap: true,
    },
});
```

### Phaser 项目配置

```typescript
import { defineConfig } from 'vite';

export default defineConfig({
    base: './',
    build: {
        rollupOptions: {
            output: {
                manualChunks: {
                    phaser: ['phaser'],
                },
            },
        },
    },
});
```

## Webpack 配置

### 基础配置

```javascript
const path = require('path');

module.exports = {
    entry: './src/index.ts',
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, 'dist'),
    },
    module: {
        rules: [
            {
                test: /\.ts$/,
                use: 'ts-loader',
                exclude: /node_modules/,
            },
        ],
    },
    resolve: {
        extensions: ['.ts', '.js'],
    },
};
```

## 构建优化

1. **代码分割**: 使用动态 import 或配置 manualChunks
2. **Tree Shaking**: 确保使用 ES 模块
3. **压缩**: 启用生产模式压缩
4. **缓存**: 配置文件名 hash

## 常用命令

```bash
# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```
