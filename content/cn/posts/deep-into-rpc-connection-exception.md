---
title: RPC 漫谈： 连接异常
date: 2021-05-06
categories: ["Tech"]
tags:
- RPC
- Service Mesh
draft: true
---

在前文讲了 RPC 框架的连接管理模式，本文主要讲述在出现异常情况时，我们需要如何去处理。

## 连接异常的种类

### 建连异常

### 写入异常

Socket 的写入操作并不是直接发送网络包，而是写入到内核中的 TCP 的发送缓冲区。操作系统提供的 write 系统调用在 blocking 模式下，只有缓冲区能够放下整个 buffer 时才会返回；在 nonblock 下，会返回能够放下的字节数，

### 读取异常


