---
title: RPC 漫谈 - 历史变迁
date: 2021-03-27
categories: ["Tech"]
draft: true
---

## 什么是 RPC

## RPC 使用

为规范内部调用的规范，我们会期望在一个文件内定义我们的通信约定，例如以下 Protobuf 的定义：

```protobuf
service Greeter {
  rpc SayHello (HelloRequest) returns (HelloReply) {}
}

message HelloRequest {
  string name = 1;
}

message HelloReply {
  string message = 1;
}
```

根据该定义，我们虽然能够建立一个共识，但各方在实现该定义时，仍然很可能出现偏差，所以我们希望能够直接从定义文件中去自动生成一些类型以及接口：

```golang
type HelloRequest struct {
	Name string `protobuf:"bytes,1,opt,name=name,proto3" json:"name,omitempty"`
}

type HelloReply struct {
	Message string `protobuf:"bytes,1,opt,name=message,proto3" json:"message,omitempty"`
}

type GreeterServer interface {
	SayHello(context.Context, *HelloRequest) (*HelloReply, error)
}
```

利用这些已经编译好的自动生成代码，我们能够专注于业务逻辑，构建自己的服务：

```golang
// === server.go ===
type server struct {
	pb.UnimplementedGreeterServer
}
func (s *server) SayHello(ctx context.Context, in *pb.HelloRequest) (*pb.HelloReply, error) {
	return &pb.HelloReply{Message: "Hello " + in.GetName()}, nil
}

s := grpc.NewServer()
pb.RegisterGreeterServer(s, &server{})
if err := s.Serve(lis); err != nil {
	log.Fatalf("failed to serve: %v", err)
}

// === client.go ===
c := pb.NewGreeterClient(conn)
r, err := c.SayHello(ctx, &pb.HelloRequest{Name: name})
if err != nil {
	log.Fatalf("could not greet: %v", err)
}
```


