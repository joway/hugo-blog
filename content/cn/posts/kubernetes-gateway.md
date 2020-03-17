---
title: Kubernetes 中使用 API Gateway 替代 Ingress
date: 2017-09-12
categories: ['技术']
draft: false
aliases: [
    "/ops/kubernetes-gateway/",
]
---

## 背景

最近在构思基于 Kubernetes 建立一个个人的开放云平台 , 听起来有点不自量力 , 不过作为个人业余小玩意还是蛮好玩的。最终的成品希望是用户能够轻松地在平台上跑一些简单的无状态服务 和 cronjob 。

在搭建平台的时候遇到的第一个困难是需要有一个好用且功能全面的 API Gateway , 主流的网关服务大多是基于 OpenResty 基础上进行二次开发 , 所需要完成的工作无非是负载均衡，和 API 管理, 加上一些零零碎碎的小功能。

## 负载均衡

负载均衡分为四层和七层两种 , 以大家所熟知的 Nginx 为例 , 在它的 conf 文件中 , 有 http {} 和 stream {} 两种 block 。

	# 四层负载均衡
	stream {
	    server {
	        listen 80;
	        proxy_pass app;
	    }
	
	    upstream app {
	        server 172.31.0.1:8000;
	    }
	}

	# 七层负载均衡
	http {
	  upstream app {
	    server 192.168.0.1:8000;
	    server 192.168.0.1:8001;
	  }
	
	  server {
	    listen          80;
	    location / {
	      proxy_pass      http://app;
	    }
	  }
	}

### 四层负载均衡

四层负载均衡只是从背后选择一个 server , 让其与客户端建立连接 , 其本身并不参与连接, 只是作为一个路由转发。好处是这样做它的性能会非常好，坏处是它也仅仅只能作为一个负载均衡存在，你无法对它做更加高层的处理，例如图片优化 , gzip 压缩等。并且由于它直接将后端服务暴露给了客户端, 当面临 DDoS 等攻击时, 后端将直接承受巨额流量。

### 七层负载均衡

七层负载均衡就是我们常用的反向代理，直接参与连接，是架在后端服务和客户端之间的桥梁。它能够知道任何客户端能够知道的任何信息，完成包括 cookie 处理, 鉴权等等操作。代价是它的性能会比四层负载均衡低，但由于客户端不直接与任何后端服务接触，它能够轻易地进行后端服务迁移，降级等操作。

### kuberntes Ingress

Kubernets 的 Service 就是属于四层负载均衡 , 但 Service 上的 ip 都是集群内网的地址 , 需要在 Service 之上再建立一个反向代理把 Service 暴露到外网 。Kubernets 自带一个 Ingress 功能 , 与其说功能，不如说就是提供了一个类似 ConfigMap 的接口功能 ，用户可以以 ` [ host - paths -> services ] ` 的形式 , 在 Ingress 里建立一个个映射规则 , 然后启动一个 Ingress Controller ,  Ingress Controller 将订阅 Ingress 里的配置规则并转化成 Nginx 的配置 , 然后对外部提供服务。在对外网暴露地址的时候, 只需要暴露 Ingress Controller 自身就行了, 所有服务可以被隔离在集群内部。

一般在使用的时候，会给 Ingress Controller 的 Service 指定一个 NodePort  , 这样每台机器都能有一个端口来作为 Ingress Controller 的入口来使用 , 然后再在 AWS 或 Google Cloud 上建立一个负载均衡把流量导向这些机器上的端口 , 从而使 Ingress Controller 的流量被分摊到每台机器上 。说起来很绕 , 相当于一个请求经过层层路由器后 , 最后打到你服务器上，还要再经过三个负载均衡器 。

