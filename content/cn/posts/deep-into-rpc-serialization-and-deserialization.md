---
title: RPC 漫谈：序列化问题
date: 2021-04-07
categories: ["Tech"]
draft: true
---

# 何为序列

我们都知道 `程序 = 数据结构 + 算法`，但程序要能够真正被使用，还需要输入与输出的数据。对于计算机而言，一切数据皆为二进制序列，但程序的编写者需要以人类可控的形式处理这些二进制数据，于是就发明了编程语言，将二进制的数据解码成了一块块独立的内存空间，并对其定义不同的类型与组织结构，例如编程语言中常见 struct/class 概念：

```go
type User struct {
	Name  string
	Email string
}
```

在上面的 `User struct` 中，Name 和 Email 分别表示两块独立的内存空间（数据）。在分布式系统中，我们常会希望两个进程能够互相交换内存里的某个 User 对象，但计算机只能认识二进制流，所以我们需要现将该 User 对象中不同的内存空间，编码成一段二进制流表示，此即为「序列化」。除了交换数据本身，为了让接受方能够将二进制流还原为其程序内的对象，我们还需要交换对这个数据的描述。

所谓的序列化和反序列化，就是将同一份数据，在人的视角和机器的视角之间相互转换。

# IDL 定义

为了传递数据描述信息，同时也为了多人协作的规范，我们一般会将描述信息定义在一个由 IDL(Interface Description Languages) 编写的定义文件中，例如下面这个 Protobuf 的 IDL 定义：

```protobuf
message User {
  string name = 1;
  string email = 2;
}
```

# Stub 代码生成

无论使用什么样的序列化方法，最终的目的是要变成程序中里的一个对象，所以一定会存在一段代码需要去实现将一段内存空间与程序内部表示（如 struct/class）相绑定的过程：

![](../../images/rpc/rpc-overview.png)

Stub 代码分为两块：
1. 类型结构体生成（即目标语言的 Struct[Golang]/Class[Java] ）
2. 序列化/反序列化代码生成（将二进制流与语言内部结构体相转换）

Stub 代码既可以自己手写，也可以通过序列化协议提供的编译器自动生成。如果你的调用方与被调用方都是同一种语言，且未来一定能够保证都是同一种语言，这种情况也会选择直接用目标语言去写 IDL 定义，跳过了编译的步骤，例如 Thrift 里的 [drift](https://github.com/airlift/drift) 项目就是利用 Java 直接去写定义文件：

```java
@ThriftStruct
public class User
{
    private final String name;
    private final String email;

    @ThriftConstructor
    public User(String name, String email)
    {
        this.name = name;
        this.email = email;
    }

    @ThriftField(1)
    public String getName()
    {
        return name;
    }

    @ThriftField(2)
    public String getEmail()
    {
        return email;
    }
}
```

但目前流行的序列化协议多是跨语言的，所以都提供了编译器，从 IDL 定义文件中生成目标语言的 stub 代码。但如果社区并没有你要的语言的编译器，你将会很难使用该序列化协议。

# 序列化方法

序列化的难点在于，如何在静态类型语言中，使用动态类型。

例如我们 Stub 部分代码根据读取的二进制数据中的类型描述字段知道了该数据对应着 User 的 struct，此时需要将二进制数据解析并赋值到该 struct 对象中，伪代码如下：

```golang
data = [...] //binary bytes
/* data format
+--------+--------+--------+--------+...+
message  |field id|field value          |
+--------+--------+--------+--------+...+
*/

// deserialization
switch [message] {
  case "user":
    obj := User{
      Name:  string([field1 value...])
      Email: string([field2 value...])
    }
}
```

这里的 `data format` 简单表示了我们二进制数据内的信息编码，前 8 bytes 表示 message name，9~16 bytes 代表 field id，后面不定长的 bytes 代表该 field 的数据。

上面的伪代码虽然看着简单，但是其实绝大部分序列化协议之间的核心区别却几乎都包含在了这段伪代码之中。我们一步步从代码实现的角度来看这里的奥秘。

## 1. Field Id 与 Field 的映射

首先我们需要将数据内的 field id 和程序 struct 中的 field 相对应。这里的 field id 既可以是字符串，也是可以 int，一般出于节约体积的角度，我们会选择用 int8 类型。

在 protobuf 中，会维护一个数组

## 2. 获取 Field 类型

先从代码实现角度来看存在的几个问题：
1. 如何将 field id 和 struct 里定义的 Field 联系在一起？
2. 如何知道 User struct 中有哪些 Field？
3. 如何知道不同 Field 对应什么类型？
4. 

## 使用反射

一个最直观的想法是使用反射构造动态类型。这也是 ProtoBuf 官方库的实现方式。

反射的原理是通过

## 编码格式

TLV

# 序列化的性能

我们经常谈到某某序列化协议的性能如何如何，这种说法其实并不严谨。虽然协议定义的一些细节能够对性能产生影响，但根本性影响序列化性能的往往还是该协议在某语言上的实现。




