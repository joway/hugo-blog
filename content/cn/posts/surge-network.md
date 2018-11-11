---
title: 使用 Surge 提升多网络环境下的流畅开发体验
date: 2018-07-03
type: "post"
draft: false
aliases: [
    "/最佳实践/surge-network/",
]
---

作为一名后端工程师经常需要在各种网络环境中切换，由于网络拓扑本身的复杂性以及一些网络工具之间的冲突和bug，常常会在切换中造成不必要的麻烦和痛苦。通常很容易在工作中听到同事会问这些问题 : 

1. 你有开 vpn 吗 ? 
2. 你开了 ss 了吗 ? 
3. 你有同时开 ss 和 vpn 吗 ?
4. 你 http 代理是不是被顶掉了 ? 

如果同是技术同事间交流那可能还容易，如果是技术和非技术间交流网络情况，那简直是一个灾难。

而事实上，在绝大部份时候，我们对于网络拓扑的需求是可被精确描述的，也就是说理想情况下不应当存在一个我为了访问某个服务而手动选择要进入某个网络环境的事情。

这篇文章会介绍我们在构建复杂网络环境中的良好开发体验时踩过的坑以及最终是如何优雅地解决这个问题的过程。

### 历史方案演变

常见的网络环境有:

1. 正常大陆网络
2. 能够上国外网站的网络
3. 公司内网
4. 各个服务器集群的内网

如果你自己还折腾了一些服务器或者家庭网络，那可能还会更加复杂。

之前摸索出的一套还算比较方便的解决方案是 :

- 在本地常驻一个 ss client 并开放 http 代理端口
- 在浏览器上使用 `Proxy SwitchyOmega` 使 Chrome 都走 ss client 的 http 代理
- 开一个 openvpn 连接到服务器内部网络

这种配置方式能够使得我既能连接所有服务器线上服务和数据库，也能自由地用浏览器去 Google 查一些资料。缺点是丢失了办公室原本的网络环境，另外如果你们服务器有两个完全隔离的子网，那么你可能需要同时连两个 vpn 。而且还有一个不好的是，你的所有非线上服务访问都经过了线上vpn机器的一层代理，让你的访问速度变慢了不说，对服务器也不是一个好事。此外，如果你的一些软件无法手动配置代理，那他们只能默认走 vpn 的网络，对于一些需要访问国外服务器的软件来说就麻烦了。

基于以上缺点，我们又迭代出了另外一个方案:

- 在服务器上安装一个 ss server
- 在本地常驻两个 ss client ，一个指向生产服务器 ss, 一个指向国外 ss , 并开放 socks5 代理端口
- 使用 `Proxifier` 代理所有本机连接并指定一些规则选择直接访问还是转发到本地的两个 ss client 上。例如我选择让所有 10.1.0.0/16 请求走生产服务器ss，别的都走国外 ss 的那个 client ，同时在 client 里配置好 pac 规则使得国内的依旧直接走本地网络。

这种方案理论上完全实现了我们的所有需求，但是需要的组件太多了，看着就很繁琐，无法推广给团队其它人使用。同时这些规则也很零零碎碎，几乎没什么可维护性 。

### 使用 Surge 构建高效开发体验

在使用 surge 长达两年之后，我才想起来仔细阅读下它的文档。无意中发现它完全不是一个单纯的"网络调试工具"，同时具备了非常完整灵活的规则系统。而这套规则系统完全能够实现我目前所遇到的所有问题。

我先简单描述下我们的基础设施网络情况:

1. 我们首先有一个公司内网，许多网站要求只有公司内网下才能访问。(`10.0.0.0/16`)
2. 我们服务器机器都在一个子网中 (`10.1.0.0/16`)
3. 我们在机器上搭建的 kubernetes(k8s) 集群自身也有一套子网 (`10.2.0.0/16`)
4. k8s 自己有一套内部域名解析系统，例如 xxx.default.svc.cluster.local 会被它自己一个叫 kube-dns 的服务解析成 10.2.0.1 , 这套解析只在集群内生效。
5. 在日常开发中，我们经常需要在本地访问各种内网中的服务，同时又要使用 Google 查阅资料

值得庆幸的是，我们所有的内网网段彼此互不重叠，也就是说，这给了我们单纯依靠 ip 来区分走什么代理的能力。

surge 支持通过域名或者IP-CIDR来判断需要走哪个代理。这就使得我们的工作变得极其之简单了。首先只需要:

- 在 k8s 内部搭建一个 ss server , 确保这个 server :
	1. 能够解析 k8s `*.*.cluster.local` 的域名
	2. 能够访问 k8s 自身的所有机器
- 配置 surge 代理服务器:

	```
	SS-SERVER = custom, s0.k8s.com, 8888, rc4, mypassword
	AWS = custom, s1.k8s.com, 8888, rc4, mypassword
	K8S = custom, s2.k8s.com, 8888, rc4, mypassword
	```
- 部分服务器走国外代理
	
	```
	DOMAIN-SUFFIX,lookup-api.apple.com,SS-SERVER,force-remote-dns
	DOMAIN,accounts.google.com,SS-SERVER,force-remote-dns
	DOMAIN-SUFFIX,googleapis.com,SS-SERVER,force-remote-dns
	DOMAIN-SUFFIX,bintray.com,SS-SERVER
	DOMAIN-SUFFIX,github.com,SS-SERVER
	DOMAIN-SUFFIX,cnn1.cache.amazonaws.com.cn,K8S,force-remote-dns
	DOMAIN-SUFFIX,svc.cluster.local,K8S,force-remote-dns
	DOMAIN-SUFFIX,ruguoapp.com,DIRECT
	```

