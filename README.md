# blog.joway.io

Hugo 博客源码。线上站点 https://blog.joway.io/ ，RSS 在 `/index.xml`。

## 环境

- Hugo **extended** 0.164 或更高（图片转 WebP 依赖 extended 版）。macOS：`brew install hugo`
- 本地预览：`make server`（等价于 `hugo server -ws .`，development 环境不会加载统计脚本）
- 正式构建：`make site`（`hugo --minify --panicOnWarning`，任何 warning 都会让构建失败）

## 写文章

```sh
hugo new posts/my-post.md      # 生成到 content/cn/posts/，默认 draft: true
```

front matter 约定：

```yaml
---
title: 标题
date: 2026-01-01
lastmod: 2026-01-02        # 可选；不写则取 git 最后提交时间
categories: ["Tech"]       # 统一双引号；常用值 Tech / Thought / Travel
draft: false
---
```

## 图片

- 原图放在 `assets/images/<文章名>/`，Markdown 里用绝对路径引用：`![说明](/images/<文章名>/foo.jpg)`
- 构建时由 `themes/yinyang/layouts/_markup/render-image.html` 自动处理：转 WebP、生成 800/1200/1600 三档 `srcset`、加 `loading="lazy"`；alt 为空时兜底为文章标题
- 相册（两列瀑布）用 shortcode，路径相对 `assets/images/`：

  ```
  {{</* gallery "tmb/day1/1.jpeg" "tmb/day1/2.jpeg" "tmb/day1/3.jpeg" */>}}
  ```

- 原图不需要预先压缩，但请勿提交没有被文章引用的图片
- 图片处理结果缓存在 `resources/_gen/`（已 gitignore），冷构建约 1–2 分钟，之后增量构建秒级

## 目录

```
config.toml                 站点配置
content/cn/posts/           文章
content/cn/{cat,travel,presentations}.md   独立页面
assets/images/              文章图片（经 Hugo 处理）
static/                     原样输出：favicon、logo、_headers、cc.png
layouts/_default/rss.xml    全文 RSS
layouts/robots.txt
themes/yinyang/             主题（本仓库直接维护，非 submodule）
```

主题关键文件：

- `layouts/partials/head.html`：meta、OG/Twitter Card、内联 CSS、主题切换脚本
- `layouts/partials/image.html`：图片处理的核心逻辑（尺寸、格式、srcset）
- `layouts/partials/seo.html`：JSON-LD
- `layouts/partials/disqus.html`：评论区滚动到附近时才加载
- `assets/css/index.css`：主题样式；`assets/css/chroma.css`：代码高亮（仅含代码块的页面内联）

## 部署

CircleCI（`.circleci/config.yml`）在 master 有提交时触发：

1. 下载 Hugo extended，恢复 `resources/_gen` 缓存
2. `make site` 构建到 `public/`
3. 将 `public/` force push 到 `joway/blog` 仓库的 master 分支，由该仓库对外提供站点
4. 同时把 `themes/yinyang/` 同步推送到 `joway/hugo-theme-yinyang`

`static/_headers` 是 Cloudflare Pages 格式的响应头配置（长缓存、安全头）。

## 统计与第三方脚本

`config.toml` 的 `params.extraHead` 里，只在 production 构建时输出：GA4（`G-X7BH3GLYYE`，由 `analytics.js` 配置）、umami、argos、mailbike、aidaily。
