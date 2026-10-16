# Kimi 0.0.5

把普通 **Kimi 桌面版的 Work 本地 Agent** 接入官方 Magpie。不是 Kimi Code CLI，也不是 Kimi 会员／API 供应商。

## 使用

1. 在 Magpie「插件」里安装本包并启用，打开普通 Kimi 桌面应用并登录。
2. 在 Magpie「Agent」列表找到 **Kimi**，选择已有供应商的模型并连接。
3. 等 Kimi 的本地 Work Agent 就绪、当前任务结束后，插件自动接入。随后在 Kimi 的 **Work** 页面使用。
4. 在 Magpie 断开 Kimi，会恢复接入前的服务地址并热加载。原供应商、模型、登录凭据、对话和其它配置保留。

Chat 页面、云端 Claw 的模型不在本插件的接入范围内。

安装单独的、本地可还原菜单补丁后，Kimi Work 的原生模型菜单显示在 Magpie 中为 Kimi 勾选的模型，名称带 `Magpie`。在 Kimi 中选择模型后，请求按该模型的完整 ID 路由；每段对话可以选择不同模型。模型目录每 10 秒自动从本机 Magpie 同步，目录有变化才通知菜单刷新。被移除的模型会明确报错，不静默切换到其它供应商。

未安装菜单补丁时，仍可在 Magpie 的 Kimi Agent 卡片中选择默认模型；Kimi 原有的模型选项使用这个默认路由。

## 工作方式

- 使用 Magpie 正式 `magpie.agent` 接口注册 Agent，不重新构建或修改 Magpie。
- Work 的模型请求经过本机回环转发至 Magpie，改用 Magpie 为该 Agent 分配的凭据和所选模型。Kimi 登录凭据不会发送给 Magpie 或第三方模型供应商。
- Kimi 的网页读取、搜索继续使用 Kimi 原有工具服务。文件操作仍由 Kimi 执行。不会运行另一个 Kimi Code 程序。
- 对接 Kimi 自带、带鉴权的本机控制接口；修改当前 provider 的 `baseUrl`，合并专属模型 alias，保留官方模型、其它 provider 和登录凭据。
- Kimi 重启后，在本地 Work Agent 稳定、空闲时重新连接；当前任务进行中时等待，不重启应用。
- Kimi 在运行中更新账号或配置、主动覆盖连接地址时暂停适配，不持续抢写。在 Magpie 里断开再连接即可重试。

## 本地数据

数据在 `~/.config/magpie-kimi/`。`connection.json` 是 Magpie 管理的选模与连接设置；`status.json` 是不含凭据的状态。`backups/` 保存首次接入前的本机配置，可能含登录信息，只保留本机，不分享或上传。

支持的 Kimi 配置必须包含普通桌面应用的本地 Work runtime，且官方服务地址为 `https://agent-gw.kimi.com/coding/v1`。其它格式停止适配。插件使用 Kimi 内部协议，后续客户端更新可能需要适配。

插件需要 Magpie 保持运行。只监听本机随机回环端口，不修改系统代理、证书、防火墙或现有模型供应商。安装包不含个人配置、提示词、账号和密钥。

## 模型范围与菜单

Kimi 模型目录遵守 Magpie 对 `kimi-desktop` 设置的可见范围、逐模型勾选、只显示已选、模型顺序和全局禁用项。未勾选模型不会出现在连接后的菜单，发起新请求也会被拒绝；新供应商的模型不会绕过只显示已选设置。

已有的本地可还原菜单补丁可使用随包提供的 `menu-hook.cjs`。本插件不会自动修改 Kimi 安装文件。连接时菜单只显示为 Kimi 选择的模型，断开恢复原生选项。

安装入口：`github:kupakupar/magpie-agent-kimi`。

## 设备间同步

Magpie 的加密同步会携带这个 Git 安装入口；新设备会按需下载插件，列表名称为 `Kimi`。安装链接和 Agent ID `kimi-desktop` 保持不变。旧设备更新代码后，Bun 仍可能保留 `magpie-agent-kimi` 安装别名，单纯更新或重复添加相同入口不能保证改名。

如果版本已经为 0.0.5 或更新，但列表仍显示旧名称，可在 Kimi 空闲时运行 `python3 tools/fix-kimi-name.py`（Windows 也可使用 `python` 或 `py -3`）。脚本先备份 Bun 安装记录，再迁移依赖别名、锁文件记录和模块目录；不卸载插件、不改 Magpie 二进制，不读写账号凭据、供应商、提示词或对话配置。完成后重新打开 Magpie 插件页面。自定义 Magpie 配置目录可通过 `--directory` 指定。

每台设备需要自行安装并登录普通 Kimi 桌面应用、在 Magpie 中连接 Kimi。登录凭据、回环端口和本地菜单补丁不会跨设备同步。Kimi Work 供应商是独立插件，本包不包含它。
