---
title: 重新思考 Go：Slice 只是「操作视图」
date: 2024-03-30
categories: ["Tech"]
draft: false
---

> 重新思考 Go 系列：这个系列希望结合工作中在 Go 编程与性能优化中遇到过的问题，探讨 Go 在语言哲学、底层实现和现实需求三者之间关系与矛盾。

---

Go 在语法级别上提供了 Slice 类型作为对底层内存的一个「**操作视图**」:

```go
var sh []any
// ==> internal struct of []any
type SliceHeader struct {
	Data uintptr
	Len  int
	Cap  int
}
```

编程者可以使用一些近似 Python 的语法来表达对底层内存边界的控制:

```go
var buf = make([]byte, 1000)
tmp := buf[:100]       // {Len=100, Cap=1000}
tmp = buf[100:]        // {Len=900, Cap=900}
tmp = buf[100:200:200] // {Len=100, Cap=100}
```

虽然 Slice 的语法看似简单，但编程者需要时刻记住一点就是 **Slice 只是一个对底层内存的「**操作视图**」，而非底层「内存表示」，Slice 的各种语法本身并不改变底层内存**。绝大部分 Slice 有关的编程陷阱根源就在于两者的差异。

### Slice 陷阱：持有内存被「放大」

以最简单的从连接中读取一段数据为例，由于我们事先并不知道将会读取到多少数据，所以会预先创建 1024 字节的 buffer ，然而如果此时我们只读取到了 n bytes, n 远小于 1024，并返回了一个 `len=n` 的 slice，此时这个 slice 的真实内存大小依然是 1024。

```go
func Read(conn net.Conn) []byte {
	buf := make([]byte, 1024)
	n, _ := conn.Read(buf)
	return buf[:n]
}
```

即便上一步我们内存放大的问题并不严重，比如我们的 n 恰好就是 1024。但我们依然会需要对连接读到的数据做一些简单的处理，例如我们现在需要通过 Go 的 regexp 库查询一段 email 的数据：

```go
func FindEmail(data []byte) []byte {
	r, _ := regexp.Compile("\\w+@\\w+.\\w+")
	sub := r.Find(data)
	fmt.Println(len(sub), cap(sub)) // output: len=cap
	return sub
}

func (re *Regexp) Find(b []byte) []byte {
    // ...
	return b[a[0]:a[1]:a[1]]
}
```

正则函数返回的 slice，依然持有着整段连接数据。当我们的切片处理函数越来越多时，我们的系统中可能充斥着无数原始连接数据的子切片。而由于 Go 自带 GC 所以编程者很少会去思考内存和变量的生命周期，所以当众多代码中的某一个函数决定将某个数据字段比如这里的 email 字段放进一个全局对象中时，编程者通常不会想到主动去额外 copy 一份数据，而是直接把这个切片直接放入： `cache[email] = ...` 。此时，整段连接数据就会被一直持有引用而得不到释放。

像是这类问题由于过于容易犯错，所以很多复杂的业务系统中倘若仔细观察，多多少少都能发现类似的内存被「放大」的现象。但是由于 Go 本身内存占用就不大，大部分时候开发者仅在发现内存以肉眼可见的速度在持续上涨时，才会通过 profling 对其中问题最严重的那部分代码进行集中治理。

然而虽然 Go profling 工具链非常完善，但唯独在查找内存引用被哪些对象持有方面却几乎是空白的。这类问题只能依靠阅读每一行有可能持有底层内存引用的代码来逐个排查。

### Slice 陷阱： 指针元素无法被释放

当 Slice 中的元素类型为值类型时，Slice 指向的内存仅包含一段连续内存。然而，当 Slice 的元素类型为指针类型时，情况就会变得复杂了：

```go
type ConnPool struct {
	pool []net.Conn
}

func (p *ConnPool) Put(conn net.Conn) {
	p.pool = append(p.pool, conn)
}

func (p *ConnPool) Get() (conn net.Conn) {
	conn = p.pool[len(p.pool)-1]
	p.pool = p.pool[:len(p.pool)-1]
	return conn
}
```

这段代码是一个典型的 FILO 连接池实现，其中有一个隐蔽的 Bug 是，Get 函数在取了一个引用类型的元素后，没有将其底层内存上对应位置存储的指针引用置零，导致即便用户释放了连接对象后，这个 slice 底层一直持有该指针，仅当未来有机会被重新覆写时才会被释放。正确的写法是：

