# 在 Windows 上构建、检查和运行 Portal 2 地图

从仓库的 `POC/` 目录打开 PowerShell。以下命令针对 Steam 原版 Portal 2。本项目的源文件是 VMF，游戏加载 BSP。Steam 工坊条目另有标题、封面和可见性。本地测试可以直接加载 BSP。

## 直接玩已有地图

把本目录的 `foundry_button.bsp` 复制到 `Portal 2\portal2\maps`。在 Portal 2 的「选项 → 键盘/鼠标」启用开发者控制台，按 Esc 返回，按键盘左上角的 `~` 键打开控制台，输入：

```text
map foundry_button
```

加载其他地图时换为对应的文件名，省略 .bsp。也可在 Steam 的 Portal 2 属性 → 通用 → 启动选项中临时填写 `-console +map foundry_button`，然后启动游戏；试玩后移除即可恢复正常启动。控制台提示找不到图时，检查文件是否位于当前 Steam 库的 `Portal 2\portal2\maps\`。

## 用项目脚本编译

先在 Steam 库的工具分类中安装 **Portal 2 Authoring Tools**。本机游戏目录是 `C:\Program Files (x86)\Steam\steamapps\common\Portal 2`。其中 `bin` 提供 Hammer 和编译器，`portal2\gameinfo.txt` 定义游戏资源搜索路径，`sdk_content\maps\instances` 存放制作期复用的 VMF。

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\build-map.ps1 -Vmf .\foundry_button.vmf
```

