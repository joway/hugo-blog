---
title: 深入理解 Lucene 工作原理
date: 2018-11-21
type: "post"
draft: true
---

## Lucene 基本组成

### 存储结构

Lucene 内部的存储结构自顶向下分为:

1. Segment 是最小的独立索引单元，由多个 Documents 构成
2. Document 由 Field 构成
	- DocId: Lucene 内部 Id，全局唯一
2. Field 由 Term 构成
	- FiledNaming: xxx
3. Term 存储了每个词对应的文档 Posting 信息
	- TermId: 全局唯一
4. Posting 里有 ...

![](../../images/lucene-inverted-index.png)

### 文件结构

|  ext	| name | description	|
|---	|---	|---	|
| .fdt | Filed Data | 文档 filed 的值 |
| .fdx	| Filed Index | 指向 field data 的指针 |
| .tim	| Term Dictionary | term 词典 |

## Lucene 处理流程

### 1. 存储 Field

判断文档每个 Field 是否需要被存储，若需要，则将 Field 写到 `.fdt` 文件中，并将该 DocId 文档的 Filed Data 在文件 `.fdt` 中的所在位置写入到文件 `.fdx` 中便于快速查找。

### 2. 构建索引














