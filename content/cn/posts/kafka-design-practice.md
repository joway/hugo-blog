---
title: Kafka 的设计与实践思考
date: 2018-04-16
categories: ['技术']
draft: false
aliases: [
    "/最佳实践/kafka-design-practice/",
]
---

前几天看了 librdkafka 的[官方文档](https://github.com/edenhill/librdkafka/blob/master/INTRODUCTION.md)，这篇文档不仅仅讲解了如何使用 Kafka ，某种程度也讲解了分布式系统实现的难点和使用细节，故而让我对 Kafka 的实现原理产生了浓厚的兴趣。

这篇文章从 Kafka 的设计到使用做了一些个人总结，围绕真正实践场景，探寻其设计上的智慧与妥协。

## 设计

### 架构设计

#### Zookeeper

Zookeeper 存储了 Kafka 集群状态信息 。

Zookeeper 还负责从 Broker 中选举出一个机器作为 Controller, 并确保其唯一性。 同时, 当 Controller 宕机时, 再选举一个新的 。

在 0.9 版本之前，它还存储着 Consumer 的 offset 信息 。

#### Broker

接收 Producer 和 Consumer 的请求，并把 Message 持久化到本地磁盘。

集群会经由 ZK 选举出一个 Broker 来担任 Controller，负责处理各个 Partition 的 Leader 选举，协调 Partition 迁移等工作。

### 内部组件设计

#### Topic

逻辑概念，一个 Topic 的数据会被划分到一个或多个 Partition 中。

#### Partition

最小分配单位。一个 Partition 对应一个目录，该目录可以被单独挂在到一个磁盘上，以实现IO压力的负载均衡。同时多个 Partition 分布在多台机器上，也实现了灵活地水平扩容。

每个 Partition 都能够拥有一个或多个 Replication 副本。创建 Topic 的时候能够指定每个 Topic 的 Replication 数量，来保证高可用，Replication 数量为1时，即没有副本，只有其自身 (所以其自身也算是一个 Replication )。其中一个Replication 被选举为 leader。如果leader挂掉了，也会有相应的选举算法来选新的leader。

**所有的读写请求都由Leader处理** 。其他 Replication 从Leader处把数据更新同步到本地。由于针对某一个 Partition 的所有读写请求都是只由Leader来处理，所以Kafka会尽量把Leader均匀的分散到集群的各个节点上，以免造成网络流量过于集中。

ISR(In-Sync Replica): 是该 Partition的所有 Replication 的一个子集，表示目前 Alive 且与Leader能够“Catch-up”的 Replication 集合。由于读写都是首先落到 Leader 上，所以一般来说通过同步机制从Leader上拉取数据的 Replication 都会和 Leader 有一些延迟(包括了延迟时间和延迟条数两个维度)，任意一个超过阈值都会把该 Replication 踢出ISR。每个 Partition 都有它自己独立的ISR。

#### Offset

每个 Partition 都是一个有序序列。编号顺序不跨 Partition ，即每一个 Partition 都是从0开始编号。该编号就是该 Partition 的 Offset 。

每次写入消息都是被顺序 append 进 Partition 序列中。

客户端凭 Offset 访问到对应的 message 。

#### Segment

Partition 由多个以Offset大小为顺序划分的 Segment 组成。每个 Partion 相当于一个巨型文件(事实上是目录)被平均分配到多个**大小相等**的 Segment 中。但每个 Segment File 的消息数量不一定相等。文件分开的好处就是能快速删除无用文件，有效提高磁盘利用率。如果是单个文件将很难删除老的数据。

当某个segment上的数据量大小达到配置值(`log.segment.bytes	`)或消息发布时间超过阈值(`log.segment.delete.delay.ms	`)时，segment上的消息会被flush到磁盘，只有flush到磁盘上的消息订阅者才能订阅到，segment达到一定的大小后将不会再往该segment写数据，broker会创建新的segment。

### 底层存储设计

Segment 是 Kafka 文件存储的最小单位。Segment File 由两部分组成，一个是 index file 一个是 data file , 分别以 `.index` 和 `.log` 结尾。

Segment 文件命名规则：Partition 全局的第一个 segment 从 0 开始，后续每个segment文件名为上一个 Segment 文件最后一条消息的 offset 值。数值最大为64位long大小，19位数字字符长度，没有数字用0填充。如 `0000000000000034567.index` 和 `0000000000000034567.log`。

假设 `0000000000000034567.index` 的文件内容为:

```
1,0
3,497
6,1407
...
N,position
```

`3,497`表示该文件 segment 中的第三个，即整个 partition 中的第 `34567 + 3`个 message 的在 `0000000000000034567.log` 文件中的物理偏移位置是497。注意该 index 文件并不是从0开始，也不是每次递增1的，这是因为kafka采取稀疏索引存储的方式，每隔一定字节的数据建立一条索引，它减少了索引文件大小，使得能够把 index 映射到内存，降低了查询时的磁盘IO开销，同时也并没有给查询带来太多的时间消耗。

因为其文件名为上一个segment 最后一条消息的 offset ，所以当需要查找一个指定 offset 的 message 时，通过在所有 segment 的文件名中进行二分查找就能找到它归属的 segment ，再在其 index 文件中找到其对应到文件上的物理位置，就能拿出该 message 。

### API 设计

Kafka 的核心设计是一个非常简单的模型，有点类似于一个复杂度为O(1)的 K-V 数据库， 客户端指定 `topic + partition + offset` ，就能够得到一个 message 。该模型接近于一个无视客户端状态的数据库。在此基础上，调用方只要自己管理 offset 状态就能直接实现一个消息队列的功能。

当然由于 Kafka 本身就为消息队列而设计，所以它在该底层基础上，提供了以下一些 API 供客户端调用。

#### Producer

发送 message 到 Kafka 。客户端需要指定一个 key , kafka 会hash该 key 到一个 Partition 上。如果不指定，将会随机选择一个 Partition 。

Producer 支持批量操作，消息攒够一定数量再发送，使用适当的延迟换来更高的数据吞吐量。

#### Consumer

一个 consumer 可以消费多个 partition , 但是一个 partition 最多只能被一个 consumer 消费。正是因为这个原因，所以一个 Topic 的 Partition 数量等于该 Topic 能够被并行消费的能力。

#### Consumer Group

多个 consumer 组成一个 Consumer Group , 每个消息只能被 Consumer Group 中的一个 consumer 消费。该状态被记录在 Kafka 中，而不需要用户自己维护。

## 实践

软件开发没有银弹，Kafka 再强大也会受限于各种不可调和的矛盾 。其它一些软件往往会为了追求某一点能力，而付出一部分代价。而 Kafka 比较灵活的是，它将这种矛盾的选择权通过参数配置和使用技巧的方式交由用户自己去选择。这种做法带来的一个问题是，在具体实践里存在太多权衡因素，导致其使用门槛相对于别的开箱即用的软件过高。

下面探讨了在一些具体场景里，需要如何去使用 Kafka 。

### 如何保证消息发布的可靠性

消息的不丢失对于消息队列来说至关重要。但要实现这一点也是非常困难，极端考虑甚至是不可能的，因为机器一定可能会挂，磁盘一定可能会坏，只是看能够承受多大的规模故障罢了。我们这边谈论的消息不丢失主要指:

- 如果发送失败，发送方要能够知道这个消息，方便它进行重试或者相应处理 。
- 如果发送成功，要确保发送成功后，即便一部分数量的 Kafka 机器全部被物理销毁，这个消息依旧能够被持久化保存下来。

前面讲到了 Kafka 的 Partition 有一个 ISR 机制，当一个 message 被写入到 Leader Partition 中后，并被所有 ISR 给同步到本地，此时只要ISR的机器有一台还存活着且磁盘完好，这个消息就能够正常存在。如果在Leader刚写入完，但此时 Leader 立马挂了，会导致这个消息永久丢失。如果要实现绝对意义的不丢失，就需要客户端当且仅当获知到这个状态时，才认为消息发送是成功的。但这种等待的性能损耗会随着 Replication 的数量增多而线形增多。

有时候我们要求可能并没有如此之精确，可以只要求 Leader 写入完了就告诉我们成功了。但这里会存在一个消息重发的情况，例如，leader 写入完成后告诉我们，但路上丢包了，导致我们以为发送失败了，此时又继续发送了一份消息，这个时候可能会存两份 。 Kafka 是不会去管理这种复杂情况的，客户端需要在使用的时候明确知道这件事情并在程序设计上为此负责，比如可以在每条消息里加一个全局唯一ID去标识一个消息，在消费的时候去判断是否消费过这个消息。

如果我们要严格要求不重发，且能够接受消息丢失的情况，只要不去理睬 leader 的写入成功信息即可，每个消息仅发送一次，不在乎发送是否成功。

在 Kafka 客户端中，我们可以有以下三个参数来处理上述情况:

- acks=0: producer 不等待 broker 的 acks。发送的消息可能丢失，但永远不会重发。
- acks=1: leader 不等待其他 follower 同步，leader 直接写 log 然后发送 acks 给 producer。
- acks=all: leader 等待所有 follower 同步完成才返回acks。

### 如何保证消息消费的可靠性

正常情况下，我们一般希望消息队列里的消息仅被消费一次，且一定会被消费一次，并且处理结果一定是成功的。但要实现这点非常困难，且这一点的可靠性大部分取决于用户编写代码本身的质量。

Kafka 的 Consumer 机制只是提供了一个保存 Offset 的接口，由于在没有过期的情况下，Kafka 并不会主动去删除消息，所以我们的问题仅仅在于如何去确保`保存 Offset`和`处理消息成功`这两个操作是一个原子操作。

#### 有且仅有一次 「exactly once」

一般性我们认为计算操作是无状态的，IO操作是有状态的，如果消费者仅仅只是做无状态的一些操作，我们其实完全不需要考虑它是否多次消费的问题。大部分时候让我们头痛的都是数据库的保存操作。有一种取巧的方案是，把每次消费的 Offset 作为一个字段和正常保存操作一起存入数据库中，如果保存失败，则说明处理失败，此时可以重新保存。

#### 至少一次 「at least once」

但我们也可以用更好的程序设计来让这件事情做的更加优雅，如果我们的消费者函数是一个幂等函数，相同的输入执行多次也不会影响到最终结果。那么我们就能够接受重复处理消息的情况。而此时只要确保所有的消息都能够被至少消费一次就行了。这种场景我们可以选择先处理消息，再保存 Offset 。

#### 至多一次 「at most once」

也有的时候我们希望最多处理消息一次，可以接受个别消息没有被处理的情况，我们也可以选择先保存 Offset , 再处理消息。

### 如何保证消息的顺序

Kafka 每个 Partition 都是相互独立的，Kafka 只能保证单个 Partition 下的有序。如果你的应用程序需要严格按照消息发送的顺序进行消费，可以考虑在程序设计上去做文章。

举个例子是，我有一个游戏系统，每个人会顺序做一些不同操作，对应不同事件，发送到Kafka。我的消费者显然需要考虑到每个用户操作的上下文关系，但这个时候我们所需要的有序其实是针对单个用户的有序，而不要求全局有序。我们可以以用户的ID作为 key , 确保单个用户一定会被分配到某个固定的 partition 上，这样我们就能够实现单个用户维度的有序了。

如果你一定要全局的有序序列，还有一种取巧的做法是，所有消息都使用同一个 key , 这样他们一定会被分配到同一个 partition 上，这种做法适用于临时性且数据量不大的小需求，消息量大了会有性能压力。

### 高度实时的场景下能够有非常高的吞吐

在 Linux 操作系统中，当上层有写操作时，操作系统只是将数据写入 Page Cache，同时标记 Page 属性为 Dirty。当读操作发生时，先从Page Cache中查找，如果发生缺页才进行磁盘调度，最终返回需要的数据。

当我们的 Producer 处于一个高度实时的状态时，读和写的文件位置会非常接近，甚至完全一样，此时就能最大限度的利用该 Page Cache 机制，也就是这种情况下Kafka 甚至都没有直接去读磁盘的文件。

### Kafka Producer Key 选择

假设一个场景，我们需要将每个用户的 Page View 信息给存入 Kafka ，此时我们会很自然地想到以 userId 来作为 key 。理想情况下这种选择可能是不会错的，但如果假设有一个用户是一个爬虫用户，他个人的访问量可能是正常用户的百倍甚至千倍，这个时候你会发现，虽然 userId 作为 key 而言，它是均匀分布的，但其背后的数据量却并不一定是均匀分布的，久而久之，就可能产生`数据倾斜`的情况，导致各个partition数据量分布不均匀。当然对于 Kafka 自身而言，一个Partition里有再多的数据，也不会去影响到它的正常性能。但没有特殊需求时，在选择 key 的时候，还是要考虑到这种情况的发生。

### 如何选择 Partiton 的数量

在创建 topic 的时候可以指定 partiton 数量，也可以在常见完后手动修改。但partiton 数量只能增加不能减少。中途增加partiton会导致各个partition之间数据量的不平等。

Partition 的数量直接决定了该 Topic 的并发处理能力。但也并不是越多越好。Partition 的数量对消息延迟性会产生影响。

一般建议选择 broker num * consumer num ，这样平均每个 consumer 会同时读取broker数目个 partition , 这些 partiton 压力可以平摊到每台 broker 上。












