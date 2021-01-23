---
title: "Pond: Golang 通用对象池"
date: 2021-01-23
categories: ['Tech']
draft: false
---

## 为什么需要通用对象池

在实际生产环境中，我们经常会遇到需要多线程共享同一堆对象的场景，例如常见的RPC、数据库连接池，大内存对象池，以及线程池等。这些池化对象的需求其实有很多重叠的地方，主要分以下几个方面：

1. 基础设置：
   1. 最大容量
   2. 创建/校验/删除对象的回调方法
   3. 申请对象时，已满时是否阻塞
2. 多重驱逐策略：
   1. 驱逐闲置对象
   2. 驱逐无效对象
3. 预创建对象

为避免重复编码，所以设计了 [Pond](https://github.com/joway/pond) 这样一个能够支撑多种使用场景的通用对象池。另外，在 Pond 的基础上，还实现了 Goroutine 池库： [Hive](https://github.com/joway/hive)。

## 使用方式

```go
//example
type conn struct {
	addr string
}

func main() {
	ctx := context.Background()
	cfg := pond.NewDefaultConfig()
	cfg.MinIdle = 1
	cfg.ObjectCreateFactory = func(ctx context.Context) (interface{}, error) {
		return &conn{addr: "127.0.0.1"}, nil
	}
	cfg.ObjectValidateFactory = func(ctx context.Context, object interface{}) bool {
		c := object.(*conn)
		return c.addr != ""
	}
	cfg.ObjectDestroyFactory = func(ctx context.Context, object interface{}) error {
		c := object.(*conn)
		c.addr = ""
		return nil
	}
	p, err := pond.New(cfg)
	if err != nil {
		log.Fatal(err)
	}

	obj, err := p.BorrowObject(ctx)
	if err != nil {
		log.Fatal(err)
	}
	defer p.ReturnObject(ctx, obj)
	fmt.Printf("get conn: %v\n", obj.(*conn).addr)
}
```

## 使用细则

### LIFO 驱逐策略

当前采用 LIFO 的驱逐策略，保证永远优先使用最常被使用的对象。之所以不采用 FIFO 是因为我们只有让热门的对象尽可能保持热门，而不是均衡每个对象的使用频率，才能够保证最大程度筛选出不常用的对象从而使其被驱逐。

### 避免频繁驱逐

某些情况下会出现不停创建新的对象，到了驱逐时间又被立马销毁的情况，从而使得对象池的大小出现不必要的频繁变动。这里我们可以通过 `MinIdleTime` 配置最小闲置时间，保证只有当对象闲置超过该时间后，才可能被驱逐。

### 对象校验

有一种情况是，一开始在池子里创建好了几个对象，但是当用户实际去取出来的时候，发现该对象其实已经被关闭或者失效了。所以在 Pool 内部需要每次取的对象都经过一次校验，如果校验不通过，则销毁对象，再次尝试去取。该策略还能保证当出现部分节点抖动时，会尽可能剔除不可用节点，提供稳定的对象。

同时为了避免当一些灾难情况下，永远无法成功创建对象（例如下游节点完全宕机），我们还需要设置 `MaxValidateAttempts` 以避免出现恶性循环。

### 预创建对象

在默认情况下，我们会在每次取对象的时候，判断是否需要创建新的，如需要再取实时创建。但如果创建操作比较费时，我们会希望在条件允许的情况下，池子里能够预留一部分空闲对象，以供未来调用。`MinIdle` 参数用以确保池子内最小能够拥有的空闲对象数。

### 超时取消

默认配置下，每次取对象如果当前池已满，且没有闲置对象，会阻塞住，直到能够获取到可用对象为止。我们使用 context 来实现获取超时取消的逻辑。一旦当触发 `ctx.Done()` 时候，会直接 return，并返回 `ctx.Err()` 。

## 高级扩展

Pond 是一个通用对象池，在此基础上，我们可以非常简单地实现诸如连接池，goroutine 池等多重应用。

以下示例展示了如何使用 Pond 创建一个简单的 goroutine 池：

### 实现 Worker 对象

Worker 结构体用以封装单个 goroutine：

```go
type Worker struct {
	jobs chan Job
}

func NewWorker() *Worker {
	w := &Worker{
		jobs: make(chan Job),
	}
	go w.Run()
	return w
}

func (w *Worker) Submit(task Task, callback Callback) {
	w.jobs <- Job{
		task:     task,
		callback: callback,
	}
}

func (w *Worker) Run() {
	for job := range w.jobs {
		if job.task != nil {
			job.task()
		}
		if job.callback != nil {
			job.callback()
		}
	}
}

func (w *Worker) Close() {
	close(w.jobs)
}
```

### 池化 Worker 对象

```go
pConfig := pond.NewDefaultConfig()
pConfig.MaxSize = h.Size
pConfig.Nonblocking = h.Nonblocking
pConfig.ObjectCreateFactory = func(ctx context.Context) (interface{}, error) {
    return NewWorker(), nil
}
pConfig.ObjectDestroyFactory = func(ctx context.Context, object interface{}) error {
    w := object.(*Worker)
    w.Close()
    return nil
}
workers, err := pond.New(pConfig)

object, err := workers.BorrowObject(ctx)
worker := object.(*Worker)
worker.Submit(func() {
    //do some task
}, func() {
    // when task finished, return object
    _ = h.workers.ReturnObject(ctx, object)
})
```
