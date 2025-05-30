---
title: 重新思考 Go：垃圾回收与编程经济学
date: 2024-03-30
categories: ["Tech"]
draft: true
---

> 重新思考 Go 系列：这个系列希望结合工作中在 Go 编程与性能优化中遇到过的问题，探讨 Go 在语言哲学、底层实现和现实需求三者之间关系与矛盾。

---

Go 是一门带 GC 的语言，编程者既不需要思考创建的对象分配在栈或是堆上，亦不需要思考合适销毁堆上的对象。大部分现代语言尤其是广受流行的语言，已经很少会再要求编程者主动管理对象的释放，但是具体对于对象生命周期的管理做法上不同语言各有千秋，从运行时垃圾回收器自动扫描，再到 Rust 这类编译期所有权主动声明。

之前听说过一个不知真假的段子，说是导弹的软件代码就不需要释放资源，只需要内存大小足够软件运行到爆炸之前就足够。不管这个段子真假与否，在我的职业生涯里遇到过不止一个核心系统，因为各种查不清，修不完的内存泄漏问题，重度依靠着定时重启进程来解决内存泄漏问题。

编程语言的技术路线决策，也和现实世界对编程的需求以及实际硬件的价格息息相关。如果今天内存是以 PB 计算的，恐怕与其精心管理对象的生命周期，不如花更多时间研究关于进程无损重启的技术更或者是彻底忘记内存这件事更符合现实。

所以这里希望引入一个新的名词来讨论这件事：「编程经济学」。编程经济学由三方面组成：**开发效率**，**编译耗时**，**运行性能**。其中，「编程时」与「编译期」基本可以等同于开发者的脑力与时间成本，或者简单称之为「开发效率」。而「运行时性能」则取决于实际硬件在运行软件时所能发挥出来的性能，一般而言，开发者常常需要针对硬件精细规划才能最大程度地发挥出硬件性能，也就是开发者的脑力劳动时间会在这时候转化为软件的运行时性能。

众多语言的不同技术选择，往往就是在编程经济学中，选择了自己的象限创立了自己的门派。我们可以列举一些常见的语言看他们的编程经济学选择，用 0-9 分代表每一部分权重：

- Python

  - 编程时效率: 9
  - 编译期耗时: 0
  - 运行时性能: 3

- Java

  - 编程时效率: 6
  - 编译期耗时: 3
  - 运行时性能: 6

- C

  - 编程时效率: 3
  - 编译期耗时: 6
  - 运行时性能: 9

- Rust

  - 编程时效率: 2
  - 编译期耗时: 9
  - 运行时性能: 9

- Go
  - 编程时效率: 8
  - 编译期耗时: 3
  - 运行时性能: 5

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
