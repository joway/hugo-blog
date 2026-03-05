---
title: "Magic Brush - 画出你自己的产品宇宙"
date: 2026-03-05
categories: ['Product']
draft: false
---

上周末用 AI 写了一个新的产品： [Magic Brush](https://brush.elsetech.app)。

这个产品的 idea 来自于我经常用 AI vibe coding 一些小的前端产品，但是如果每次都为这些小产品创建独立的域名和部署太过于繁琐，而且目前也缺乏一个聚合站点可以浏览其他人创建的小产品。另外，我在写博客的时候，也经常会想要插入一些交互页面来展示我的 idea，但是如果要在博客里插入一堆 js/css 代码又会导致博客无法长期维护。我把这些需求收集了下，整理并抽象出了一个产品形态：

> 这个产品可以允许用户使用自然语言创作页面，然后通过 `iframe` 嵌入到任意网页中去。并且这个产品还可以有一个广场功能，可以看到其他人的作品。不仅仅能用来做博客的交互页面插入，也可以作为产品原型设计的工具。

## 产品设计

[Magic Brush](https://brush.elsetech.app) 由 2 主要页面组成。

### 页面设计页

用户可以在设计页右边会话框写自己的提示词与 AI 交互，左边的页面会实时渲染最新的页面。其他用户可以以只读的方式访问该页面，并且也能看到提示词，方便其他人模仿修改并创建自己的页面。

![](/images/magic-brush/preview.png)

### 广场页

广场页面允许看到所有 Public 的页面设计，可以以 Like 数量排序或者时间排序：

<iframe src="https://brush.elsetech.app/square" style="width:100%;height:600px;border:0;" loading="lazy"></iframe>

## Use Cases

### 创作可交互文章

对于有些文章来说，文字并不是最适宜的表达载体，例如游记。你可以把你的游记喂给 AI 生成可交互的页面，然后再插入到文章中。例如我的 [<<熊野古道中边路纪行>>](https://blog.joway.io/posts/japan-kumano-kodo/) 游记中，可以被转变为：

<iframe src="https://brush-api.elsetech.app/pages/2ZkCB6KD0F" style="width:100%;height:2500px;border:0;" loading="lazy"></iframe>

### 创作流程图

传统流程图需要用截图的形式插入到文章，导致不易修改。我们可以让 AI 生成流程图页面，然后直接插入到文章中，并且后续实时渲染最新的修改。

<iframe src="https://brush-api.elsetech.app/pages/KBDTrLJfrt" style="width:100%;height:600px;border:0;" loading="lazy"></iframe>

### 创作自定义工具

你还可以根据自己需要，写一个自己用的趁手的前端工具，例如：

<iframe src="https://brush-api.elsetech.app/pages/l6IldHx-Ol" style="width:100%;height:600px;border:0;" loading="lazy"></iframe>

甚至能在网页上插入一个小型浏览器:

<iframe src="https://brush-api.elsetech.app/pages/cJ3w_m4e3K" style="width:100%;height:600px;border:0;" loading="lazy"></iframe>

这些工具都能用 `https://brush-api.elsetech.app/pages/cJ3w_m4e3K` 的方式作为工具本身全屏打开。

## 实现过程

[Magic Brush](https://brush.elsetech.app) 的实现非常简单优雅，整个 Design Agent 在前端运行，后端代码无法拿到用户的 API Token。后端部署在 Cloudflare Worker 上，数据库使用 Cloudflare R2 。整个产品的维护成本接近于 0，除非用户变多。

Design Agent 的设计与传统 Code Agent 类似，约束是产出只能是一个 HTML 文件。在最开始的时候模型会返回一个根据初始提示词生成的 HTML 页面作为起始文件，而在后续 Modify 过程中，只允许调用一系列 tool call 来修改页面，最大化减少了 token 的消耗。

开发过程中，我使用 Claude Code 作为起始项目一把梭的 Agent，在后续的增删改前后端过程中我转用了 codex 进行开发。总耗时大约为 10 小时。

如果使用过程中有任何建议，欢迎联系我(i@elsetech.app)，也希望你会喜欢这个产品 :) 。