- 配置 surge IP-CIDR 规则使得特定 ip 段走各自代理服务器:

	```
	IP-CIDR,10.0.0.0/16,DIRECT
	IP-CIDR,10.1.0.0/16,AWS
	IP-CIDR,10.2.0.0/16,K8S
	```

`enhanced-mode` 使得我们能够代理非 http 的其它基于 TCP 协议的请求，如上配置我们能够使得 git ssh 协议也走代理。

`force-remote-dns` 表示使用远程服务器来解析我们的域名，一方面可以让代理服务器拿到适合他自己位置的CDN地址，另外一方面可以防止本地DNS被劫持造成的影响，而对于 k8s 而言，这个设置还有一个好处是能够不需要本地解析 k8s 的 service name , 因为本地本身也没有能力去解析这个域名。而由于我们的 ss server 本身就架设在 k8s 内部，所以它完全有能力来解析这个域名。

完整的 Rule 配置如下:

```
[General]
loglevel = notify
skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, localhost
dns-server = system, 114.114.114.114, 223.5.5.5, 119.29.29.29
external-controller-access = xxx@0.0.0.0:8888
bypass-system = true
bypass-tun = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, localhost
enhanced-mode-by-rule = true
replica = false
ipv6 = false
interface = 0.0.0.0
port = 6152
socks-port = 6153

[Replica]
hide-apple-request = true

[Proxy]
SS-SERVER = custom, s1.k8s.com, 8888, rc4, mypassword
AWS = custom, s1.k8s.com, 8888, rc4, mypassword
K8S = custom, s2.k8s.com, 8888, rc4, mypassword

[Rule]
DOMAIN-SUFFIX,lookup-api.apple.com,SS-SERVER,force-remote-dns
DOMAIN,accounts.google.com,SS-SERVER,force-remote-dns
DOMAIN-SUFFIX,googleapis.com,SS-SERVER,force-remote-dns
DOMAIN-SUFFIX,bintray.com,SS-SERVER
DOMAIN-SUFFIX,github.com,SS-SERVER
DOMAIN-SUFFIX,cnn1.cache.amazonaws.com.cn,K8S,force-remote-dns
DOMAIN-SUFFIX,svc.cluster.local,K8S,force-remote-dns
DOMAIN-SUFFIX,ruguoapp.com,DIRECT

IP-CIDR,10.0.0.0/16,DIRECT
IP-CIDR,10.1.0.0/16,AWS
IP-CIDR,10.2.0.0/16,K8S

GEOIP,CN,DIRECT

FINAL,SS-SERVER
```

- `GEOIP,CN,DIRECT` 表示中国的IP都直连
- `FINAL,SS-SERVER` 表示其余的都走代理

之后我们就可以删掉一切之前接触过的网络工具，只需开一个 surge, 并且设置为系统代理和开启增强模式，我们能够实现的功能千言万语只能用一个成语来形容 : `四海为家`。

下面是这种`四海为家`式体验的生活描述:

1. 当我们想访问 k8s 的服务例如 `http://xxx.default.svc.cluster.local:3000` 的时候，我们直接在浏览器里输入，surge 匹配到规则里的后缀将它发送到代理服务器并解析出IP就能直接访问。
2. 如果我们需要使用 MongoDB GUI 程序(Robo 3T.app) 时，不需要去配置什么代理，直接连 `mongodb://username:pass@10.1.0.5:30001/db?authSource=admin&replicaSet=rs0` , surge 会直接代理 mongo 的协议(也是基于TCP的)。
3. 当你要 git clone 一个 ssh 地址时，它也会自动去走代理。而不需要去配置 gitconfig 文件。
4. 如果你需要连接线上服务器的 redis 也只需要直接从本地执行 redis-cli , 不需要连到线上服务器
5. 同时你可以流畅地使用任何邮件客户端收发 gmail ，而不用管该客户端是否是smtp还是https。
6. 你可以自由访问一切国外网站。
7. 当你访问国内网站依旧是以本地网络出去，闲暇摸鱼 bilibili 而不担心速度。
8. 偶尔你需要手机抓包或者电脑抓包，直接打开 Surge Dashboard 而无需配置，即便是在电脑上抓手机包亦是如此(必须在同一个局域网下，surge for ios 会自动传输数据到 Mac 客户端上)

作为内部工具更为重要的是，如果你想把同样的工作体验传播给同事，仅需给他一个几十行的配置文件即可，而他并不需要知道任何网络知识，导入直接上手。

### 一些可能的问题

对于生产环境的访问严格讲不应当过于方便，过度的方便可能也会导致人为误操作的风险。所以建议仅仅放入一些安全性较低的子网进配置文件。

关于 ss server 的鉴权目前普遍是用端口区分的形式，我们内部本身就存有一套鉴权体系，所以打算有空的时候 fork 下 ss 的代码加入内部鉴权机制，便于管理。

如果你们公司内部不是使用surge，其实你也可以考虑使用 `Proxifier` 实现同样的需求，只不过用起来不如surge来得方便。

