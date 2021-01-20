---
title: Golang for-range 内部实现
date: 2021-01-20
categories: ["Tech"]
draft: false
---

最近在写一个编解码的功能时发现使用 Golang `for-range` 会存在很大的性能问题。

假设我们现在有一个 `Data` 类型表示一个数据包，我们从网络中获取到了 `[1024]Data` 个数据包，此时我们需要对其进行遍历操作。一般我们会使用 for-i++ 或者 for-range 两种方式遍历，如下代码：

```go
type Data [256]byte

func BenchmarkForStruct(b *testing.B) {
	var items [1024]Data
	var result Data
	for i := 0; i < b.N; i++ {
		for k := 0; k < len(items); k++ {
			result = items[k]
		}
	}
	_ = result
}

func BenchmarkRangeStruct(b *testing.B) {
	var items [1024]Data
	var result Data
	for i := 0; i < b.N; i++ {
		for _, item := range items {
			result = item
		}
	}
	_ = result
}
```

输出结果：

```
BenchmarkForStruct-8     	 1697805	       652 ns/op
BenchmarkRangeStruct-8   	   60556	     19837 ns/op
```

可以看到通过索引来遍历的方式要比直接使用 for-range 快了近 30 倍。

索引遍历就是单纯地去访问数组的每个元素。而对于 for-range 循环，Golang 会根据迭代对象类型，已经 range 前的参数，对其进行不同形式的展开。对于以下 range 代码：

```go
for i, elem := range a {}
```

编译器会将其转换成如下形式（伪代码）, [range.go](https://github.com/golang/go/blob/master/src/cmd/compile/internal/gc/range.go#L216)：

```golang
ha := a // 值拷贝
hn := len(ha) // 提前保存长度
hv1 := 0 // 当前遍历索引值
v1 := hv1 // 保存当前索引
v2 := nil // 保存当前值
for ; hv1 < hn; hv1++ {
    v1, v2 = hv1, ha[hv1] // 值拷贝
    ...
}
```

这里有几点需要额外注意：
1. 编译器提前保存了元素长度，所以运行过程中即便长度变化，也不会影响循环次数
2. `ha := a` 这一步会进行一次值拷贝，这里部分情况下可能会存在性能问题 （如上面的 [256]byte 类型，每次拷贝都有很大内存开销）
3. `v1, v2 = hv1, ha[hv1]` 会对数组元素进行一次值拷贝
4. v1, v2 预先创建，地址不会改变，对应到原始代码就是 `for i, elem := range a {}` 中的 `i, elem` 在每次循环时，都是同一个变量。

由此可以发现，当被迭代对象的元素为拷贝开销较大的类型时，使用 for-range 循环会存在很大的性能问题。此时更加建议使用标准 for 循环。
