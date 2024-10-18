---
title: 对 Go 语言的批判思考
date: 2024-03-30
categories: ["Tech"]
draft: true
---

协程原本的思想是程序通过约定的方式彼此协作，达到公共资源利用的最优解。在 Go 中，协程之间的协作是隐式的，几乎所有接口函数都是以同步的方式书写，在底层实现中才会真正决定是否让渡给其他协程执行。

这种实现方式，好处是解放了编程者的心智负担，坏处是编程者几乎不再有能力去设计自己的并发模型。以一段最简单的代码为例：

```go
//go:noinline
func fibonacci(num int) int {
	if num < 2 {
		return 1
	}
	return fibonacci(num-1) + fibonacci(num-2)
}

var wg sync.WaitGroup
for i := 0; i < 4; i++ {
    wg.Add(1)
    go func() {
        defer wg.Done()
        x := fibonacci(32)
        _ = x
    }()
}
wg.Wait()
```

在 CPU 资源足够的情况下，我们期望的是 4 个线程使用 4 个 CPU cores，并行执行 4 个 goroutine。理论上，每个 goroutine 的执行时间应该是接近的。然而实际情况是，让我们将这段代码跑 1000 次，得到最短的耗时情况为 `avg=7.35ms min=7.15ms max=14.48ms`。可以看到，最短耗时和最长耗时相差了近一倍。

实际上，这其中的差异在于，Go 调度器并非是一个可预测的调度模型。任意其他 Goroutine 的运行时行为以及垃圾回收器都有能力中断我们当前 Goroutine 的执行。

### 什么是 Go 协程真正的问题？

对于性能优化而言，没有什么比编程者自身对代码的精细规划更为重要。而 Go 在设计上就已经拒绝了编程者主观能动性对性能的参与。

#### 抢占让效率更低

由于不同 Goroutine 与线程并没有亲和性，所以我们没有能力做到诸如某一个请求的协程都尽可能在同一个线程上执行这样的要求。更加糟糕的是，由于 Go 协作抢占的实现是在函数入口插入抢占判断，一旦像是序列化这类重计算函数被抢占，整个 Cache 都会被无意义地切换走。而下一次继续执行时，只会更慢。并且这种抢占还无法在编程时禁止。

#### 捆绑销售 Runtime

## 内存管理

### 内存分配：不应该低估 make 的耗时

```go
costs := make([]time.Duration, 0, 10000000)
var buf []byte
for i := 0; i < cap(costs); i++ {
    begin := time.Now()
    buf = make([]byte, 1000)
    costs = append(costs, time.Since(begin))
}
```

### 垃圾回收：不应该低估 make 的耗时

## 重新思考 Go