Ingress Controller 并不仅仅局限于 Nginx 。Kubernetes 官方提供了许多种选择方案。例如使用 HAProxy 来替代 Nginx : [haproxy ingress](https://github.com/kubernetes/ingress/blob/master/examples/deployment/haproxy/README.md) 。事实上只要自己 watch 好 K8S Ingress 的变化，然后生成好对应的代理规则完全可以实现一个自己定制的 Ingress Controller 。

但这里有一个坑是 Ingress 的 spec 字段只允许你写它规则里的配置项, 如果你想加入别的字段就会非常蛋疼了。这种情况下 ，我看到过的项目一般会有三种方案:

1. 一种是使用 metadata.annotations 字段来写配置 , 这个字段可以随意写，但是如果你要针对 path 做限定条件，这个方案就非常蛋疼了。
2. 还有一种是在所有配置都在 ConfigMap 里写 , 不再需要 watch Ingress 了。这种做法其实就不算是在实现 Ingress Controller 了 ，因为完全脱离了 Ingress 自己的使用规范，但是异常好用。
3. 第三种也是最为灵活的还是直接写自己的数据库里，完全和 k8s 脱离。Ingress 这个项目以目前的趋势看，顶多成为一个 Demo 类型的产品，离成为一个功能完备的网关服务还有很长的路要走。依照它的规范来建立网关服务除了让能够使用现成的接口和命令行工具外，看不到任何的优势。

## API Gatewat 选型

### 初步需求

在了解清楚了这个背景并且确认了 kubernets 自身短期内很难再为社区提供一个内置的 API Gateway 以后 ，就需要从 k8s 生态外部寻求更加优秀的解决方案进行改造了。

我对于 API Gateway 的需求是 :

- 能够有一个现成并且活跃的社区
- 能够完成基本的七层负载均衡需求
- 能够有一个优秀的 UI 界面管理 API
- 能够支持对部分 API 进行鉴权
- 由于是业余折腾所需，所以我希望安装和使用足够简单，不需要后期折腾

整个流量的链路是:

	外部流量 
	-> aws / google cloud load balance
	-> api gateway node port 
	-> servicename.namepsace 
	-> pod ip 

基于上述目的，搜寻了一圈以后，发现了两个不错的项目 : [Kong](https://getkong.org/)  和 [Orange](http://orange.sumory.com/docs/) 。

### Orange 

Orange 基于 Openresty 开发，仿照了 Kong 的思想 , 使用了更加简洁和统一设计 。但它只支持 mysql 作为数据库 。 值得一提的是，它的 API 部分使用了作者另外研发的一套框架 Lor ，另外它还内置了一个非常漂亮简洁的 Dashboard 。它的核心思想是，当一个请求进来以后，会根据其特征，经过层层规则筛选，最后匹配到一个后端服务。规则会缓存在 share dict 中 , 所以它的性能和是否什么数据库没有什么关系 。

但按目前 Orange 的设计以及社区的使用情况来看，它并没有成熟的 Kubernetes 架构下使用的例子，不过 Kuberntes 也并没有什么特殊的东西，别的架构能用这里应该也差不多，所以我还是斗胆尝了第一口螃蟹 。

总体用下来 , 基本功能是可以实现 , 但是除此之外好像也没有什么别的高阶能力了 。不过它的 Dashboard 的确写得不错 ，基于条件配置比基于表单配置要好得多。我在公司内部尝试过给我们自己的 API Gateway 写配置前端，写得异常痛苦，用的人想必也异常痛苦。但当时也想不到什么好的方法，因为把一个有很长深度的 json 树给抽象到表单上去配置本身就是一个贼麻烦的事情，像 AWS 对于这些配置前端实在没办法做了干脆就直接给你一个 json 编辑器让你手写了。Orange 不同的是，它直接从目的出发，既然你最终想要的是一个路由规则，那我就不用 json 去生成规则，而是直接让你自己去写规则。

例如 ，我原先需要这样一个表单 :

![](https://ik.imagekit.io/elsetech/blog/images/old-blog/1505148736.png?tr=w-1024)

它有一个问题是 , 我需要人肉把一个表单在大脑内编译成一个 nginx 的配置规则， 如果你的一个域名后面有100个后端服务，你这个表单就需要写100次，且无法复用表单。

但是在 Orange 里 , 这个表单就是 :
	
	if host == xxx.joway.io 
	if urls == /static
	…
	
	then proxy : http://service-name:port

![](https://ik.imagekit.io/elsetech/blog/images/old-blog/1505148844.png?tr=w-1024)

你只要在这里面不停添加规则就行了 , 如果两个后端服务只有一个条件是不同的，你只要写一个 OR 就行了 , 可以非常完美的复用配置 。

当然 Orange 还是有很多坑的。有一个坑是我需要手动在 orange 的 nginx.conf 文件里把 resolver 改成我 Pod 上的 nameserver 地址 ，否则它解析不到我 k8s 里的 service name 。k8s 自己会跑一个 kube-dns 来解析所有内外网的域名 , 所以我不需要单独给它指定类似 8.8.8.8 的地址。

还有一个坑是，它官方推荐的镜像每一次重启容器都会初始化数据库 …… 这导致我一度以为这玩意的配置都是存在内存里的。

我改了下官方的推荐镜像，移除了它自带的 dnsmasq , 镜像地址在 [joway/docker-orange-kubernetes](https://github.com/joway/docker-orange-kubernetes) 。 第一次指定 `ORANGE_DB_SETUP` 环境变量就能初始化数据库。

### Kong

Kong 是另外一个非常活跃的项目 , 专门针对微服务设计的，支持 cassandra 和 postgres 两种数据库。它有着机器丰富的插件 ， 并且已经有非常多的 kubernetes 生产环境实践例子。它没有官方自带的 dashboard , 但有第三方的项目提供 UI 界面。

我使用的是 konga (https://github.com/pantsel/konga) 这个项目。从 UI 上讲也是非常美观的，但是功能上还是比 Orange 要复杂和难用。但是由于 kong 整个社区的背书，我最终还是选择了它。

![](https://ik.imagekit.io/elsetech/blog/images/old-blog/1505150036.png?tr=w-1024)


![](https://ik.imagekit.io/elsetech/blog/images/old-blog/1505150092.png?tr=w-1024)

值得注意的是，kong 支持重试策略 ，这个功能有利有弊，好处是当后端服务不稳定的时候，比如访问100次有5次超时，这个时候对客户端而言顶多有几个服务慢了一些时间而已，不至于失败。但坏处是，一旦流量来了一波高峰，导致后端服务被压跨了一部分，但它还在不停重试，导致流量被放大，从而后端服务更加无法恢复过来，最后雪崩。关于这个我并没有在 Kong 里找到相应应对措施配置，但如果是自己写的话，其实可以做一个一定时间全局最大重试次数来加以控制。

