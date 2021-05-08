---
title: RPC 漫谈： 连接问题
date: 2021-05-06
categories: ["Tech"]
draft: false
---

## 什么是连接

在物理世界并不存在连接这么一说，数据转换为光/电信号后，从一台机器发往另一台机器，中间设备通过信号解析出目的信息来确定如何转发包。我们日常所谓的「连接」纯粹是一个人为抽象的概念，目的是将传输进来的无状态数据通过某个固定字段作为标识，分类为不同有状态会话，从而方便在传输层去实现一些依赖状态的事情。

以 TCP 为例，一开始的三次握手用来在双方确认一个初始序列号（Initial Sequence Numbers，ISN），这个 ISN 标志了一个 TCP 会话，并且这个会话有一个独占的五元组（源 IP 地址，源端口，目的 IP 地址，目的端口，传输层协议）。在物理意义上，一个 TCP 会话等价于通往某一个服务器的相对固定路线（即固定的中间物理设备集合），正是由于这样，我们去针对每个 TCP 会话进行有状态的拥塞控制等操作才是有意义的。

## 连接的开销

我们常常听到运维会说某台机器连接太多所以出现了服务抖动，大多数时候我们会接受这个说法然后去尝试降低连接数。然而我们很少去思考一个问题，在一个服务连接数过多的时候，机器上的 CPU，内存，网卡往往都有大量的空余资源，为什么还会抖动？维护一个连接的具体开销是哪些？

**内存开销：**

TCP 协议栈一般由操作系统实现，因为连接是有状态对，所以操作系统需要在内存中保存这个会话信息，这个内存开销每个连接大概 4kb 不到。

**文件描述符占用：**

在 Linux 视角中，每个连接都是一个文件，都会占用一个文件描述符。文件描述符所占用的内存已经计算在上面的内存开销中，但操作系统为了保护其自身的稳定性和安全性，会限制整个系统内以及每个进程中可被同时打开的最大文件描述符数：

```sh
# 机器配置: Linux 1 核 1 GB

$ cat /proc/sys/fs/file-max
97292

$ ulimit -n
1024
```

上面的设置表示整个操作系统最多能同时打开 97292 个文件，每个进程最多同时打开 1024 个文件。

严格来说文件描述符根本算不上是一个资源，真正的资源是内存。如果你有明确的需要，完全可以通过设置一个极大值，让所有应用绕开这个限制。

**线程开销：**

有一些较老的 Server 实现采用的还是为每个连接独占（新建或从连接池中获取）一个线程提供服务的方式，对于这类服务来说，除了连接本身占用的外，还有线程的固定内存开销：

```sh
# 机器配置: Linux 1 核 1 GB

# 操作系统最大线程数
$ cat /proc/sys/kernel/threads-max
7619

# 操作系统单进程最大线程数，undef 表示未限制
$ cat /usr/include/bits/local_lim.h
/* We have no predefined limit on the number of threads.  */
#undef PTHREAD_THREADS_MAX

# 单个线程栈默认大小，单位为 KB
$ ulimit -s
8192
```

在上面这台机器里，允许创建的线程数一方面受操作系统自身设定值限制，一方面也受内存大小限制。由于 1024MB / 8MB = 128 > 7619 ， 所以这台机器中能够创建的最大线程数为 128。如果 Server 采用一个线程一个连接，那么这时 Server 同时最多也只能够为 128 个连接提供服务。

可以看出这种单连接单线程的模式会导致连接数大大地被线程数所制约，所以现代 Server 实现大多抛弃了这种模式，让单一线程专门处理连接。

## C10K 问题

