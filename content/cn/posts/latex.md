---
title: 一份其实好吃的 LaTeX 入门餐
date: 2018-05-13
categories: ['技术']
draft: false
aliases: [
    "/编程/latex/",
]
---

最近在使用 LaTeX 写作，发现虽然这个「软件」使用简单，设计简约，但使用起来却并不是非常的容易，加上其生态非常芜杂，各种宏包和发行版层出不穷，中文世界鲜有文章系统地去讲他们之间的关系。这篇文章不会去介绍其基本用法，而是以一个更为宏观的角度，旨在厘清 TeX 排版系统的来龙去脉，以及其生态圈中各个项目的作用与关系。或有纰漏，还望雅正。

标题致敬 Liam Huang 老师很流行的一篇文章 [《一份其实很短的 LaTeX 入门文档》](https://liam0205.me/2014/09/08/latex-introduction/#%E4%BC%98%E9%9B%85%E7%9A%84_LaTeX) 。

## 什么是 Tex

TeX 是高德纳教授在70年代末编写 ***The Art of Computer Programming*** 时，对当时的计算机排版技术感到无法忍受，因而决定自己开发一个高质量的计算机排版系统 TeX 。

TeX 的版本号有别于当下流行的 `x.x.x`，而是以圆周率 π 的形式。当前的版本号是 `3.14159265` ，所以下一个版本是 `3.141592653` 。最终无限收敛到 π ，代表了 TeX 不断追求完美的理想。而事实上 TeX 也的确堪称「完美」，高德纳甚至曾悬赏任何发现 Bug 的人，每一个漏洞的奖励金额从2.56美元开始，之后每发现一个 Bug 都会翻倍，直至327.68美元封顶。

TeX 的输出文件被称为 DVI(Device Independent) 文件，DVI 可以作为一种界面描述的中间格式，通过它可以再进而转换成 PDF 格式。

为了区分概念，我们应当将高德纳写的 TeX 软件分为 TeX 语法 和 TeX 编译器。虽然高德纳自己写了一个 TeX 编译器，但其它人依旧可以在不同平台自己编程实现 TeX 语法的编译器。为了保持语法的稳定，TeX 有一组严格的测试文件，如果测试文件文件的输出结果不同于预定的结果，那么这个排版系统就不能够被称为「TeX」。这些不同的 TeX 编译器我们都称之为 「 TeX 引擎」。

TeX 目前(2018年)有如下几个编译引擎:

1. TeX : 高德纳最早开发的官方实现，只能编译成DVI格式。
2. pdfTeX : 支持直接编译成 PDF 格式。
3. XeTeX : 支持 Unicode 编码和直接访问操作系统字体。
4. LuaTeX : Lua 实现的 TeX 编译器。

虽然 Tex 出于向下兼容考虑要求了所有编译器都需要能够编译历史上所有符合标准的 Tex 文件，但并不意味着它不能增加新的功能。TeX 作为一门「宏语言」，能够使用宏定义出新的语法，甚至能够覆盖原先的语法。要理解这一点必须要先理解什么是「宏编程」。

## 什么是宏编程

要理解为什么宏如此强大，甚至强大到可以自己定义语法，我们可以来看一个例子 。

我们假设我们写了一门新的语言 「D」，它的语法如下 :

```c
# compare:
"a" == "b" # false
"a" == "a" # true

# do .. while
do {
} while(bool)

# io
print("...")

# macro
define TYPE_NAME(params, ...) ......
```

乍一看宏(macro) 的用法非常像函数，但和函数有着本质区别的是，宏是一个编译时的字符串替换，而函数是运行时的一段可执行代码。例如:

```c
define PLUS(a, b) a + b

int c = PLUS(1, 2)
```

这段代码在预处理的时候就会被替换成 

```c
int c = 1 + 2
```

我们可以发现这门语言中并不存在 if 语法，也不存在循环，但是通过宏我们能够为他定义出 if 和 for 语法。例如:

```c
define IF(condition, instruction) do { instruction } while (condition)

define FOR(count, instruction) int __for_count__ = 0; do { __for_count__++ ; instruction } while ( __for_count__ < count )
```

利用宏我们完全可以扩展出一门新的语法结构，我们命名为 「D+」。「D+」严格意义上并不能算一个新的语言，只是称之为一个宏集。并且由于其只是在编译时做了字符串替换，所以依旧是可以用D的编译器编译的。

回到主题上来，TeX 就像是这里的 D 语言，LaTeX 就是「D+」宏集。LaTeX 本身也都是用 TeX 编译器来实现编译的。

## 宏集和宏包

宏集和宏包其实是一堆 TeX 指令集合，宏集以 `.cls` 结尾，宏包以 `.sty` 结尾。宏集需要以 `\documentclass{...}` 来加载，且一个文档一般只使用一个documentclass。而宏包是以`\usepackage{...}`，无使用限制。

正式因为这个区别，所以一般宏集是一个完整的文档格式模板(也称之为「格式format」)，比如武汉大学的论文模板 `\documentclass{whucls}`。而宏集比较灵活，例如你临时需要一些宏包来定义一些特殊字体就可以按需加载宏包。

## 什么是 LaTeX

LaTeX 就是一种 TeX 宏集，它内嵌了许多常用文档格式，例如 : article、report、book、letter等。使用方式很简单，在 .tex 文件最开头加上 `\documentclass{article}` 即可。

LaTeX 内建了许多新的指令，只需要对相应的段落内容予以其在文档中的「类型」即可使 LaTeX 自动为你排版。例如以下这段文档:

```tex
\documentclass{article}
    \title{TITLE XXXXXX}
    \author{XXX}
    \date{\today}

    \begin{document}
    \clearpage\maketitle

    ....

    \section{XXXXX}
    ...

    \section{XXXXX}
        \subsection{XXX}
        ...

        \subsection{XXX}

    \section{XXXXX}
    ...

    \end{document}
```

这里的 title、section、subsection 都是预先定义的 LaTeX 宏，在宏中已经定义好了样式。当然如果你需要在 LaTeX 宏集的基础上做自己的修改，你也可以基于 LaTeX 宏集做一个单独的宏包。

## 为什么要使用 LaTeX

我把上面这种写作方式称之为「面向对象写作」。这种设计的优点在于其逻辑完全与实际需求场景相吻合。例如我们在写论文的时候都会拿到一个论文格式规范清单，上面详细规定了什么样的内容需要以什么样的样式来书写。而我们一般使用 Word 时候的方式却是针对所有内容单独一点点地去设立样式。(当然目前 Word 也开始支持这种面向对象赋予格式，但远远没有 LaTeX 那么彻底。)

打个比方，LaTeX 相当于带 `class` 的 CSS , 而 Word 是裸写`<div style="">`。LaTeX 使得作者可以全身心地投入到写作之中，而无需去关心样式，当需要调整排版样式的时候，也仅仅只需修改类型的样式而非文档本身即可。

## 中文支持

关于中文支持网上说法非常过时和混乱。这里做一个统一的说明。

历史上中文支持方案有 CCT、CJK、xeCJK 三种。CCT 目前已经过时，推荐使用 xeCJK 。

但支持中文并不意味着就完成了中文化，我们还需要考虑到中文文档在不同文档类型、文本内容类型中的字体、字号等排版上的设计，同时还有不同系统字体系统不同的困扰。另外由于 LaTeX 在上述需求中完全是以英文视角在进行设计，所以回到中文世界我们需要一套完全不同的宏集合以支持完整的中文化需求。

目前中文世界有一个流行的宏集叫做 `CTeX`。与 LaTeX 一样，CTeX 也支持 `ctexart`(article)、`ctexrep`(report)、`ctexbook`(book)等文档类。同样使用如下方式引入:

```tex
\documentclass{ctexart}
```

严格来讲，CTeX 是一个内含多种程序和文件的软件包套装。但上文讲的 CTeX 指的仅仅其中的宏集/宏包部分。网络上针对 CTeX 的批评很多时候是针对其套装里的GUI和其它软件而言，其实和它的宏集没什么关系。

CTeX 宏集帮助我们处理好了各种中文排版问题，和操作系统问题，所以一般都推荐直接使用它，不需要额外的任何定义即可实现中文支持。

```tex
\documentclass[12pt, UTF8]{ctexart}

  \begin{document}
  \end{document}
```

虽然理论上当你使用 CTeX 写作时，应当称`该文档使用 CTeX 完成`，但事实上极少会有人这么去说，包括许多说自己在用 TeX 写作的人其实用的也都是 LaTeX 。这种语言上的错误用法大多是因为这个生态其实已经够复杂了，没必要再把人与人之间的交流弄复杂。所以大家统一称这个生态为 LaTeX 。

## 编辑器

非计算机专业的人往往会出于一些软件使用习惯，将编译器和编辑器等同来看。相当一部分时候编译器也的确顺带着编译器一起被整合成一个软件。但其实即使是系统自带的文本查看工具也可以称之为编辑器。网上主流的TeX编辑器有: TeX Live 、MiKTeX、CTeX 套件。为方便用户使用，这些软件在安装过程中按自动安装上各个主流的 TeX 编译器版本。当然你也可以使用任意其它编辑器诸如 VS Code 、Atom 、Vim ，使用他们的插件或者手动编译即可。

## 我的 LaTeX 工作方式

我个人比较喜欢的是 xelatex 编译器 + VS Code 的编写方式。

选择 xelatex  是因为它使用 unicode 编码直接支持中文。而 VS Code 的 LaTeX 插件支持每次保存文件自动编译，同时 Mac 的PDF查看程序每当文件发生变化的时候会自动刷新，从而实现了即写即看、所见即所得的写作体验。

我长期使用 Markdown 方式写作，即便是用 LaTeX 我们依然可以维持这个方式，方式很简单，markdown 的文档结构是完全能够被映射到 latex 的文档结构上的，利用这个方式可以写一个 parser 就能够实现这种批量转换了。我之后可能会考虑写一个工具来做这个事情。

- Mac 可以使用 MacTeX : [https://www.tug.org/mactex/](https://www.tug.org/mactex/)
- VS Code LaTex Workshop 插件地址 : [https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)
- VS Code 使用 xelatex 自动编译配置文件 : [https://github.com/joway/latex-template-zh/blob/master/.vscode/settings.json](https://github.com/joway/latex-template-zh/blob/master/.vscode/settings.json)

## 一些 LaTeX 模板

- [latex-template-zh](https://github.com/joway/latex-template-zh) : 我用来写中文文章的模板库，在 ctex 基础上加了一些行间距之类的，使其更加适用于互联网文章的排版。
- [latex-resume-template](https://github.com/joway/resume) : 我的 LaTeX 简历模板。