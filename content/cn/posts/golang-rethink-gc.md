---
title: 对 Go 语言的批判思考
date: 2024-03-30
categories: ["Tech"]
draft: true
---

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