```go
func (p *ConnPool) Get() (conn net.Conn) {
	conn = p.pool[len(p.pool)-1]
	p.pool[len(p.pool)-1] = nil // reset to nil
	p.pool = p.pool[:len(p.pool)-1]
	return conn
}
```

然而，如果元素为值类型时，我们却并不需要做这类操作因为 slice 的底层内存大小已经固定，置零为空结构体没有任何意义。这种同一个类型同一个语法，却因元素类型而编程范式不一致的设计，极大地促使了这个编程错误出现的概率，对编程者的心智负担也极重。

### 性能问题： 低效的 memclr 行为

slice 最为常见的用法莫过于 `make slice and copy data` :

```go
buf := make([]byte, len(data))
copy(buf, data)

// => ASM
XORL    CX, CX ;; needzero = false
MOVQ    BX, AX ;; size = len(data)
XORL    BX, BX ;; type = nil
CALL    runtime.mallocgc(SB)
MOVQ    AX, main..autotmp_8+24(SP)
MOVQ    main.data+48(SP), BX
MOVQ    main.data+56(SP), CX
PCDATA  $1, $1
CALL    runtime.memmove(SB)

// runtime.mallocgc implementation
func mallocgc(size uintptr, typ *_type, needzero bool) {
    // ...
    if needzero && span.needzero != 0 {
	    memclrNoHeapPointers(x, size)
	}
}
```

这里 mallocgc 的第三个参数 `needzero` 被置为了 false，意味着这段内存我们并不需要调用底层的 `memclrNoHeapPointers`(类似于 C 中的 `memset`) 去清零整段内存。

然而，如果我们在 make 和 copy 之间插入一段 if 语句后，汇编就会变成：

```go
buf := make([]byte, len(data))
if len(data) < 10 {
    return data
}
copy(buf, data)

// => ASM
LEAQ    type:uint8(SB), AX
MOVQ    BX, CX
CALL    runtime.makeslice(SB)
// ... as same as before

func makeslice(et *_type, len, cap int) unsafe.Pointer {
    // ...
	return mallocgc(mem, et, true)
}
```

这里我们会发现，原先的 mallocgc 变成了 makeslice 调用。而 makeslice 的实现中，已经强制设置 `needzero = true` 。也就是说，第二种写法，势必会让整段内存被调用一次 `memclrNoHeapPointers`。但实际上，从代码的语义上来说，我们依然确保了 buf 一定会被整段 data 覆写，所以事实上这里的 `memclrNoHeapPointers` 操作是浪费的。

虽然这部分差异看似很小，但在实际项目中，尤其是那种 RPC 反序列化密集的场景里，众多字段都通过大量 `make and copy` 的方式生成，而这些代码常常因 make 和 copy 代码之间插入了其他代码导致没被编译优化，所以会出现在 `memclr` 之后紧接着 `memmove`。因为字段众多，所以这细碎的小开销累加起来非常夸张。

### 重新思考 Slice

无论是编程陷阱还是性能问题，我们都可以看到在使用 Slice 的时候，我们需要时刻关注底层内存的状态。但 Go 在语法上却又将底层内存给隐藏了起来。

真实世界对一段连续内存的创建，拷贝，操作需求多种多样，但在 Go 中表达能力却非常有限。Go 试图用统一简洁的 slice 语法把这些需求都包含在内，但同时，用户却又不得不因为元素类型不同而需要思考不同的操作方法。甚至在 Go 1.21 引入 clear 之前，对一个引用类型的 slice 置零我们还需要手动循环遍历 `for i := range slice { slice[i] = nil }` 。

虽然 Slice 的语法级实现提供了极大的便利性，但是这种便利性不应是牺牲了基本的安全性为代价的。何况某些基本操作如果有且仅能用花哨易错的语法实现，那么不仅没有安全性，也丝毫看不到任何便利性。

实际上 Go 已经在改变这种单纯依靠语法实现所有内存操作的思想了。Go 1.21 引入了 slices 标准库来操作 slice 结构。例如上面删除指针元素的问题就可以使用 slices.Delete 函数来替代繁杂且易错的语法操作(虽然 1.21 版本这个函数实现意外的居然没有修复内存泄漏的问题，但[新的修复已经 merged](https://go-review.googlesource.com/c/go/+/541477) )。

未来我们或许会看到，在一些稳定性优先的公司里，会更推崇使用标准库来操作 slice，让 slice 类型本身回归到一个不需要了解底层实现原理和各路花哨用法的简单数据类型。