通过上面的讨论，我们能够看到，真正制约了连接数量的，本质还是内存资源。其他变量要么可以通过修改默认参数绕开，要么可以通过更改软件设计而优化。但如果事实真的如此简单，为什么还会有著名的 [C10K](https://en.wikipedia.org/wiki/C10k_problem) 问题呢？

这其实纯粹是一个软件工程的问题，而非硬件问题。早期操作系统设计时，就没有考虑到未来会出现单机 10K 连接甚至更多的问题，所以在其接口上并未对这类场景进行优化，而在此之上的基础设施软件（例如 Apache）自然而然也就没有考虑到应对这类场景。

对于应用软件开发者而言，操作系统就如同法律，我们能够做什么并不全凭物理世界可以做什么，还要遵从操作系统允许我们做什么。

需要注意的是 C10K 问题指的是连接数，而非请求数。如果是 10K 的 QPS(Query per Second) 在一条连接上也能够进行，这也是为什么对于企业内网中的 RPC 调用而言，一般也不会出现 C10K 的问题。C10K 问题往往出现在诸如推送服务，IM 服务这类需要和海量客户端建立持久连接的场景。

在 Linux 语境下，连接被抽象为文件，所以 C10K 问题的关键在于 Linux 中所提供的 IO 接口设计是否可以应对大规模连接的场景，以及我们如何使用这些接口去实现能够支持高并发连接的软件架构。

### Linux IO 的历史演变

如果我们要一次处理多个连接（即多个文件描述符），那么必然需要操作系统能够提供给我们一个批量监听函数，让我们能够同时去监听多个文件描述符，并且通过返回值告知我们哪些文件已经可读/可写，然后我们才能去真正操作这些已经就绪的文件描述符。

Linux IO 的根本性工作无非就是上面这些，看上去并不是什么复杂的设计，但是这部分工作在历史上的不同实现方式却深刻影响了后来的应用软件发展，也是很多基础软件之间核心区别所在。

#### select, 1993

select 的函数签名：

```cpp
#define __FD_SETSIZE 1024

typedef struct
  {
    __fd_mask fds_bits[__FD_SETSIZE / __NFDBITS];
  } fd_set;

int select (int nfds, fd_set *readfds, fd_set *writefds, fd_set *exceptfds,
          struct timeval *timeout)
```

使用方式：

```cpp
// 初始化文件描述符数组
fd_set readfds;
FD_ZERO(&readfds);

// socket1, socket2 连接注册进 readfds
FD_SET(conn_sockfd_1, &readfds);
FD_SET(conn_sockfd_2, &readfds);

// 循环监听 readfds
while(1)
{
    // 返回就绪描述符的数目
    available_fd_count = select(maxfd, &readfds, NULL, NULL, &timeout);

    // 遍历当前所有文件描述符
    for(fd = 0; fd < maxfd; fd++)
    {
        // 检查是否可读
        if(FD_ISSET(fd, &readfds))
        {
            // 从 fd 读取
            read(fd, &buf, 1);
        }
    }
}
````

select 函数在大规模连接时的缺陷主要在以下两方面：

- **线性遍历所有文件描述符，O(N)  复杂度**：

  select 函数本身并不返回具体哪些文件描述符就绪，需要用户自己去遍历所有文件描述符，并通过 FD_ISSET 来判断。连接少时影响并不大，但当连接数达到 10K，这个 O(N) 复杂度造成的浪费也会非常夸张。
- **fd_set 大小限制**：
  
  fd_set 结构背后是一个位图，每一位代表一个文件描述符但就绪状态，1 代表就绪。Linux 默认 FD_SETSIZE 为 1024，也就是实际大小为 1024/8bits = 128 bytes。并且这部分内存最后会被拷贝到内核态，也会造成拷贝上的开销。

这种设计看起来粗糙，但是好处是可以很好应对排队问题。如果某个连接特别繁忙，也不会影响这个系统调用本身的性能，因为它只关心是否就绪，不关心具体有多少数据待处理。在 2000 年 Linus 的 [邮件](http://lkml.iu.edu/hypermail/linux/kernel/0010.3/0003.html) 中可以看到更多相关讨论。

#### poll, 1998

poll 函数的签名：

```cpp
struct pollfd
  {
    int fd;             /* File descriptor to poll.  */
    short int events;   /* Types of events poller cares about.  */
    short int revents;  /* Types of events that actually occurred.  */
  };

int poll (struct pollfd *fds, nfds_t nfds, int timeout)
```

使用方式：

```cpp
// 初始化 pollfd 数组
int nfds = 2
struct pollfd fds[fds_size];
fds[0].fd = STDIN_FILENO;
fds[0].events = POLLIN;
fds[1].fd = STDOUT_FILENO;
fds[1].events = POLLOUT;

// 监听 pollfd 数组内的文件描述符
poll(fds, nfds, TIMEOUT * 1000);

// 遍历 fds
for(fd = 0; fd < nfds; fd++)
{
    // 是否是读取事件
    if (fds[fd].revents & POLLIN)
    {
        // 从 fd 读取
        read(fds[fd].fd, &buf, 1);
    }
}
```

poll 相比 select 的差异主要有两个：
1. 通过 pollfd 统一 readfds, writefds, exceptfds 三种事件类型。
2. 通过 pollfd[] 数组传递需要监听的文件描述符，不再限制文件描述符数量。（内核将数组转换为链表）。

但在 poll 发明的 1998 年，大规模网络基础设施依然不是一个普遍的需求，所以这次 API 增加并没有解决前面说的在大规模连接下，需要遍历所有文件描述符的问题。但就在 poll 发布后的 1999 年发生了几件事情：
1. C10K 问题被正式提出
2. HTTP 1.1 发布，在这一版本引入了 keep alive 的持久连接概念
3. QQ 发布

并且在 00 年前后 2C 互联网引来了大爆发和大泡沫的时代。

在 QQ 发布的年代，这个问题是无解的，这也是为什么像 QQ 这种面向会话而生的应用，却抛弃了面向会话的 TCP 协议，而使用的是 UDP。

#### epoll, 2003

epoll 函数签名：

```cpp
typedef union epoll_data {
    void    *ptr;
    int      fd;
    uint32_t u32;
    uint64_t u64;
} epoll_data_t;

struct epoll_event {
    uint32_t     events;    /* Epoll events */
    epoll_data_t data;      /* User data variable */
};

int epoll_create(int size);
int epoll_ctl(int epfd, int op, int fd, struct epoll_event *event);
int epoll_wait(int epfd, struct epoll_event *events,
                 int maxevents, int timeout);
```

使用方式：

```cpp
#define MAX_EVENTS 10
struct epoll_event ev, events[MAX_EVENTS];
int listen_sock, conn_sock, nfds, epollfd;

// 创建 epollfd 对象，后续 epoll 操作都围绕该对象
epollfd = epoll_create(10);

// 对 ev 绑定关心对 EPOLLIN 事件，并注册进 epollfd 中
ev.events = EPOLLIN;
ev.data.fd = listen_sock;
if(epoll_ctl(epollfd, EPOLL_CTL_ADD, listen_sock, &ev) == -1) {
   perror("epoll_ctl: listen_sock");
   exit(EXIT_FAILURE);
}

for(;;) {
    // 传入 events 空数组，阻塞等待直到一有就绪事件便返回，返回值为有效事件数
    nfds = epoll_wait(epollfd, events, MAX_EVENTS, -1);
    if (nfds == -1) {
        perror("epoll_pwait");
        exit(EXIT_FAILURE);
    }

    // 只需要遍历有效事件即可
    for (n = 0; n < nfds; ++n) {
        if (events[n].data.fd != listen_sock) {
            //处理文件描述符，read/write
            do_use_fd(events[n].data.fd);
        } else {
            //主监听socket有新连接
            conn_sock = accept(listen_sock,
                            (struct sockaddr *) &local, &addrlen);
            if (conn_sock == -1) {
                perror("accept");
                exit(EXIT_FAILURE);
            }
            setnonblocking(conn_sock);
            
            //将新连接注册到 epollfd 中，并以边缘触发方式监听读事件
            ev.events = EPOLLIN | EPOLLET;
            ev.data.fd = conn_sock;
            if (epoll_ctl(epollfd, EPOLL_CTL_ADD, conn_sock,
                        &ev) == -1) {
                perror("epoll_ctl: conn_sock");
                exit(EXIT_FAILURE);
            }
        }
    }
}
```

epoll 有以下几个特点：
1. 每个文件描述符，只会在创建时，被 epoll_ctl 拷贝一次。
2. epoll_wait 只有大小有限的参数，从而避免了频繁进行用户态到内核态的拷贝。
3. epoll_wait 只返回就绪状态的文件描述符，避免了对所有文件描述符去遍历。

因此，当连接数线性增多时，epoll 调用本身的性能并不会线性增大。现代 Server 在 Linux 平台下大多已经转向使用 epoll 来实现。

### 高并发服务设计

我们可以把 C10K 问题拆解成以下三个子问题：
1. 如何高效地**建立**大量连接 (accept)
2. 如果高效地**读写**大量连接（read/write）
3. 如何高效地**处理**大量请求

这三个子问题的区别是，建立连接只会在一开始占用 CPU，连接建立完成后，只会占用内存资源，并且每次建立连接所消耗的资源都是固定的。但每个连接上的读写操作以及对请求数据的处理却会频繁消耗不可预计的 CPU 与 内存资源，且连接间和请求间的差异会非常大。

#### 如何高效建立连接

由于建立连接消耗的资源是固定的，假设需要 x ms，如果我们用一个单线程，只负责监听 listen port 文件描述符，创建新连接但不负责对其进行读写。那么该线程每秒能够创建的连接数应该是 1000/x 。

一般来说，创建连接本身的消耗非常少，单线程足以应对 10K 甚至更高的并发。

#### 如何高效读写连接

我们通过前一个步骤已经确保服务能够高效建立新连接，而对于这些新连接的读写任务工作量我们实现并无法准确估算，所以需要有一个线程池专门去使用 epoll_wait 批量监听连接事件，并进行真正的读写操作。但这里的读写操作涉及到 epoll 的两种通知模式 ———— **水平触发**和**边缘触发**。

对于 select/poll 而言，获取的都是文件描述符就绪的列表，每次调用只会去检查是否可读/可写的状态，拿到可用描述符后，进行读写，然后再进行下一次 select/poll。如果没有读完，下一次调用 select/poll 时，还会继续返回可读状态，只要继续去读就没问题。如果没有写完，当下一次回到可写时状态时，可以继续写。epoll 同样也有这类模式，我们将这种处理称之为**水平触发**。

与水平触发对应的是边缘触发，他们的命名来自电平的概念：

```text
Level Triggered:
        ......
        |    |
________|    |_________


Edge Triggered:
          ____
         |    |
________.|    |_________

// "." 表示触发通知
```

**边缘触发**只有在从无数据到有数据时通知一次，后续调用都返回 False。所以当收到通知后，必须去一次性读完文件所有内容。而如果某个连接极端繁忙，这个时候就会出现饥饿现象。但这类饥饿现象和 epoll 或是边缘触发关系都不大，纯粹是我们在代码实现时，需要多考虑到均衡读写的情况。如果在水平触发的模式下，也总是去尝试一次性读完所有内容，依然会存在饥饿现象。

对于绝大多数小体积消息而言，无论哪种触发方式都能够快速读完消息，差别不大。但对于大体积的消息，诸如视频这种，水平触发的方式会导致 epoll_wait 频繁被唤醒，相比于边缘触发会多很多次系统调用，所以性能会更差。

#### 如何高效处理请求

对于绝大部分业务来说，业务逻辑的处理才是真正耗费资源的操作，因此我们不能将这部分操作放进 IO 线程内进行，否则会影响到这个线程中监听的其他连接。所以需要单独再开辟一个工作线程池去处理业务逻辑本身。

归根结底，对于消耗少且固定的任务，可以使用单线程。对于消耗不确定的任务，需要使用线程池。

#### 最终架构

通过上面一系列任务拆分，我们可以得到一个业内称之为主从 Reactor 的支持高并发的服务模型：

```
     单线程                         线程池                         线程池
[ Main Reactor ] == 新连接 ==> [ Sub Reactor ] <-- Data --> [ Worker Thread ]
    建立新连接                      读写连接                      业务逻辑处理
```

这个模型也是 Java 的 Netty 框架，和 Go 的 [gnet](https://strikefreedom.top/go-event-loop-networking-library-gnet) 框架的实现基础。

互联网业务有红利，基础设施软件的变革也有红利。Epoll 就是上个 10 年最大的一个红利之一。

## 连接池 VS 多路复用

对于连接的管理有两种基本思想：**连接池**和**多路复用**。

连接是请求的传输载体，一个请求包含一来一回，即一个 RTT 时间。连接池一般是指每个连接同时只为一个请求提供服务，也就是一个 RTT 内只会存在一个请求，此时如果存在大量并发请求必须使用一个**连接池**来管理生命周期。但连接本身是全双工的，完全可以一直发送 Request，一直发送 Response，这也是**多路复用**的含义，但这需要应用层协议支持对给每个包标定一个 ID 来用以分割不同请求和响应。

HTTP 1.0 协议就是因为并未对每个请求标定 ID，所以在实现上不可能支持多路复用。而在 HTTP 1.1 协议中，增加了 Keep-Alive 连接保活以及 Pipeline 的概念，请求可以不停发，但是 Response 返回的顺序必须是发送时的顺序，以此来尽可能复用连接。但是 Pipeline 对 Response 顺序的要求会导致如果某个请求处理时间比较长，那么后面的返回会一直堆积。1.1 因为是 1.0 的修订版，所以不太可能增加太多不兼容的变更。但在 HTTP 2.0 中，就增加了 stream ID 来实现多路复用的能力。

Thrift 协议也会在开头(8~12 bytes)标明自己的序列号 ID，所以也能很好支持多路复用。

但是主流数据库协议如 Mysql 却大多都不支持连接的多路复用，这也是为什么我们经常会需要去配置数据库连接池的原因。数据库的大部分时间消耗在磁盘 IO 和 CPU 计算，使用连接池的方式可以保证有限度的并发请求量，一个接一个把活干完，如果出现繁忙状况，请求主要被阻塞在 Client 端。如果是多路复用的方式，Client 并没有办法准确估计出 Server 的负载能力，大量请求依旧会被发出去，阻塞在数据库侧，这个往往我们是不想看到的。另外，连接池的方式对于 Client 的实现来说往往也更加容易。

## Server Push

我们都知道连接本身是全双工的，Client 和 Server 之间想怎么发消息就怎么发，何况一个请求的返回消息本身就是一个字面意义的 Server Push。那为什么 HTTP 2.0 以及一些 RPC 协议还要去标榜自己支持 Server Push ？

这个问题本身又是一个软件工程的问题。我们已经习惯了用输入输出的模式去编程，所以在协议设计的时候，很少考虑到输入没输出，输出没输入的这种情况。Server Push 就属于一种输出没输入的情况。

在 HTTP 1.1 里，一个完整的消息应该如下：

```
=== Request ===
GET /hello.txt HTTP/1.1
User-Agent: curl/7.16.3 libcurl/7.16.3 OpenSSL/0.9.7l zlib/1.2.3
Host: www.example.com
Accept-Language: en, mi

=== Response ===
HTTP/1.1 200 OK
Date: Mon, 27 Jul 2009 12:28:53 GMT
Server: Apache
Last-Modified: Wed, 22 Jul 2009 19:15:56 GMT
ETag: "34aa387-d-1568eb00"
Accept-Ranges: bytes
Content-Length: 51
Vary: Accept-Encoding
Content-Type: text/plain

Hello World! My payload includes a trailing CRLF.
```

每个 Response 必须对应一个 Request，从代码侧来说，就是一个函数调用。试想如果此时 Server 在连接中，莫名其妙返回了一个客户端没有请求的 Response，代码实现上能怎么做？代码根本没调用，自然也就没地方在监听等待这个 Response ，自然没地方会去处理它。

后人在 HTTP 1.1 上所实现的所谓的长轮询，无非是利用长连接的特性，延迟发送了消息。与其说是什么新技术，不是说是投机取巧，但是的确在简单的场景下是一个好用的方案。要彻底解决问题必须修改协议，这也是为什么会有 WebSocket 和 HTTP 2.0 的原因。

在 HTTP 2.0 中，通过标记特殊的帧 PUSH_PROMISE 来表示这个消息是没有对应 Request 的，但具体实现的时候会发现，就算 Server 能够 Push 内容给 Client，Client 也需要去解析不同消息具体含义是什么。在传统模式下，一个 Response 的含义由 Request 决定，但现在一个没有 Request 的 Response 只能通过解析其内容决定。这就导致了实现这个解析的过程其实是可以各家自己定义自己的。对于浏览器标准而言，Server Push 一般用于静态资源，所以就需要建立一套资源缓存的标准。

而在 grpc 中，虽然底层用的是 HTTP 2.0 ，但并没有使用 PUSH_PROMISE 功能，就是因为对于 RPC 而言，我可以一个请求有多个返回（所谓的流模式），但是不能说没有请求直接有返回，否则用户处理侧会更加复杂且不统一了。grpc 使用流模式的示例：

```go
stream, err := streamClient.Ping(ctx)
err = stream.Send(request)
for {
    response, err := stream.Recv()
}
```

可以看出，Server Push 从来不是一项新技术，因为一直以来这功能就是 TCP 现成的。我们所缺少的，其实仅仅只是在应用层的操作规范而已。

## 最后

从 epoll 的诞生，到 Server Push 问题的解决，我们不难看到，所谓的新技术从更加宏观的视角来看压根就不能算是技术，仅仅只是一些对约定共识的改变而已。但就是这种共识的改变，可能会需要几十年的时间。

文明建立在共识的基础上，技术也是如此。文明的进步靠去破除女子无才便是德这类旧有的共识，技术的进步也是如此。
