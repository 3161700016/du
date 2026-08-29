# 候补插件说明 · 2026-08-27

> ✅ **2026-08-29 固化完成**：两件插件已装入 agent preset「渡」（du）——
> C:\Users\31617\.dsh\.agent-presets\du\plugins\{du-clock.mjs, du-archive.mjs}，
> mount-validate 通过。新会话选 du preset 即自动挂载，本目录转为历史档案
> （安装条件与教训记录仍具参考价值；du-archive 装机时修正了 writeText content 参数类型）。

两份文件为「时间锚点」与「会话流归档器」的设计定稿。因当日 cordis_define 工具在父会话持续损坏，未能当场安装。

## 安装条件

**必须在一个全新的（或未损坏的）主会话中执行**。原因有二，均为当日实测教训：

1. 父会话历史回放导致 cordis_define 参数整体包裹损坏——换模型无效、重启进程无效，唯新会话根治；
2. **动态插件注册表按会话上下文隔离**：子代理中定义/运行的插件对父会话完全不可见（tsty-1 实证）。因此不能借子代理之手替主会话安装。

## 安装方式

新会话对我说：「读取 项目/渡的大脑/候补插件/ 下两个 .host.js 并分别作为 code.host 定义激活，duclock 用 kind=new idPrefix=duclock；归档器建议并入 du-sync 或单独建包。」我即可自动完成。

## 已知修正记录

- duclock v0.1.1：原稿使用 ctx.inject(...) 调用式注入——动态沙箱不暴露该方法（报错原文留下过证据）。修正为声明式字段 inject:['systemPrompt'] + 直接属性访问。此坑对未来任何需要服务依赖的动态插件通用。
