---
title: Golang Interface 内部实现
date: 2021-01-20
categories: ['Tech']
draft: false
---

最近遇到一个由于 Golang Interface 底层实现，引发的线上 panic 问题，虽然根源在于赋值操作没有保护起来，却意外地发现了关于 interface 的一些有意思的底层细节。

假设我们现在有以下定义：

```go
type Interface interface {
    Run()
}

type Implement struct {
    n int
}

func (i *Implement) Run() {
    fmt.Printf(i.n)
}
```

对于使用者而言，一个变量无论是 `Interface` 类型或是 `*Implement` 类型，差别都不大。

```go
func main() {
    var i Interface
    fmt.Printf("%T\n", i) //<nil>
    i = &Implement{n: 1}
    fmt.Printf("%T\n", i) //*main.Implement

    var p *Implement
    fmt.Printf("%T\n", p) //*main.Implement
    p = &Implement{n: 1}
    fmt.Printf("%T\n", p) //*main.Implement
}
```

如果现在有这么一段代码：

```go
func check(i Interface) {
    if i == nil {
        return
    }
    impl := i.(*Implement)
    fmt.Println(impl.n) //Invalid memory address or nil pointer dereference
}
```

这段代码从逻辑上来说，`impl.n` 永远都不会报空指针异常，因为 i 如果为空就会提前返回了。而且就算 i 为 nil，在 `impl := i.(*Implement)` 类型转换的时候就会直接 panic，而不是在下一行。但在线上环境上却的确在 `impl.n` 位置报了错误。

在探究了 interface 底层实现后发现，在上面的 main 函数的例子里，i 和 p 虽然在使用方式上是一致的，但在内部存储的结构体却是不同的。`*Implement` 类型内部存储的是一个指针，对他赋值也只是赋予一个指针。而 `Interface` 接口底层结构却是一个类型为 `iface` 的 struct ：

```go
type iface struct {
    tab  *itab
    data unsafe.Pointer
}

type itab struct {
    inter *interfacetype
    _type *_type
    hash  uint32 // copy of _type.hash. Used for type switches.
    _     [4]byte
    fun   [1]uintptr // variable sized. fun[0]==0 means _type does not implement inter.
}
```

当对一个接口赋值时，即对该 struct 的 `tab` 与 `data` 字段分别赋值。而该操作并非是原子性的，有可能赋值到一半，也就是 `.tab` 有值而 `.data` 为空时，就被另一个 goroutine 抢走，并进行 `!= nil` 的判断。而 golang 却只有在 `iface` 两个属性同时为 nil 时候才认为是 nil，所以 check 函数内的 if 条件判断失效。

同时由于 `.tab` 内已经有了类型信息，所以在 `impl := i.(*Implement)` 类型转换的时候也能够成功转换，并不会报空指针错误，即便该 interface 的 `.data` 字段是 nil 。只有当实际去调用 `impl.n` 的时候，才会发现 `.data` 为 nil，从而 panic。
