---
title: 宏观理解 Raft 协议
date: 2021-05-06
categories: ["Tech"]
draft: true
---

## CAP

### C：Consistency

A total order must exist on all operations such that each operation looks as if it were
completed at a single instance. For distributed shared memory this means (among other
things) that all read operations that occur after a write operation completes must return the
value of this (or a later) write operation. 

### A：Availability

Every request received by a non-failing node must result in a response. This means, any
algorithm used by the service must eventually terminate.

### P：Partition Tolerance

The network is allowed to lose arbitrarily many messages sent from one node to another.

## Leader Election

选举是由候选人发动的。当领袖的心跳超时的时候，追随者就会把自己的任期编号（英语：term counter）加一、宣告竞选、投自己一票、并向其他服务器拉票。每个服务器在每个任期只会投一票，固定投给最早拉票的服务器。

## Log Replication

