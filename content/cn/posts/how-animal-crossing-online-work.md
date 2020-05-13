---
title: "从动物森友会聊主机游戏联机原理"
date: 2020-05-13
categories: ['技术']
draft: false
---

最近在玩动物森友会的时候时常会遇到一些迷之联机问题，在网上一番搜索，发现大家的答案都趋于用玄学来解释，于是便有了兴致想在原理上搞懂这些问题，顺便探究动森这款游戏的联机设定背后有哪些技术上的原因。

## 游戏是如何同步的

我们首先先来看看游戏是如何同步的。

想象两个独立房间里分别有甲、乙两个玩家，他们要远程下一局象棋。他们每下一步前都需要先获知到当前棋盘的情况，这时便可以有两种实现方式。

第一种业界叫做锁步同步，原理是每个玩家操作一步时，就通知给另外一个玩家，彼此同步当前的所有操作序列，通过这些有时间顺序的操作，就能够计算出当前的棋局状态。但它不允许中间丢失任何一步的信息，否则就会出现非常大的计算偏差。

第二种叫做状态同步，顾名思义是玩家每操作一步，就同步整个棋盘的状态。这种方式可以容忍中间某些状态丢失，最终得到的状态依旧还是一致的。

在实际实践中，针对那种玩家操作非常高频的游戏会更多使用锁步同步，例如王者荣耀。而对于那些卡牌类游戏更偏向于直接用状态同步。当然也会有两种方式组合使用的情况。

![](../../images/how-animal-crossing-online-work/sync-methods.jpg)

## 游戏是如何联机的

### 通信架构

无论是上面哪种同步方式，我们都需要通过网络在多个主机间交换数据。为方便论述，我们现在转换成甲、乙、丙三个人一起下跳棋。为保证三个人最终得到的游戏状态都是一致的，我们往往需要有一台 Host 主机来作为权威主机，其他主机只能通过权威主机下发的命令(状态/操作序列)来更新自己的游戏数据。

在这里我们假设是甲来做「Host」。乙、丙每操作一步，都需要先发送给甲确认，无误后再发送该操作被确认的信息给乙、丙，乙、丙此时才能够认为操作成功并将画面更新到最新的状态。甲主机上在任意时刻都存有当前游戏的真正状态，其他主机只是在 follow 甲主机的状态更新自己的画面。

在上述模式下，由于甲主机既要作为游戏主机，又要作为状态同步的主机，当联机用户数一多，甲主机就会不堪重负，出现所谓的「炸机/炸岛」现象。另外，这种模式会需要甲主机一直存活，只能作为短时间内的伺服方案。所以有些游戏会引入一个外部自建/官方的服务器来承担这个状态同步的功能，例如我的世界。但其原理依旧是一样的。

### NAT 穿透

在了解完上面的基础知识后，我们能够发现，在不考虑外部服务器的情况下，我们会对玩家主机间的网络有以下几点要求：

1. 甲能够向乙、丙发送数据
2. 乙、丙能够向甲发送数据
3. 乙、丙之间不需要有网络联通保障

