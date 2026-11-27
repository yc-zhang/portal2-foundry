# 怎样查找 Portal 2 的材质和组件

字典统一放在 [dictionaries/](../dictionaries/)，文件名按用途命名。早期的总表把材料和组件一起导出，未记录两者之间的依赖。需要查具体组件的材质依赖时，看模型、实例和编译后的资源依赖报告。

| 字典 | 可以查到什么 |
|---|---|
| [materials.json](../dictionaries/materials.json) · [纯文本列表](../dictionaries/materials.txt) | 材质别名、VMF 材质路径、native 标记和来源。VPK 中的路径为 `materials/<键>.vmt`。 |
| [components.json](../dictionaries/components.json) | JSON 支持的 chamber_types，以及 Hammer 实体、SDK 实例和 Puzzle Maker 物品。 |
| [voices.json](../dictionaries/voices.json) | `recordings` 按游戏相对路径列出 `sound/vo/` 下的 WAV、MP3 录音及其来源。播放实体链接到组件定义和 I/O，工坊入场语音链接到 SDK 实例，BEE2 语音包链接到 `bee2.json` 的 `quote_packs`。 |
| [bee2.json](../dictionaries/bee2.json) | BEE2 官方包与物品 ID；按 native_editor_item 查与原版物品的对应关系，按 declarations 查哪个包定义或覆盖了该物品。 |
| [connections.json](../dictionaries/connections.json) | JSON 使用的 from、to、once，组件端口到 Source I/O 的映射，以及官方 FGD 中每个类直接声明的输入、输出和参数类型。查继承端口时沿 bases 查基类；同名声明分别保留来源。 |

路径相对于 Steam 的 `steamapps/common/Portal 2/`，实例路径相对于 `sdk_content/maps/`。字段 `connections` 在 VMF 中位于实体内部。例如小房间中的 `plate.pressed → gate.open` 表示 plate 发出 OnPressed 后，向 gate 发送 Open。高级 VMF 连线还支持参数、延迟及触发次数；当前 JSON 只开放端点和 once。

查原版录音时可搜索路径前缀，例如 `sound/vo/glados/`。索引涵盖基础游戏、数字编号 DLC、update 和 platform 中的 VPK 与散装文件。语言包目录、字幕文本和 VCD 场景内容另计。缺少基线记录的散装录音标为 `unverified`。BEE2 的 `quote_packs` 记录包清单中的角色、名称、配置文件标识和原始说明；例如 Nigel 的说明限定在 Aperture Tag 中使用。当前 chamber JSON 尚无可放置的旁白预设。

## Portal 2 VMF 顶层区块

每个文件包含用途、常见字段、当前生成器开放的控制项及两份 VMF 快照的实测结果。examples.count 只统计顶层出现次数。

| 字典 | 当前工程中的作用 |
|---|---|
| [world](../dictionaries/vmf/world.json) | worldspawn 和静态 brush；JSON 控制长方体及材质，天空盒固定。 |
| [entity](../dictionaries/vmf/entity.json) | 实体、属性和事件。小房间快照有 8 个顶层 entity，大房间有 17 个；生成器目前支持 9 种预设。 |
| [versioninfo](../dictionaries/vmf/versioninfo.json) | srctools 填写的版本元数据。 |
| [visgroups](../dictionaries/vmf/visgroups.json) | Hammer 可见性分组，两张图都导出了空块。 |
| [viewsettings](../dictionaries/vmf/viewsettings.json) | 编辑器网格与吸附；保留实际导出的标志与间距。 |
| [cameras](../dictionaries/vmf/cameras.json) | 编辑器视角；两份快照的 activecamera 都为 -1。 |
| [cordons](../dictionaries/vmf/cordons.json) | 局部编译边界；两份快照都关闭。 |
| [hidden](../dictionaries/vmf/hidden.json) | 隐藏实体的顶层包装，两份快照均未出现。 |
| [quickhide](../dictionaries/vmf/quickhide.json) | 快速隐藏计数，两份快照均未出现。 |

用地板按钮对照这四层：POC 描述用 `floor_button`，生成器创建 `prop_floor_button`。若要复用带安装框的白地板按钮，还可以放置 `instances/p2editor/floor_button_white_intact.vmf`。Puzzle Maker 里的 `ITEM_BUTTON_FLOOR` 则列有白底、黑底和不同按钮形状的实例。生成器当前只识别 `chamber_types` 中的名称。

材质索引枚举主游戏、数字编号 DLC、update 和 platform 中的 VPK 及散装 VMT。目录 `tile/`、`metal/`、`concrete/` 适合寻找墙地面，`signage/` 和 `overlays/` 可用于标识，`models/`、`vgui/` 和 `tools/` 服务于其他用途。可在 Hammer 的纹理浏览器输入材质路径查看缩略图。可开传送门性要结合实际表面的材质标记、尺寸和阻挡判断。

