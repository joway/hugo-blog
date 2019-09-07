---
title: "Lemon : Koa 风格的 Python 异步 Web 框架"
date: 2018-01-08
draft: false
aliases: [
    "/Lemon/lemon-overview/",
]
---

前段时间想要写一些简短高效的 API ，背后的工作无非就是一些计算和数据处理，但是可能并发量会比较高。当我在 Python 的生态里去搜寻一些靠谱的 Web 框架时，很难找到一个设计优秀且运行效率高的框架。尤其是当我已经习惯了 NodeJS 的 Koa 那种简洁明了的设计时，很难再喜欢上像 Flask 那种装饰器的写法和各种概念拢杂在一起的设计。最后实在没有办法，就自己写了个符合我个人审美的框架 [Lemon](https://github.com/joway/lemon) 。

## 什么是 Web 框架

在讲 Lemon 的设计前，我们先来看一看一个请求是如何被响应的 ，以及框架在其中的作用是什么 :

当一个请求从客户端进入服务器，首先以 TCP 包的形式被接收到，这个时候我们需要手动去建立连接，接收到 TCP 报文后我们需要去判断它的协议，然后再解成相应协议(一般都是HTTP协议)的报文，传给 application 去处理，当处理完后还要把结果写回成 TCP 报文传回去，如果有 keep alive 还需要去手动管理这个连接的生命周期。以上这些统称为 server 部分。

而和开发者关系最密切的 application 部分做的就是拿到一个 http 或其它协议的报文，然后根据其信息做针对性的响应，传给 server 。

无论你是使用任何语言任何框架，都逃不开上面这个处理过程。而我们在比较框架的时候，无外乎是对以下几个方面做一些针对性的优化:

1. TCP报文解析成 HTTP(或其它协议) 报文的效率
2. 并发策略 (多线程，多进程，协程，线程池，Event Loop)
3. application 本身的运行效率 (由框架的效率，所用的语言和使用者自身的代码质量共同决定)

对于第一点，python有一个叫 [httptools](https://github.com/MagicStack/httptools) 的库就是使用了 NodeJS 的 http parser 以达到高性能解包的目的。

针对第二点，有许多OS层面和工程层面的技术在致力于解决这个问题。[uvloop](https://github.com/MagicStack/uvloop) 就是其中的一种，采用事件循环的方式，底层用的是 libuv , 同样也是 NodeJS 的底层异步IO库 。

第三点可能是我们大部分人的考虑的重点，需要各自根据团队情况，在开发效率和运行效率中间进行权衡。作为框架本身，它能够做的极致就是不给 application 拖后腿，而现实中，大部分时间其实都是在运行用户自己编写的代码。

当我们在谈论一个 Web 框架的时候，更多是在谈论第三点 application 的部分。第一二两点是 server 的实现部分。大部分时候，框架自身并不会去实现一个完整的 server 。为了让我们使用各种框架来进行开发的 application 能够在不同 server 中可以运行，会指定一些接口标准，在 Python 里同步的比如 wsgi , 异步的比如 asgi 。

对于 application 部分，显然所用语言已经限定了，而代码质量又取决于开发者自己的造化，那么框架能够做的，就是帮开发者简化编写业务逻辑的困难，形成一套代码的格式与套路。而许多人关心的框架的并发能力和运行效率，大多时候并不取决于框架自己，而是依赖于 server 的实现 。

Lemon 想要做的，就是在第一二层利用已有的最新的技术实现其高效率能力，而在 application 层，做一个设计简单，使用舒适的 API 框架。

## Lemon 初探

Python 3.5 以上已经支持类似 NodeJS 的那种 async 的写法了，加上[uviloop](https://github.com/MagicStack/uvloop) 这个高性能事件循环库。我们完全可以借助这两个在 Python 里实现一个类 Koa 的异步 Web 框架。

在 Lemon v0.0.1 版本的时候，我用 [uvloop](https://github.com/MagicStack/uvloop) 和 [httptools](https://github.com/MagicStack/httptools) 自己去实现了一个 server 。但是后来发现这件事情要做得好且稳定还是挺复杂的。偶然间发现了 [uvicorn](https://github.com/encode/uvicorn) 这个项目，代码写的非常优雅，而且也是用的 uvloop 和 httptools , 很适合作为一个 server 来使用。于是后来就又删掉了我自己的 server , 转而使用 uvicorn 。

[Sanic](https://github.com/channelcat/sanic/) 的架构和上述很像，但是它没有用 uvicorn 而是自己写了一套 server 并且它是基于 Flask 的 API 风格的，项目也写的比较乱。

在 Lemon 中，一个 application 的设计是这样的 :

```python
async def middleware1(ctx, nxt):
    ctx.body = {
        'msg': 'hello'
    }
    await nxt()

	
async def middleware2(ctx: Context):
    ctx.body['ack'] = 'yeah !'
	
app = Lemon()
	
app.use(middleware1, middleware2)
	
app.listen()
```

这种设计思路非常简单，就是用 `一条函数链` 描述整个请求过程 。`ctx` 作为传递各种参数的媒介，每个 middleware 都有能力直接返回结果或者传递给下一个 middleware 。

那么如果我们要设计路由该怎么做呢 ? 很简单，路由就是最前面的 middleware1 ，由它去拿 ctx.path 然后决定要走哪个函数。

同样的全局的错误处理或者鉴权处理都可以被抽象到这个 middleware 对象中来。这样在我们的设计里，就不会有那么多人为的概念。

我们可以看一下Flask框架中示例代码是怎么样的:

```python
@app.route('/<name>')
def hello_world(name):
    return jsonify({
        'hello': 'flask',
    })

app.run()
```

首先它用一些很魔法的设计，强制我的 hello_world 函数必须接受一个叫 name 的参数，因为我在路由里命名了它。并且如果我要加一些中间件，我只能通过装饰器的方式去加，而且我还要时刻留心函数参数这件事情。如果我要拿请求参数，还要用一个全局的变量 `request` 去拿。这种局部不像局部，全局不像全局的方式非常的脏乱 。

## Lemon 模块设计

### Server

可以支持任何实现了 asgi 接口的 server 。默认调用 `app.listen()` 会启动一个 uvicorn server 。无需配置即可部署在生产环境中。

### Router

默认的 Router 使用了 Trie 树作为路由的数据结构。如果你使用的是 HTTP RPC Style 形式的 API ，可以使用 SimpleRouter ，直接用字典形式存储。你也可以自己继承 AbstractRouter 或 AbstractBaseRouter 实现你自己的 Router 。

### Context

`ctx` 实例，`ctx.state` : {...} 用来存储 middleware 链上的信息，供下游使用。

### Request 

`ctx.req` 的对象，存储客户端请求的所有信息。

### Response

`ctx.res` 的对象，存储返回的结果。

## Lemon 目前的状态

Lemon 目前还只是一个 alpha 的版本 , 并不建议在生产环境上用，我最近会去写一系 benchmark 和 稳定性测试。包括还需要完善使用文档，添加一些易用的功能。

我用我自己写的小工具测试了下, 结果如下:

#### Lemon

![Lemon](https://cdn.joway.io/images/1515340517.png?imageMogr2/thumbnail/!70p)

#### Sanic

![Sanic](https://cdn.joway.io/images/1515340610.png?imageMogr2/thumbnail/!70p)

#### Flask

![Flask](https://cdn.joway.io/images/1515340570.png?imageMogr2/thumbnail/!70p)

测试结果很符合预期，因为和 Sanic 用的底层技术都差不多，所以两者性能几乎一样。之后会做更为广泛和专业的测试。


## 项目地址

[https://github.com/joway/lemon](https://github.com/joway/lemon)