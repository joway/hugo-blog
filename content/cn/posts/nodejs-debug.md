---
title: NodeJS 内存泄漏检测与定位
date: 2019-11-10
categories: ['技术']
draft: false
---

最近解决了一个 Node.JS 应用内存泄漏 Bug，顺便学会了用 Chrome DevTools 去看 heapdump 文件。这里做一些简单的记录。

# 如何「优雅地」获得 heapdump 文件

由于我们所有应用都是以容器部署的，所以要去获得某个容器内的文件，并拷贝到本地难度还是比较大，也非常麻烦。考虑到调试时或许会需要下载非常多次的 snapshot 文件，建议可以包下 [heapdump](https://www.npmjs.com/package/heapdump) 库，做成一个接口，把文件 dump 之后再传输给客户端，这样一劳永逸。

需要小心的是，在 heapdump 的时候内存很容易翻倍，所以当内存超过 500 MB的时候如果去 heapdump 非常容易导致 OOM 从而 Crash。

# 如何检测内存泄漏

检查内存泄漏有两种方法，一种是针对比较大的内存泄漏可以直接观察内存是否一直在稳步上升。如果是一些小的泄漏使得内存上升变化并不非常明显的话，可以通过对比不同时间的 heapdump 文件。

有时候内存上升也可能是因为本身访问量就在上升，所以需要两者对比着分析。

## Heapdump 文件对比

通过下载两份间隔一段时间(几分钟)的 heapdump 文件，打开 Chrome DevTools，进入 Memory Tab，选择 Load。选中其中时间更近的 heapdump ，并选择 Comparison，比较对象是老的那份 heapdump：

![](/images/nodejs-debug/01.png)

此时可以选择按 Delta 排序，可以看到两个时间点增加了哪些新的对象。

如图可以看到 string 和 Object 的 Delta 是差不多的，所以可以比较确定是由于 Object 里产生了大量一些 string 对象导致的数量增多，但并不一定能够100%确定是内存泄漏，也可能是正常业务波动。此时需要再拉新的一个时间点的 heapdump 文件再来对比，如果一直在增加，那么内存泄漏的可能性就非常大了。

# 如何定位内存泄漏

首先依旧是拿到 heapdump 文件，并在 Chrome 中打开。

![](/images/nodejs-debug/02.png)

这里有一些名词需要解释含义：

- Distance: 距离 GC 跟节点的距离
- Objects Count: 对象数目
- Shallow Size: 对象自身被创建时，在堆上申请的大小
- Retained Size: 把此对象从堆上移除，FullGC 能够释放的空间大小

我们可以先不管别的值，只看 `Retained Size` 。从上图我们可以看到，Object 的 `Retained Size` 是最大的，所以可以点开浏览它里面的元素。

![](/images/nodejs-debug/03.png)

如图标红的是该元素的引用关系，即在代码 `[engine.io/lib/server.js](http://engine.io/lib/server.js)` 中 `nsps(Server)` 对象的 `/notification` 属性下的 `adapter(Namespace)` 属性里的 `sids` 属性中引用了我们选中的对象 72257。sids 的值就是选中的对象。

通过查看这个对象，我们能够发现是否存在异常的内容，而通过 Retainers 里的引用关系，我们能够找到该对象在代码中的定位。如果值的内容并无异常，那有可能是 Retainers 里的引用关系导致它一直没有被释放。

此处很难总结出什么方法论，但主要思想就是根据 Retained Size 递减排序一路找下去。只要是内存泄漏， Retained Size 一定是会高，但反过来 Retained Size 高不一定是内存泄漏，依照这个逻辑，顺藤摸瓜总能找到一些蛛丝马迹。
