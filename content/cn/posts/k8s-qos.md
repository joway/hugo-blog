---
title: Kubernetes QOS 服务质量保证
date: 2017-05-28
type: "post"
draft: false
aliases: [
    "/ops/k8s-qos/",
]
---

kubernetes 的 QOS 策略非常复杂且难以理解 , 它的文档也是在一个代码库的角落里 , 官方似乎也并不特别去强调这个功能。但在实践中 , 这种基本的功能又是不可或缺的。相关代码在 [qos.go](https://github.com/kubernetes/kubernetes/blob/master/pkg/api/v1/helper/qos/qos.go)

### 对于可压缩(Compressible) 资源

目前仅支持 CPU 。

container 被确保拥有 requests 的资源 , 但能额外再使用多少CPU资源取决于其它 containers。例如:

	containerA.requests.cpu = 600m
	containerB.requests.cpu = 300m
	600:300 = 2:1 
	=>
	所以 containerA 的可以被分配的额外 cpu 为 66.6， containerB 为 33.3 。

### 不可压缩(Incompressible)资源 

目前仅支持 内存

### 调度

k8s 确保一个 Pods 里的 containers 的 requests 总和会小于被分配到的Node的可用资源 , 否则则报错。

Pod 的 schedule 取决于 requests , 而非 limit。

PS : 调度在 Pod 层面上执行。

### QoS 等级

> Best-Effort < Burstable < Guaranteed

![](https://cdn.joway.io/images/upload/14959675747.png)

- BestEffort:
	> POD 中的所有容器都没有指定CPU和内存的requests和limits
	例如:
		containers:
		name: foo
			resources:
		name: bar
			resources:
	当 Node Out Of Memory 时 , 首先被杀。
	当资源充足时，它可以使用全部剩余内存资源。
- Burstable:
	> POD 中只要有一个容器，这个容器requests和limits的设置同其他容器设置的不一致，那么这个POD的QoS就是Burstable级别
	当limit没设置时, 默认可以达到机器最大资源数。
	Burstable 当受到系统内存压力时 , 且没有 Best-Effort pod 存在时， 超出 requests 的 Pod 会被删除。
	当资源充足时，它仅仅只会按照 requests 和 limits 的设置来使用内存。
- Guaranteed: 
	> POD 中所有容器都必须统一设置了limits，如果有一个容器要设置requests，那么所有容器都要设置，并设置参数同limits一致。
		containers:
		name: foo
			resources:
				limits:
					cpu: 10m
					memory: 1Gi
				requests:
					cpu: 10m
					memory: 1Gi
		name: bar
			resources:
				limits:
					cpu: 100m
					memory: 100Mi
				requests:
					cpu: 100m
					memory: 100Mi
	若机器出现 OOM , 当没有更低优先级的时候, 再去杀它。
	若Pod 自身超出了 limit ， 被杀掉。
	当资源充足时，它仅仅只会按照 requests 和 limits 的设置来使用内存。