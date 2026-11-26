# Portal 2 Foundry

用 AI 制作原版《传送门 2》创意工坊地图的实验工作区。当前处于 POC 阶段，地图、生成器、构建说明和实验记录都在 [POC/](POC/README.md)。

## 从这里接手

| 想做什么 | 从哪里开始 |
|---|---|
| 玩已经实测的地图 | 把 [foundry_button.bsp](POC/foundry_button.bsp) 复制到 Steam 游戏目录的 `Portal 2/portal2/maps/`，进游戏执行 `map foundry_button`。要修改这间大房间，打开[对应的 VMF](POC/foundry_button.vmf)。 |
| 复现实验生成链路 | [chamber.json](POC/chamber.json) 描述另一间早期小房间。[生成器](POC/generate_vmf.py) 用 Python / srctools 导出 VMF，Valve 的 VBSP、VVIS 和 VRAD 再编译为 BSP。安装依赖和编译命令见[构建说明](POC/docs/portal2-map-build.md)。 |
| 理解已验证的结果 | [实验日志](POC/logs/2026-11-25.md) 记录了缺枪、方块模型缺失和灯光过曝的定位过程。[实机截图](POC/media/portals-and-button.jpg) 记录了双传送门、方块压住按钮和出口打开。 |

## 下次实验

目标是让 LLM 通过 Python / srctools 直接生成 VMF，由官方编译器构建，再进游戏试玩。Hammer 仅用于核对布局、组件位置和事件连线。下一步选一个带输入或输出的 BEE2 组件，核对它经过预编译后产生的实体、I/O 与资源依赖，再尝试移入最小样图。工坊订阅、在线结算与投票仍待验证。

## 工作目录与归档

从仓库根目录执行 `cd POC` 后即可使用构建说明中的相对路径。开发机需要另行安装原版 Portal 2 和 Authoring Tools。本机 Python 环境位于 `POC/.venv/`，换电脑可按 `POC/requirements.txt` 重建。

本机的 `POC/local-archive/` 保存迁移清单、旧版分享图、原始 ZIP、历史对话和编译日志。该目录只作本地归档；换电脑如需这些原始记录，请单独复制。仓库中的实验日志、源文件、可玩地图与实测截图可直接随 Git 获取。
