---
title: "ElasticSearch 最佳实践"
date: 2017-05-28
type: "post"
draft: false
aliases: [
    "/ops/elasticsearch-bp/",
]
---

Elasticsearch 是一个需要不停调参数的庞然大物 , 从其自身的设置到JVM层面, 有着无数的参数需要根据业务的变化进行调整。最近采用3台 AWS r3.2xlarge , 32GB, 4核, 构建了一套日均日志量过亿的 EFK 套件。经过不停地查阅文档进行调整优化 , 目前日常CPU占用只在30% , 大部分 Kibana 内的查询都能在 5s ~ 15s 内完成。

下面记录了一些实践过程中积累的经验。

## 硬件

### CPU

1. 多核胜过高性能单核CPU
2. 实践中发现, 在高写入低查询的场景下, 日常状态时 , CPU 还能基本应付, 一旦进行 kibana 上的查询或者 force merge 时, CPU 会瞬间飙高, 从而导致写入变慢, 需要很长一段时间 cpu 才能降下来。

### Mem

1. Elasticsearch 需要使用大量的堆内存, 而 Lucene 则需要消耗大量非堆内存 (off-heap)。推荐给 ES 设置本机内存的一半, 如32G 内存的机器上, 设置 -Xmx16g -Xms16g ，剩下的内存给 Lucene 。
2. 如果你不需要对分词字符串做聚合计算（例如，不需要 fielddata ）可以考虑降低堆内存。堆内存越小，Elasticsearch（更快的 GC）和 Lucene（更多的内存用于缓存）的性能越好。
3. 由于 JVM 的一些机制 , 内存并不是越大越好, 推荐最大只设置到 31 GB 。
4. 禁用 swap `sudo swapoff -a`

## 配置

PS: 应该尽可能使用 ansible 这类工具去管理集群 , 否则集群内机器的状态不一致将是一场噩梦。

### JVM 

- 不轻易丢改 jvm 参数 , 除非你明确知道这个参数在做什么。

### 节点配置

#### 集群配置

PUT `/_cluster/_settings` 

#### 对所有索引设置

PUT `/_all/_settings` 

```
# cluster settings
PUT /_cluster/settings
{
	 # 永久变更, 它会覆盖掉静态配置文件里的选项
    "persistent" : {
        "discovery.zen.minimum_master_nodes" : 2 
    },
    # 临时修改 , 重启后清除
    "transient" : {
        "indices.store.throttle.max_bytes_per_sec" : "50mb" 
    }
}
```

#### 防止脑裂

```
discovery.zen.minimum_master_nodes > = ( master 候选节点个数 / 2) + 1 
```

集群最少需要有两个 node , 才能保证既可以不脑裂, 又可以高可用


### Segment

es 为了搜索性能不被后台 merge 影响 , 对它进行了限速。

如果使用的是 SSD , 需要手动调高 elasticsearch 的 throttle 。[尤其是对高写入的服务]

```
PUT /_cluster/settings
{
    "persistent" : {
        "indices.store.throttle.max_bytes_per_sec" : "100mb"
    }
}
```

## 故障恢复

### 恢复集群

当有节点掉线的时候 , 其余节点会选举 master , 并 rebalance data && copy shards , 这时整个集群网络和IO会大幅度上升 , 等到有节点加入的时候 , 该节点会删除本地已经被复制的数据, 然后再进行 rebalance。这个过程需要大量时间。但是假如数据的 replica set 存在于当前活跃的节点中 , 则整个集群仍旧是出于可用状态 , status 会变成 yellow。

在实践中发现 , 当一台机器被打挂后 , 压力均摊到其余机器, 会把其余机器也给打挂。这种场景下，与其雪崩，不如挂掉以后停止自动恢复，等挂掉的机器自己重启并假如集群。

设置下几个个参数可以帮助我们做这个权衡:

```
gateway.recover_after_nodes: 8 # 等待集群至少存在 8 个节点 后才能进行数据恢复
gateway.expected_nodes: 10
gateway.recover_after_time: 5m # 等待 5 分钟，或者 10 个节点上线后，才进行数据恢复，这取决于哪个条件先达到
```

这些配置只能设置在 config/elasticsearch.yml 文件中或者是在命令行里（它们不能动态更新）。

另外, 我们也能够通过设置延迟分配来阻止当某个 Node 临时下线时候触发 reassign 。下面的操作能够延迟5分钟分配, 若此时 Node 又恢复回来了则不进行再分配。

```
PUT /_all/_settings 
{
  "settings": {
    "index.unassigned.node_left.delayed_timeout": "5m" 
  }
}
```
	
### 滚动重启/升级

#### 前期准备

- 可能的话，停止索引新的数据。
- 禁止分片分配。这一步阻止 Elasticsearch 再平衡缺失的分片，直到你告诉它可以进行了。

	```
	PUT /_cluster/settings
		{
		    "transient" : {
		        "cluster.routing.allocation.enable" : "none"
		    }
		}
	```


- 关闭单个节点
- 执行维护/升级
- 重启节点，然后确认它加入到集群了
- 重启分片分配

	```
	PUT /_cluster/settings
	{
	    "transient" : {
	        "cluster.routing.allocation.enable" : "all"
	    }
	}
	```

- 对其它Node同样进行此类操作

## Tips

1. 降低日志收集组件的并发程度(降低实时性要求), fluentd 线程从 4 减少到 1 时 , ES 有负载有明显降低。
2. 在 fluentd 与 ES 中间加入一个 kafka 作为消息缓存，这样无论日志量瞬间增加多少倍，ES 都能平滑地消费 kafka 。