脚本在游戏的 `sdk_content\maps\foundry_build_<唯一编号>\` 创建独立构建目录，保留原地图名。成功后将同名 BSP 和日志复制到 VMF 旁。加 `-Install` 同时更新 `portal2\maps\<地图名>.bsp`；已有同名产物将被替换。Steam 库在其他位置时传入 `-GameRoot 'D:\SteamLibrary\steamapps\common\Portal 2'`。RemoteSigned 仅用于本次 PowerShell 进程。

## 逐条执行底层命令

下面用仅引用原版资源的小房间示范三个底层编译命令。含自定义贴花的最终大房间请使用上面的脚本，脚本会额外调用 BSPZIP。每个阶段只在前一阶段成功后运行。

```powershell
$source = Get-Item -LiteralPath '.\foundry_srctools.vmf'
$root = 'C:\Program Files (x86)\Steam\steamapps\common\Portal 2'
$game = Join-Path $root 'portal2'
$stage = Join-Path $root ('sdk_content\maps\foundry_build_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
$base = Join-Path $stage $source.BaseName
Copy-Item -LiteralPath $source.FullName -Destination "$base.vmf"

& "$root\bin\vbsp.exe" -game $game $base
if ($LASTEXITCODE -ne 0 -or !(Test-Path "$base.prt") -or (Test-Path "$base.lin")) {
    throw "VBSP failed or the map leaked. Check $base.log"
}
& "$root\bin\vvis.exe" -game $game $base
if ($LASTEXITCODE -ne 0) { throw "VVIS failed. Check $base.log" }
& "$root\bin\vrad.exe" -both -game $game $base
if ($LASTEXITCODE -ne 0) { throw "VRAD failed. Check $base.log" }
Copy-Item -LiteralPath "$base.bsp" -Destination (Join-Path $game "maps\$($source.BaseName).bsp")
```

| 阶段 | 输入和产物 | 如何判断 |
|---|---|---|
| VBSP | 读取 VMF、解析实例、生成几何与碰撞，写出初始 BSP 和可见性入口文件 PRT | 检查日志中的 instance、material 和 leak 信息。房间泄漏时，在 Hammer 打开构建目录里的 VMF，使用 Map → Load Pointfile 沿线查找缺口或落在封闭空间外的实体。 |
| VVIS | 读取 BSP 和 PRT，将预计算的区域可见性写回同一 BSP | 查看 portalclusters 和 visdata。这里的 portal 指可见性分区边界。 |
| VRAD | 根据光源、表面和遮挡烘焙光照，再次写回 BSP | `-both` 构建 LDR 和 HDR 两套光照。检查日志里的 lightdata、光源数和最终写入路径。 |

`-game` 后面是含 `gameinfo.txt` 的子目录；最后一个参数是地图路径主干。若 VBSP 在项目目录或系统临时目录报告 `Can't create LogFile`，先按上例将 VMF 放入游戏 SDK 目录。在本机这一步解决了问题。若日志报告缺失 instance，检查 VMF 的 `file` 相对路径是否能在 `sdk_content\maps` 下找到对应文件。[Valve 问题记录](https://github.com/ValveSoftware/portal2/issues/430)

## 从描述生成 VMF

示例使用整数 Hammer 单位，Z 轴向上。每个 world 条目通过两个角点定义一个长方体。components 定义可复用类型的实例，connections 通过组件 ID 和端口名连接两端。在新电脑上先安装 Python 3.12，再执行以下命令。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe generate_vmf.py chamber.json foundry_srctools.vmf
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\build-map.ps1 -Vmf .\foundry_srctools.vmf -Install
```

| 描述中的内容 | 生成器写入 VMF 的内容 |
|---|---|
| world 的 min、max、material | srctools 的 make_prism 生成六面 brush，材质别名解析为 Source 材质名。若要每面用不同材质，可在加入地图前设置返回对象的 top、bottom 等面的 mat。 |
| cube、floor_button | 创建 prop_weighted_cube、prop_floor_button 实体；按钮指定原版 MDL 模型。 |
| lift_door、finish_zone | 把 brush 挂在 func_door 或 trigger_once 下；触发体用 tools/toolstrigger。 |
| plate.pressed → gate.open | 写入 OnPressed → gate → Open。释放按钮映射为 OnUnPressed → Close。 |
| exit_zone.entered → pti.finish | 写入一次性的 OnStartTouch，向官方实例中的 @relay_pti_level_end 发送 Trigger。 |
| workshop_finish | 放置 func_instance 并引用 instances/p2editor/global_pti_ents.vmf。VBSP 展开该实例。 |

材质别名指向相对于 `materials/` 的 VMT 名称，通常省略扩展名。VMT 的着色器及参数可以引用 VTF 纹理；brush 面保存材质名、贴图轴与缩放。原版资源由游戏挂载。若引入自定义 MDL、VMT 或声音，需要解析其依赖，并把玩家缺少的文件打入 BSP 的 pakfile。构建脚本会将 `assets/<地图名>/` 下的资源挂载到游戏目录，并使用 BSPZIP 随图打包。扩展组件时，可以从本机 `bin\portal2.fgd` 和它包含的 FGD 核对实体属性和 I/O，从原版实例核对模型、朝向、偏移和运行逻辑。[srctools VMF API](https://srctools.readthedocs.io/en/stable/modules/vmf.html) · [Valve 工坊结束逻辑](https://www.thinkwithportals.com/puzzlemaker/workshop_compatibility.php)

## 在 Hammer 和游戏中分别验收

用 Portal 2 Authoring Tools 启动 Hammer，选择 Portal 2 配置。用 File → Open 打开构建目录的 VMF，这样也便于查找实例和 pointfile。按 Alt+P 检查地图问题。在 3D 视图检查门洞、按钮高度和触发体范围。在 foundry_srctools 小房间中选择 plate → Properties → Outputs，检查 gate 的 Open 和 Close 两条连线。F9 可从 Hammer 调用编译与运行流程。直接编辑生成的 VMF 后，若希望下次生成仍保留改动，应把对应修改写回 JSON 或组件定义。

在游戏控制台执行 `map foundry_srctools`。依次验证出生位置、站上按钮时门打开、离开按钮时门关闭、方块压住按钮时玩家能穿过门。普通控制台加载适合验证交互；通过工坊队列完成一次才算验证订阅、结算和投票全流程。

## BEE2 组件怎样交给 Hammer

BEE2 的包包含 PeTI 物品定义、样式、实例、资源和编译规则。要观察一个复杂物品的实际实现，可在 BEE2 将物品和样式导出到 Portal 2，在游戏内用它搭一间小房并执行构建；然后查看编译日志里 styled VMF 的实际路径，通常是 `sdk_content\maps\styled\preview.vmf`。将其另存为独立文件，用 Hammer 打开并沿 func_instance 的 file、参数和 I/O 追踪。仅调用 puzzlemaker_export 获得的原始 VMF 可能还未套用 BEE2 规则。

要复用单个独立实例，在 Hammer 放置 func_instance，选择已安装到 SDK 的实例 VMF，配置朝向、实例名和参数，并接上该实例公开的 I/O。若组件依赖 BEE2 在编译时生成的继电器、邻接检测、指示灯或样式替换，单独放置实例不足以重现这些行为。用同一物品的 styled 小样核对额外实体和资源，再决定将哪些部分封装为 srctools 的组件。普通 Hammer 图按 BEE2 的编译器判断会跳过 PeTI 转换。这是调研路线，本次示例使用 Valve 原版组件。[BEE2 物品包](https://github.com/BEEmod/BEE2-items) · [BEE2 编译器实现](https://github.com/BEEmod/BEE2.4/blob/master/src/vbsp.py)