虽然上述要求看起来很容易，但是由于现在网络运营商都会不同程度地使用 [NAT](https://zh.wikipedia.org/wiki/%E7%BD%91%E7%BB%9C%E5%9C%B0%E5%9D%80%E8%BD%AC%E6%8D%A2) 技术，所以导致要让两台家用主机建立双向通信并不是一件非常容易的事情。

家用网络一般有四种不同的 NAT 类型：

**Full-cone NAT**：

- Once an internal address (iAddr:iPort) is mapped to an external address (eAddr:ePort), any packets from iAddr:iPort are sent through eAddr:ePort.
- Any external host can send packets to iAddr:iPort by sending packets to eAddr:ePort.
![](../../images/how-animal-crossing-online-work/Full_Cone_NAT.png)

**(Address)-restricted-cone NAT**：

- Once an internal address (iAddr:iPort) is mapped to an external address (eAddr:ePort), any packets from iAddr:iPort are sent through eAddr:ePort.
- An external host (hAddr:any) can send packets to iAddr:iPort by sending packets to eAddr:ePort only if iAddr:iPort has previously sent a packet to hAddr:any. "Any" means the port number doesn't matter.

![](../../images/how-animal-crossing-online-work/Restricted_Cone_NAT.png)

**Port-restricted cone NAT**：

- Once an internal address (iAddr:iPort) is mapped to an external address (eAddr:ePort), any packets from iAddr:iPort are sent through eAddr:ePort.
- An external host (hAddr:hPort) can send packets to iAddr:iPort by sending packets to eAddr:ePort only if iAddr:iPort has previously sent a packet to hAddr:hPort.

![](../../images/how-animal-crossing-online-work/Port_Restricted_Cone_NAT.png)

**Symmetric NAT**

- Each request from the same internal IP address and port to a specific destination IP address and port is mapped to a unique external source IP address and port; if the same internal host sends a packet even with the same source address and port but to a different destination, a different mapping is used.
- Only an external host that receives a packet from an internal host can send a packet back.

![](../../images/how-animal-crossing-online-work/Symmetric_NAT.png)

主机上的网络测试功能能够告诉我们当前网络的 NAT 类型。Switch 上的 Type A、B、C、D 分别映射到上面四种类型，而 PS4 上则是 Type 1(直连，无 NAT)、2(非 Symmetric NAT)、3(Symmetric NAT)。为方便下文叙述，我们用 Switch 的 ABCD 指代上述四种网络类型。

理解了四种 NAT 类型各自的限制，我们就能够通过推导判断出，哪两个 NAT 类型的网络是不可能建立双向通信的，而不再需要去人肉尝试。这里我们分别举例来介绍不同 NAT 类型下的不同情况，甲作为 Host 主机，并且我们有一个外部的 Switch 联机服务可以获取到甲乙的外网 IP 信息。所谓的 Swtich 联机服务是一个第三方服务器，甲乙都能通过访问它去搜索到对方的外网IP和端口号信息，同时也可以将自己的外网IP和端口号信息给注册到上面。所以这里甲、乙能够在通信前就知道彼此的通信地址信息。

**如果甲的 NAT 类型是 A ：**

- 无论乙的类型是 A/B/C/D，乙都能够直接向甲的 eAddr:port 发送数据，而当甲已经收到乙的数据时，也能够获得到乙的 eAddr2:port2，以及向乙发送数据的资格，从而建立双向通信。

**如果甲的 NAT 类型是 B ：**

- 当乙的 NAT 类型是 B/C/D ：甲先使用 `192.168.1.1:10001` => `1.1.1.1:10002(甲外网出口)` => `2.2.2.2:20002(乙外网入口)` 向乙尝试发送数据，虽被乙拒绝，但在乙路由器上留下了访问记录，从而使得乙具备了向甲发送数据的能力。而当乙发送完数据，又会使得甲获得向乙发送数据的能力，从而建立双向通信。
- 当乙的 NAT 类型是 A 时同上甲为A时逻辑

**如果甲的 NAT 类型是 C ：**

- 当乙的 NAT 类型是 D ：乙尝试连接甲的时候会被拒绝，并且甲也没法知道乙映射的端口号是哪一个所以亦无法连接到乙。无法建立任一方向的通信。
- 当乙的 NAT 类型是 B ：C-B 的连接同上面 B-C 的连接。
- 当乙的 NAT 类型是 C ：C-C 和 C-B/B-C 的区别仅在于要求双方出口的端口要一直保持一致，要求更加严格，但依旧能够建立双向通信。
- 当乙的 NAT 类型是 A 时亦能够建立双向通信。

**如果甲的 NAT 类型是 D ：**

- 当乙的 NAT 类型是 D：无法建立任一方向的通信。
- 当乙的 NAT 类型是 C：同 C-D，无法建立任一方向的通信。
- 当乙的 NAT 类型是 A/B：同 A-D 和 B-D，能够建立双向通信。

综上推导，可以有以下结论：

1. 只有 C-D,D-C,D-D 的组合是没有可能能够建立双向通信的，其他组合在 NAT 层面上都能够具备双向通信的能力。
2. 类型为 A/B 的玩家理论上连其他任何类型的玩家都不会有 NAT 上的问题。

当然上述都是理论，实际中是否真的能够连接上还取决于其他网络状况甚至是程序编写逻辑的因素。

## 动森是如何做联机的

许多主机游戏在联机的时候都会有一些在玩家看来非常奇怪甚至奇葩的设定，这些设定都和上面讲的同步机制和联机网络问题相关。

动森的联机模式也有诸多有意思(恼人)的设定，例如：

- 联机状态下无法更改岛的装饰
- 当一个玩家上岛时，会需要所有人暂停近很长时间来等其成功加入
- 当一个玩家离开时，同样需要大家同步目送其离开，并且在离开时会保存当前时刻的数据进度
- 当有个玩家掉线/强行退出时，所有人的数据会回滚岛上一次玩家登岛/正常离开时的版本
- 当岛内有玩家打开了对话窗口时，人不能正常离开也不能上岛

当然以下分析也仅仅是我在玩了 200 个小时游戏后，结合自己的软件工程经验对动森实现方式的猜测。在没有看代码前谁也无法保证这种猜测的绝对正确性，况且相比正确性，我更在乎这个猜测过程的开心，所以不必太过于认真。

我们可以把联机游戏的过程分以下几个环节来分别讨论：

### 1. 甲打开联机权限(即所谓的开门)，用自己主机作为 Host

这一步甲将自己的外网 IP 和端口号(如 `1.1.1.1:10001`)注册在了 Switch 的联机服务中。

### 2. 乙通过搜索找到甲，尝试加入

- 乙通过联机服务先将自己的外网 IP 和端口号(如 `2.2.2.2:10002`)注册上去。(即游戏里询问是否要联机的那一步)
- 再通过搜索得到甲的 `1.1.1.1:10001` (即动森里搜索好友的那一步)，尝试连接。

  注意，此时甲主机在后台也通过联机服务知道了乙在连它，并且甲也会根据 NAT 类型的不同，用乙的 `2.2.2.2:10002` 去连乙，尝试打通双向通信。

### 3. 建立连接，上岛

当上面一步确认能够建立双向通讯后，就可以开始上岛了。上岛又分为以下几个步骤：

#### 3.1 Host 打包当前所有游戏状态

在上岛前，甲主机(Host)会把当前时刻的所有人的游戏数据给打包一份 snapshot。

这里的 snapshot 数据内容包括岛屿数据和玩家数据。

#### 3.2 下载对方岛的 snapshot

动森上岛时会弹出一个显示进度的动画，这个动画的过程就是在下载目标岛的 snapshot 数据，很明显能够发现如果在中国连美国的玩家，这个过程会非常漫长，这个是由于跨境网速慢导致的。

#### 3.3 其他人同步等待，直到新玩家上岛

之所以其他玩家要等待新玩家上岛是因为上一步保存的 snapshot 必须是最新的结果，这也意味着其他玩家不能再有增量操作，否则新玩家上岛时状态就不一致了。

### 4. 正常游戏

当上岛完毕，就可以开始正常开始游戏了。这时候就会遇到一个如何同步玩家彼此操作数据的问题。

这里我们把玩家的操作分为两种类型：

1. 影响游戏数据（低频，有时序要求，需要落盘）
2. 影响游戏画面但不影响游戏数据（高频，无时序要求，不需要落盘）

如果仔细体验会发现，当我们在挖坑、和 NPC 对话、丢物品等会对全局游戏数据产生直接影响的操作时，偶尔会出现一下卡顿，这是因为这些会影响全局状态的操作在渲染画面前都需要先向 Host 主机请求是否允许，这里如果出现网络抖动的话就会出现卡顿/失败的情况。但是我们跑步的时候却很少出现卡顿，但有时会出现「闪回」，因为跑动只影响了玩家当前位置，不影响游戏数据，就算出现闪回也是能够接受的，而且还不需要强制保证时序性。况且如果跑步也要去 Host 端询问就会导致整个游戏体验都非常卡。但是像丢物品这种操作如果数据错乱或者时序错乱的话，整个状态就不一致了，会非常严重。

所以这里的同步方式其实是锁步同步。只不过分别对低频和高频做了分别的策略。

### 5. 玩家退出/强退/掉线

玩家如果正常退出游戏，会触发一个「保存数据」界面。要理解这个保存数据的含义，我们要把游戏里的数据分为两类：

1. 岛屿的状态
2. 每个玩家的每一步操作数据

首先对于主机游戏来说，其真正有效的数据都是要最终落盘到主机本地存储里。但试想如果每一次更新都触发玩家本地主机存储的更新，到时候要回滚起来也会变得异常麻烦，更不用说磁盘的 IO 还非常慢。所以这里的架构其实是，Host 主机的内存里存放着当前游戏的权威数据，包括岛屿状态和玩家操作。另外，无论玩家用什么方式退出，我们都必须确保结束游戏后，所有玩家本地的存档加上 Host 主机上的存档都是某一个时间点上的真正游戏状态。游戏数据正确性的优先级是高于用户体验的。下面会有例子来解释这点的重要性。

当玩家正常退出触发「保存数据」时，Host 主机首先会开启一个当前时刻的 snapshot，然后每个玩家的主机都会向 Host 主机去下载属于其的操作数据，并落盘到本地。

但当有玩家异常退出时，由于其并没有下载属于他的数据，所以他的本地游戏数据还停留在上一次保存的时间点 T1 上，为了满足我们前面说的数据正确性的保证，虽然岛上其他玩家没有掉线，并且他们游戏里的状态都是最新的也是正确的数据，但不得不为了让这个家伙的数据是正确的而把其他所有人的数据都回滚到了时间 T1 上，这就是为什么动森会出现掉线回档的原因。

## 常见问题

### 任天堂联机服务垃圾吗？

通过上面的解释能够理解，这些看似奇葩的联机体验背后，的确是有着非常多技术难题的。而且任天堂毕竟是一家游戏公司不是专业数据库公司，虽然目前的技术实现方案有可以改进的地方，但是也是要算上 ROI 的。

### 为什么游戏厂商不自建服务器来提升体验？

游戏玩家来自全球各地，如果要用自建服务器来提升体验，那也得在全球都铺设服务器，这个成本相当大且实现难度也相当大的。的确现在会有那种全球同服的解决方案，但是一般都是像网络游戏这种就靠着联网来挣钱的公司会有能力和意愿采用。主机游戏的商业模式注定了他们不会花非常高的成本去提升网络体验。当然主机生产商自己搞一个全球服务器就是另说了。

## 参考资料

- [Wikipedia: Network address translation](https://en.wikipedia.org/wiki/Network_address_translation)
- [Peer-to-Peer (P2P) communication across middleboxes](http://midcom-p2p.sourceforge.net/draft-ford-midcom-p2p-01.txt)
- [网络游戏同步技术概述](https://zhuanlan.zhihu.com/p/56923109)



