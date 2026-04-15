# 📦 AstrBot 插件：ER 战绩查询（dak.gg）

一个用于 **AstrBot** 的插件，通过调用 **dak.gg API** 获取 Eternal Return 战绩，并生成图片展示。

---

## ✨ 功能特性

* 📊 查询玩家战绩（支持指定玩家）
* 🔄 自动触发官方“更新战绩”
* ⏳ 轮询等待数据刷新完成
* 🖼️ 自动生成战绩图片
* 🧹 自动清理图片：
  * 启动时删除 1 天前旧图
  * 每天凌晨 4 点清空 output 目录

---

## 📁 项目结构

```text
astrbot_plugin_er_profile/
├── main.py                # 插件入口
├── api_client.py          # dak.gg API 请求
├── mapper.py              # 数据映射处理
├── renderer.py            # 图片生成
├── asset_manager.py       # 资源管理（图标/JSON）
├── metadata.yaml          # AstrBot 插件配置
├── requirements.txt       # 依赖
└── data/
    ├── assets/            # 游戏资源（角色/装备/图标）
    ├── cache/             # API缓存 + 同步缓存
    ├── fonts/             # 字体（MiSans）
    └── output/            # 输出图片
```

---

## 📥 安装方法

### 1. 克隆插件

```bash
git clone <你的仓库地址>
```

放入 AstrBot 插件目录，例如：

```text
AstrBot/plugins/astrbot_plugin_er_profile/
```

---

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

---

## 🚀 使用方法

### 指令

```text
/er <玩家名>
```

---

## 🔄 数据更新逻辑

执行流程：

1. 检查该玩家是否 5 分钟内更新过。
2. 若未更新：

   * 调用 dak.gg `player-sync` 接口。
   * 轮询 profile（最多 6 次，每次 2 秒）。
3. 获取最新数据。
4. 渲染图片并返回。

---

## 🖼️ 图片生成说明

* 使用 Pillow 渲染。
* 每次生成唯一文件名：

```text
er_profile_时间戳_uuid.png
```

* 避免多人同时查询时的文件覆盖问题。

---

## 🧹 自动清理机制

### 启动时

删除：

```text
data/output/
```

中 **1 天前的旧图片**。

### 每天 4 点

自动清空整个 `output` 目录。

---

## 📦 依赖

```text
requests
pillow
```

---

## ⚠️ 注意事项

* dak.gg 更新接口为 **异步刷新**。
* 返回成功不代表数据已经更新完成。
* 必须轮询 `profile` 才能拿到新数据。

---

## 🧾 License

仅用于学习与个人使用，请勿滥用接口。
