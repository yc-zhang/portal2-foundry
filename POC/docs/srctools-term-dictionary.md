# 用 srctools 制作 Portal 2 关卡

**适用环境**　Python 3.12、srctools 2.7.0、Portal 2 与 Portal 2 Authoring Tools。下文从一条关卡需求走到可试玩的 BSP。可以直接用 Python 制图，全程无需准备 `chamber.json`。[依赖版本](../requirements.txt) · [上游 VMF API](https://srctools.readthedocs.io/en/stable/modules/vmf.html)

**供 LLM 检索**　随附的 JSON 索引收录 26 个制图操作。按 `intent` 查想做的事，按 `scope` 查操作写到哪里，再读 `api`、`parameters`、`returns`、`usage` 和 `verify`。参数记录类型、传参方式、是否必填及 Python 默认值。例如搜索“制作密封房间外壳”，能查到六块墙的返回类型，以及把墙加入世界的下一步。[制图 API 元数据](srctools-authoring-api.json)

## 从需求选择操作

以“玩家向前走，靠近隔墙后一秒，滑门打开并保持开启”为例。先把可观察的行为写清楚，再选实现。这样 LLM 既知道要生成哪些对象，也知道试玩时应该看到什么。

| 需求 | 选择与输入 | srctools 操作 | 如何验收 |
|---|---|---|---|
| 有一个可行走的房间 | 给出室内净空、墙厚和内侧材质 | `make_hollow` → `add_brushes` | 玩家在房内出生，VBSP 生成 PRT，房间无 leak |
| 一堵隔墙，中间留门洞 | 门洞宽、高与墙厚；把洞口两侧和上方各做一块 | `make_prism` → `add_brush` | 门关闭时挡住通道，打开后玩家有净空通过 |
| 门沿墙滑动 | 选刷体实体，指定门板、移动方向、速度、开启后等待时间 | `create_ent` → `entity.solids.append` | 门板有碰撞，开启方向和位移正确 |
| 玩家靠近才开门 | 在门前放触发体，选玩家触碰事件，连至门的开启输入 | `Output` → `zone.add_out` | 出生时门关闭，走入区域一秒后开门 |
| 看得见房间和门 | 给每侧放灯并指定颜色、亮度和衰减 | `create_ent` → VRAD 烘焙 | 两侧能看清门框、门板和通道 |

资源选择发生在确定用途之后。几何需要材质路径；点实体或刷体实体需要 Portal 2 支持的 `classname` 和属性；整套预制机关需要实例 VMF 路径、朝向、参数及公开端口。查到的值填入下述 API。实体类、材质名、模板路径是三种不同的输入。[项目资源查找说明](resource-dictionary.md)

## 关卡对象与数据类型

| 术语 / Python 入口 | 类型、单位或归属 | 能控制什么 |
|---|---|---|
| 地图 `VMF()` | 一个地图对象 | 保存世界、实体集合、编辑器信息和数字 ID 分配器。可新建、读入、查询、修改、导出。 |
| 世界 `vmf.spawn` | 特殊的 `Entity`，类名为 `worldspawn` | 通过键值设置整图属性，例如 `vmf.spawn["skyname"]`。静态封闭几何属于这个世界。 |
| 位置 `Vec(x, y, z)` | 世界坐标，单位为 Hammer unit（HU），Z 向上 | 用于点位、边界角、位移。两角限定空间范围，单个点只标记位置。 |
| 朝向 `angles` | pitch、yaw、roll，单位为度 | 设置玩家或机关朝向。门的平移方向由该实体的 `movedir` 指定。 |
| 刷体 `Solid` | 一个凸实体，由多个 `Side` 包围 | 墙和地板挂在世界上；门板、触发范围挂在实体的 `solids` 上。一个刷体只挂在一个父对象下。 |
| 面 `Side` | 定界平面由三个不共线的点定义，点序决定朝向 | 逐面设置材质、贴图坐标和光照采样；多个平面必须共同围成有体积的凸体。凹形物体分成多个凸块。 |
| 实体 `Entity` | 类名、键值属性、可选刷体、事件输出 | 表达出生点、灯、模型、移动机关、逻辑、触发区。点实体可只用位置，刷体实体需要几何来定义形状或作用范围。 |
| 键值 `ent[key]` | VMF 把值写作字符串；API 可接受数值、布尔值、`Vec` 等 | `classname` 选择行为，`targetname` 给 I/O 引用，`origin` 设置位置。其余键须按该实体的定义填写。 |
| 对象编号 `obj.id` | 库按对象类别分配的整数 | 用在面引用、对象与编辑器组之间。游戏 I/O 通常按实体的 `targetname` 寻址；多个实体可以同名，需要单目标时应检查唯一性。 |
| 事件线 `Output` | 属于发事件的实体，保存在 `entity.outputs` | 描述哪个事件给哪个目标发送哪个输入，以及参数、延迟和触发次数。 |
| 实例 `func_instance` | 指向另一份 VMF 的实体 | 用 `file` 选模板，用 `origin`、`angles` 放置，用 `ent.fixup["$变量"]` 传模板声明的参数。VBSP 展开实例。 |

### 几何、表面和复用

| 想做什么 | API 与关键元数据 | 使用条件 |
|---|---|---|
| 做一个盒体 | `vmf.make_prism(p1, p2, mat=...)` 返回 `PrismFace`，含 `solid` 及六个具名面 | 每一轴都要有非零跨度。用 `.top` 取 +Z 面、`.west` 取 −X 面。设完材质再加入相应父对象。 |
| 做整间房 | `make_hollow(p1, p2, thick=16, mat=..., inner_mat=...)` 返回六个 `Solid` | 两角定义**室内净空**，墙厚向外增加。内外材质可分别指定。要给外墙开洞，应拆分该墙并保证整体对虚空密封。 |
| 逐面贴材质 | `side.mat` 取相对 `materials/` 的材质名，通常省略 `.vmt` | 白砖可只贴内侧。VMT 定义材质和着色参数，可以引用 VTF 图像。能否开传送门还要看实际材质、表面范围和阻挡。 |
| 对齐瓷砖、调阴影 | `side.uaxis`、`side.vaxis` 含方向、偏移和比例；`side.lightmap` 为每个光照采样格覆盖的 HU | 贴图接缝查 UV，阴影分辨率查 lightmap。调小 lightmap 会增加烘焙数据。 |
| 复制或旋转结构 | `solid.copy()` 取得副本，`solid.localise(origin, angles)` 旋转并平移，`get_bbox()` 返回两角 | 先复制再变换可保留原件。若贴花通过面 ID 引用旧面，复制时用 `side_mapping` 取新旧 ID 对应关系。 |
| 做起伏地面 | `Side.disp_power`、`DispVertex` 表达位移面的细分和顶点 | 在合适的四边形面上定义位移网格，另用普通世界刷体密封房间。 |
| 放投影标识 | `make_overlay(vmf, normal, origin, uax, vax, material, surfaces)` 返回贴花实体 | 该助手适合轴对齐表面。`surfaces` 传目标面对象；两个切向量的方向和长度决定贴花的朝向与跨度。 |

### 实体属性与事件

`vmf.create_ent(classname, **keys)` 创建实体并注册到地图。类名、键值和事件名可以写进 VMF，游戏是否执行相应行为取决于 Portal 2 的实现。选择新机关时，从游戏的 FGD 查类名、继承属性和 I/O 类型；从已有实例核对原点、朝向、使用的模型与内部连线。对设置了特定名字的实体，可用 `vmf.by_target[name]` 检查匹配数，用 `vmf.by_class[classname]` 检查同类对象。

| `Output` 构造参数 | 类型 / 默认 | 怎样选择 |
|---|---|---|
| `out` | 必填，事件名 | 由源实体发出，例如触发区的 `OnStartTouch`。 |
| `targ` | 必填，实体对象或目标名 | 传对象时库取它的 `targetname`。单目标示例先给门命名，再传门对象。 |
| `inp` | 必填，输入名 | 必须是目标类支持的动作，例如门接受 `Open`。 |
| `param` | 默认空字符串 | 需要参数的输入按其声明传值，例如数值或实体名。 |
| `delay` | 秒，默认 `0.0` | 延迟发送命令。若语义是“持续站满一秒”，还要处理提前离开的情况。 |
| `times`、`only_once` | 默认 `-1`、`False` | `-1` 可重复，`only_once=True` 把次数设为 1。源实体自身的生命周期也会限制事件，例如 `trigger_once`。 |

## 可运行示例：靠近后打开的滑门

先在项目 `POC` 目录准备环境。后续 PowerShell 命令都从该目录运行。示例在当前目录写出 `manual_gate.vmf`，重复执行会更新同名文件。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

把下面的 Python 保存为 `make_manual_gate.py`。出生点位于西侧，面向 +X。触发区在门前，门打开时沿 +Y 滑入侧墙。这里的材质和类名给出一组可复现的选择。

```python
from pathlib import Path

from srctools import Vec
from srctools.vmf import Output, VMF

vmf = VMF()
vmf.spawn["skyname"] = "sky_black_nofog"
panel = "metal/black_floor_metal_001b"
tile = "tile/white_floor_tile002a"

# 给出室内净空的两个角。六块外墙沿净空向外加厚。
walls = vmf.make_hollow(Vec(-256, -160, 0), Vec(256, 160, 160),
                        thick=16, inner_mat=tile)
vmf.add_brushes(walls)

# 隔墙位于 x=64..80，中间留出宽 96、高 112 的通道。
for y1, z1, y2, z2 in [(-160, 0, -48, 160), (48, 0, 160, 160),
                       (-48, 112, 48, 160)]:
    slab = vmf.make_prism(Vec(64, y1, z1), Vec(80, y2, z2), mat=panel)
    vmf.add_brush(slab.solid)

vmf.create_ent("info_player_start", origin=Vec(-192, 0, 8), angles="0 0 0")
for x in (-96, 168):
    vmf.create_ent("light", origin=Vec(x, 0, 128), _light="255 245 225 350",
                   _quadratic_attn="1", _linear_attn="0", _constant_attn="0")

# 门板沿 +Y 滑入隔墙，wait=-1 使它在打开后保持开启。
gate = vmf.create_ent("func_door", targetname="exit_gate", movedir="0 90 0",
                      speed="128", lip="0", wait="-1", spawnflags="0")
gate.solids.append(vmf.make_prism(Vec(66, -48, 0), Vec(78, 48, 112), mat=tile).solid)

zone = vmf.create_ent("trigger_once", targetname="approach_gate", spawnflags="1")
zone.solids.append(vmf.make_prism(Vec(-32, -160, 0), Vec(0, 160, 112),
                                  mat="tools/toolstrigger").solid)
zone.add_out(Output("OnStartTouch", gate, "Open", delay=1.0, only_once=True))

out = Path("manual_gate.vmf")
with out.open("w", encoding="ascii") as stream:
    vmf.export(stream)
check = VMF.parse(str(out))
assert len(check.brushes) == 9
assert len(check.by_target["exit_gate"]) == 1
wire, = next(iter(check.by_target["approach_gate"])).outputs
assert (wire.output, wire.target, wire.input, wire.delay, wire.times) == (
    "OnStartTouch", "exit_gate", "Open", 1.0, 1)
print(out.resolve())
```

## 从 VMF 编译到游戏验收

在 Steam 安装 Portal 2 Authoring Tools。下列命令先生成并回读 VMF，再调用项目的构建脚本。脚本默认使用本机标准 Steam 路径，自定义 Steam 库可传 `-GameRoot`。[构建脚本](../build-map.ps1) · [Windows 构建说明](portal2-map-build.md)

```powershell
.\.venv\Scripts\python.exe make_manual_gate.py
if ($LASTEXITCODE -ne 0) { throw 'VMF 生成或回读失败' }
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\build-map.ps1 -Vmf .\manual_gate.vmf
```

| 阶段与执行者 | 产物 / 通过条件 | 遇到问题先查什么 |
|---|---|---|
| srctools 生成、回读 VMF | 示例断言九块世界几何，找到门并核对事件、目标、动作、延迟及次数 | 空文件或数量不对时检查导出路径、刷体的父对象和实体名称 |
| Valve VBSP | 生成 BSP、PRT，房间无泄漏；实例在此展开 | 出现 `.lin` 时在 Hammer 加载 pointfile，沿线找外壳缝隙或室外实体 |
| Valve VVIS / VRAD | VVIS 将区域可见性写回 BSP，VRAD 烘焙并写入光照 | VVIS 查 PRT；画面发黑、过曝或阴影异常时查灯的位置、衰减、面朝向和 VRAD 日志 |
| srctools / BSPZIP | `BSP` 读取成品，`PackList` 收集资源依赖，项目打包脚本核对随图资源 | 查 SDK 构建目录中的 `.dependencies.json`；动态脚本引用的资源可显式加入地图的资产目录 |
| Portal 2 实机 | 地图能加载，玩家能行走，经过触发区后一秒门滑开，通过后门保持打开 | 门不动时按源事件、目标名、输入名和刷体归属逐项检查；贴图缺失时核对材质路径与内嵌资源 |

要独立检查编译器保留了什么，可在构建完成后运行以下 Python。点光源可能已经烘焙进地图，按运行时需要保留的实体检查结果。

```python
from srctools.bsp import BSP

level = BSP("manual_gate.bsp").ents
gate, = level.by_target["exit_gate"]
zone, = level.by_target["approach_gate"]
wire, = zone.outputs
assert (gate["classname"], zone["classname"]) == ("func_door", "trigger_once")
assert (wire.output, wire.target, wire.input, wire.delay, wire.times) == (
    "OnStartTouch", "exit_gate", "Open", 1.0, 1)
```

试玩时将生成的 `manual_gate.bsp` 复制到游戏的 `portal2/maps/`，或在构建命令末尾加 `-Install` 安装同名 BSP。打开 Portal 2 开发者控制台，执行 `map manual_gate`。先停在出生点确认门关闭，然后向前穿过触发区，等门打开并走过门洞，再返回检查门仍开启。结构回读、编译结果、玩家实际观察应分别记录。

## 文件格式附录：VMF 的顶层区块

**“顶层”取决于正在读哪个文件。** 在项目的 `chamber.json` 中，`materials`、`world`、`components`、`connections` 都是一级字段。导出到 VMF 后，材质路径落在 `side.material` 或相应实体属性上，放置好的组件落在 `entity`，输出线落在源实体的 `connections` 子块中。下面列的是 **srctools 2.7.0 导出器可写出的九种 VMF 根区块**；它们的数量与可以制作的机关种类无关。

| VMF 根区块 | 对应的对象或属性 | 内容与用途 |
|---|---|---|
| `world` | `vmf.spawn`、`vmf.brushes` | 一个世界实体，包含全局属性与静态几何，几何继续分为 `solid → side`。 |
| `entity` | `vmf.create_ent(...)` | 每个实体一个区块，可重复。键值、可选的 `solid`、`connections` 和编辑状态属于该实体。 |
| `versioninfo` | `map_ver`、`format_ver`、`hammer_ver`、`hammer_build`、`is_prefab` | 地图修订、格式和编辑器版本；`export(inc_version=False)` 可保留当前修订号。 |
| `visgroups` | `vmf.create_visgroup(...)`、对象的 `visgroup_ids` | 定义编辑器显示分组，以组 ID 记录成员。 |
| `viewsettings` | `snap_grid`、`grid_spacing`、`show_grid` 等 | 保存 Hammer 的网格和吸附偏好。 |
| `cameras` | `Camera(vmf, pos, targ)`、`active_cam` | 保存编辑器观察位置和注视点。游戏镜头由游戏实体控制。 |
| `cordons` | `Cordon(...)`、`cordon_enabled` | 保存 Hammer 局部编译范围和启用状态。 |
| `hidden` | 实体或刷体的 `hidden` 标记 | 顶层可包住隐藏实体，几何所属的区块内部也可包住隐藏刷体。 |
| `quickhide` | `quickhide_count` | 记录快速隐藏计数，计数大于零时导出；具体隐藏对象由 `hidden` 包装。 |
