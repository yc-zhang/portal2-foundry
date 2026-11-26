"""Portal 2 VMF reference for the sections used or recognised by the POC."""
SECTIONS = {
    "world": {
        "purpose": "worldspawn 定义地图全局属性，包含静态 brush 几何。",
        "json_control": "world[].min/max 生成轴对齐长方体；material 引用材质别名。skyname 固定为 sky_black_nofog。",
        "fields": {"id": "对象编号", "classname": "worldspawn", "mapversion": "与 versioninfo.mapversion 对应",
                   "skyname": "天空盒名", "solid.side.plane": "确定面的三个点",
                   "solid.side.material": "材质路径，见 ../materials.json",
                   "solid.side.uaxis / vaxis": "贴图轴、偏移与缩放", "solid.side.rotation": "贴图旋转",
                   "solid.side.lightmapscale": "光照贴图采样间距", "editor": "Hammer 编辑状态"},
    },
    "entity": {
        "purpose": "每个实体一个区块。classname 决定实体行为、可用属性与 I/O。",
        "json_control": "components[] 选择预设并设置位置、边界等；connections[] 设置跨实体连线。",
        "fields": {"id": "实体编号", "classname": "Source 实体类，见 ../components.json",
                   "targetname": "I/O 可引用的名字", "origin": "世界坐标", "angles": "朝向",
                   "solid": "门、触发区等 brush 实体的几何", "file": "func_instance 的源 VMF",
                   "connections": "事件输出子块，见 ../connections.json", "editor": "Hammer 编辑状态"},
    },
    "versioninfo": {
        "purpose": "VMF 文件和编辑器版本信息。", "json_control": "srctools 导出时填写。",
        "fields": {"editorversion": "编辑器版本", "editorbuild": "编辑器构建号", "mapversion": "地图修订号",
                   "formatversion": "VMF 格式版本", "prefab": "是否为预制件"},
    },
    "visgroups": {
        "purpose": "在 Hammer 中分组显示或隐藏对象。", "json_control": "默认空分组；chamber.json 无此配置。",
        "fields": {"visgroup.name": "组名", "visgroup.visgroupid": "对象 editor 块引用的组 ID",
                   "visgroup.color": "编辑器颜色", "visgroup.visgroup": "嵌套分组"},
    },
    "viewsettings": {
        "purpose": "Hammer 编辑视图的网格和吸附偏好。", "json_control": "使用 srctools 默认值。",
        "fields": {"bSnapToGrid": "网格吸附", "bShowGrid": "二维网格", "bShowLogicalGrid": "逻辑视图网格",
                   "nGridSpacing": "网格间距", "bShow3DGrid": "三维网格"},
    },
    "cameras": {
        "purpose": "保存 Hammer 的观察视角；游戏镜头由实体控制。", "json_control": "默认无已保存视角。",
        "fields": {"activecamera": "当前视角；-1 表示没有选中", "camera.position": "观察点",
                   "camera.look": "观察目标坐标"},
    },
    "cordons": {
        "purpose": "Hammer 局部编译的空间范围。", "json_control": "默认关闭。",
        "fields": {"active": "全局开关", "cordon.name": "范围名", "cordon.active": "单个范围开关",
                   "cordon.box.mins": "边界最小角", "cordon.box.maxs": "边界最大角"},
    },
    "hidden": {
        "purpose": "在顶层包裹隐藏实体；world 或实体内部也能用 hidden 包裹隐藏 brush。",
        "json_control": "仅在对象被设为隐藏时出现；chamber.json 无此配置。",
        "fields": {"entity": "隐藏实体的完整区块"},
    },
    "quickhide": {
        "purpose": "Hammer 快速隐藏操作对应的对象计数。",
        "json_control": "srctools 在计数大于 0 时导出；chamber.json 无此配置。",
        "fields": {"count": "快速隐藏计数"},
    },
}