列表范围随安装变化。关卡私有 BSP 包和外部 BEE2 包库未扫描。若 BEE2 已经将文件导出到当前安装的受扫描目录，重新索引会收录相应定义；BEE2 的样式选择和预编译条件仍需另查包配置。

从 POC 目录运行以下命令可刷新字典：

```powershell
.\.venv\Scripts\python.exe index_resources.py 'C:\Program Files (x86)\Steam\steamapps\common\Portal 2'
```

## 查哪些组件能直接使用

[独立组件字典](../dictionaries/components.json) 的 `chamber_types` 是生成器能直接接受的类型。每项包含实体类、默认参数、可连接的端口和来源。以下是当前使用原版资源的配方：

| 放什么 | chamber.json 的 type |
|---|---|
| 出生点、双传送枪、点光源 | `spawn`、`portal_gun`、`light` |
| 普通方块、爱心方块（同伴方块） | `cube`、`companion_cube` |
| 地板按钮、升降门 | `floor_button`、`lift_door` |
| 终点触发区、工坊结束逻辑实例 | `finish_zone`、`workshop_finish` |

例如把 `{"id":"heart","type":"companion_cube","at":[-112,84,36]}` 放进 components 数组。原版使用 `prop_weighted_cube` 的 `CubeType=1`；模型为 `models/props/metal_box.mdl`。本机原版 VPK 和散装模型目录均未检出文件名含 cake 的 MDL，因此蛋糕未列为可用组件。

要找激光发射器、光桥、引力漏斗或炮塔，可以在组件字典的 `editor_items` 查 `ITEM_LASER_EMITTER_CENTER`、`ITEM_LIGHT_BRIDGE`、`ITEM_TBEAM`、`ITEM_TURRET`，查看其原版实例。接入生成器前仍需为相应物品实现放置和连线。`hammer_entities` 和 `instances` 提供更底层的声明与模板。

## native 的判定范围

BEE2 应用负责配置 Puzzle Maker、选择样式和预处理地图。独立维护的 BEE2-items 包库提供物品，也包含音乐、语音、标识和样式等资源。字典的 packages 枚举官方源码包，items 只枚举这些包在清单顶层及 Overrides 中声明的 Item。包数、物品 ID 数和样式声明数是三个不同的量。

例如 `ITEM_BUTTON_FLOOR` 与原版同名；BEE2 的 VALVE_BUTTONS 提供物品配置，其他样式包可覆盖实现。它的 `native_editor_item` 指回原版。相反，`ITEM_BEE2_BUMBLEBALL` 在原版清单无同名物品，是扩展玩法。这里的 `native: false` 指 BEE2 声明本身属于扩展；新 ID 也能复用原版实体、模型和 I/O。该索引不代表物品已安装、可直接作为 chamber type 使用，或已完成 BSP 依赖打包。第三方包和经过预编译后的最终资源不在这份官方清单快照中。[BEE2 应用](https://github.com/BEEmod/BEE2.4) · [本次官方包快照](https://github.com/BEEmod/BEE2-items/tree/09c8d97dd4633abf4472b9415ae66d567dc4eb12/packages)

在 POC 目录重建 BEE2 索引时，使用原版安装生成的 components.json 作对照，并将上游检出到字典中记录的提交。以下假设上游目录名为 BEE2-items。

```powershell
$revision = git -C .\BEE2-items rev-parse HEAD
.\.venv\Scripts\python.exe index_bee2.py .\BEE2-items\packages --revision $revision
```

`native: true` 表示该定义有版本基线支持，按原版配置使用时资源由 Portal 2 或制作端 Authoring Tools 提供。FGD 的标记证明声明来自原版；实体的运行效果仍需试玩。原生组件若改用自制模型或材质，新增文件依然要打包。

索引对照 [Steam depot 文件指纹](../stock-resource-hashes.json)，按相对路径及 SHA-1 校验散装 VMT、FGD、实例、editoritems 和 VPK 索引。VPK 判定校验目录索引，假定对应数据卷完整。基线来自本机 Portal 2 与 Authoring Tools 已安装版本的 Steam 清单，清单版本在组件字典的 `reference_depots`。外来路径记为 `extend / false`；原版路径的文件内容变化记为 `unverified / null`；同名资源有不同来源时标记 `mixed / null`。来源顺序不表示加载优先级。游戏更新后应刷新版本基线；在此之前新增路径的 extend 是相对于旧基线的判断。对于 BEE2 替换过的整个 editoritems 文件，具体条目可能需要再与原版逐项核对。字典的来源标记与 BSP 构建器的保守打包判断分别维护。
