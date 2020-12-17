---
title: Golang rand 库锁竞争优化
date: 2020-12-17
categories: ['Golang']
draft: false
---

# 背景

最近在实现一个随机负载均衡器的时候发现一个问题，在高并发的情况下，官方标准库 `rand.Intn()` 性能会急剧下降。翻了下实现以后才发现它内部居然是全局共享了同一个 [globalRand](https://github.com/golang/go/blob/master/src/math/rand/rand.go#L293) 对象。

一段测试代码：

```go
func BenchmarkGlobalRand(b *testing.B) {
   b.RunParallel(func(pb *testing.PB) {
      for pb.Next() {
         rand.Intn(100)
      }
   })
}

func BenchmarkCustomRand(b *testing.B) {
   b.RunParallel(func(pb *testing.PB) {
      rd := rand.New(rand.NewSource(time.Now().Unix()))
      for pb.Next() {
         rd.Intn(100)
      }
   })
}
```

输出：

```go
BenchmarkGlobalRand
BenchmarkGlobalRand-8 18075486 66.1 ns/op
BenchmarkCustomRand
BenchmarkCustomRand-8 423686118 2.38 ns/op
```

# 解决思路

最理想对情况是可以在每个 goroutine 内创建一个私有的 rand.Rand 对象，从而实现真正的无锁。

但在很多其他场景下，我们并不能直接控制调用我们的 goroutine，又或者 goroutine 数量过多以至于无法承受这部分内存成本。

此时的一个思路是使用 `sync.Pool` 来为 rand.Source 创建一个池，当多线程并发读写时，优先从自己当前 P 中的 poolLocal 中获取，从而减少锁的竞争。同时由于只是用 pool 扩展了原生的 rngSource 对象，所以可以兼容其 rand.Rand 下的所有接口调用。

基于这个思路，实现了一个 [fastrand](https://github.com/joway/fastrand) 库放到了 github。

从 benchmark 中可以看到性能提升显著，在并发条件下，比原生全局 rand 快了大约 8 倍.

```
BenchmarkStandardRand
BenchmarkStandardRand-8                         60870416                19.1 ns/op             0 B/op          0 allocs/op
BenchmarkFastRand
BenchmarkFastRand-8                             100000000               10.7 ns/op             0 B/op          0 allocs/op
BenchmarkStandardRandWithConcurrent
BenchmarkStandardRandWithConcurrent-8           18058663                67.8 ns/op             0 B/op          0 allocs/op
BenchmarkFastRandWithConcurrent
BenchmarkFastRandWithConcurrent-8               132542940                8.79 ns/op            0 B/op          0 allocs/op
```
