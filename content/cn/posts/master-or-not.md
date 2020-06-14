---
title: 从改名浪潮聊政治正确
date: 2020-06-14
categories: ['随笔']
draft: true
---

最近的 BLM 运动在计算机软件界掀起了一阵政治正确导向的改名浪潮，事实上这股风已经刮了很长一阵了，早在16年就有人[提议](https://github.com/antirez/redis/issues/3185) Redis 的 Master-Slave 应该改名叫做 Primary-Replica，并且在此之前已经有许多项目进行过类似的实践，如 [Django](https://github.com/django/django/pull/2692)， [Drupal](https://www.drupal.org/node/2275877)， [CouchDB](https://issues.apache.org/jira/browse/COUCHDB-2248)。不止 Master-Slave 的命名引起争议，甚至连名字里带 [Cop](https://github.com/rubocop-hq/rubocop/issues/8091) 都引起了部分人的反感。

计算机科学领域中之所以存在如此广泛使用 Master 的现象，很大一个原因恐怕是机器的诞生就是为了来替人类来充当「奴隶」的。当我在使用程序帮助我自动化地做一些我人力不愿意做的事情时，我彼时的心态大概的确是和当初的奴隶主类似的。

我其实很赞同 Primary-Replica / Leader-Follower 相比于 Master-Slave 是一个能更好地反应计算机主从架构且又能不冒犯任何人的术语。如果我现在要新设计一个主从系统，我一定不会使用 Master-Slave 这样的词语。但至于对于已有的项目，是不是应该追溯起来使他们都按照这个标准改名，我觉得这就是另外一回事了。

我觉得这里我们需要先达成两点共识：

1. 道德的标准一定是带着时代局限的，正如不能拿现在的法律去追溯过去的案件，更不能以现在的道德去要求发生在过去的事情
2. 道德不是法律，法律必须是清晰严谨的，道德很多时候是模棱两可的。



## 道德的时代局限



一个有意思的例子是，IBM 过去的一首公司歌曲里有一句歌词：“ that's why we are so gay”。这里的 gay 的含义是无忧无虑，和现在的含义相去甚远。

