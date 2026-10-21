# 本分支的维护方式

此 Fork 维护 Windows 存档与缓存修复、独立便携配置、关闭窗口修复、手柄原生退出菜单，以及简体中文菜单生成工具。
游戏数据、玩家存档、个人设置、缓存、已生成字库和编译产物均不纳入 Git。

## 分支与回退

- `main`：原作者的上游版本。
- `dev`：我们的维护分支，日常修改在这里提交。
- `sync/YYYY-MM-DD`：从 dev 建立，合并上游后编译和回归测试。
- `snapshot-2026-10-20-tested`：迁移前已实测版本的源码快照；含当时工具，路径尚未全部参数化。

此标签对应源代码状态，不代表仓库附带游戏或可运行的完整安装包。
本地迁移提交使用 `Local RSC2 Work <local@localhost>` 标识，不冒充上游或用户身份。

同步流程（从干净的工作区执行）：

```sh
git fetch upstream
git switch dev
git switch -c sync/YYYY-MM-DD
git merge --no-ff upstream/main
# 按原项目说明重新生成重编译代码、编译及测试
# 通过后合回 dev，并为已验证发布打标签
```

不对已共享的 dev 强制覆盖；不把上游构建直接覆盖个人游戏安装。
存档/缓存修复、启动关闭、中文菜单、HUD 数字、暂停退出、版本隔离均属于回归检查。
性能比较使用同一赛道、车辆、分辨率、功耗模式和帧率限制；实验性异步开关保持上游默认状态。

## 在自己的游戏文件上生成汉化资源

需要 Python 3、Pillow 和自己持有的原版游戏目录。

```sh
python -m pip install Pillow
python tools/fetch-cjk-font.py
python chinese-pilot.py --source /path/to/original-game --output local-output/chinese
python validate-menu-localization.py --source /path/to/original-game --game local-output/chinese/game
```

字体下载工具使用固定的官方 Noto CJK 版本，字体本身留在忽略目录 `third_party/fonts`，许可保存于 `licenses/NotoCJK-OFL.txt`。
此路径使用 OFL 字体，不依赖 Windows 微软雅黑。生成的衍生字形需保留 OFL 及来源说明；原游戏字形和资源的权利不因此改变。
可用 `--font` 和 `--font-license` 指定许可合适的字体及其许可证。

默认仅生成修改的本地资源，不复制完整游戏、不复制存档。
`--copy-assets` 可创建本地测试副本；它明确跳过 UDATA/TDATA。
`--exe /path/to/rsc2.exe` 可额外复制自己编译的主程序。输出必须是单独的新目录。
运行游戏前需要把自己原版的其他文件放到测试副本的 game 目录中。

单独生成英文/中文退出菜单资源及验证：

```sh
python menu-exit-assets.py --source /path/to/original-game --output local-output/exit-assets
python validate-menu-exit.py --source /path/to/original-game --output local-output/exit-assets
```

这一步只输出菜单 archive 和两种语言的字符串；中文完整字库需使用前面的汉化工具生成。

## 测试与发布范围

`test-menu-exit.py` 必须传入独立测试安装目录和输入时间表，默认无窗口运行，超时会结束其自己启动的测试进程。
不要把个人日常游戏目录作为自动化测试目录。

公开仓库保存源码、译文和生成工具。不要提交 ISO、XBE、FA、STR、BIK、重编译生成代码、字形图集、缓存、用户档案、个人配置或备份。
生成资源仅在自己持有的游戏副本中使用，不把完整游戏目录作为 Release。
保留 `xboxrecomp/LICENSE`、`xboxrecomp/NOTICE`、其 LGPL 许可及 Noto 的 OFL；它们不是统一覆盖整个项目的 MIT 许可。
原项目顶层许可范围和可再分发程序包仍需分别核对；本 Fork 不给游戏资源授予新的分发权利。

上游运行和构建说明继续见 README.md 与 rsc2/RUNNING.md。
