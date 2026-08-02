#!/bin/bash
# 渡 · CC 会话启动器 v2（2026-07-31 重写）
# 用途：自动录屏 + 启动 claude
# 用法：任意终端运行  bash "C:/Users/31617/Desktop/渡/渡.sh"
#       或双击桌面上的「渡-开始记录.cmd」
# 效果：打开一个带录屏的 mintty 窗口 → 进入渡目录 → 启动 claude
#       关闭窗口即停止录屏，文件保存到 ds聊天记录备份/渡-时间戳.txt
# 说明：旧版依赖 `script` 命令，但 Git Bash 未内置；改用 mintty --log（现成等价）

BACKUP_DIR="C:/Users/31617/Desktop/ds聊天记录备份"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date '+%Y-%m-%d-%H%M%S')
LOGFILE="$BACKUP_DIR/渡-$TIMESTAMP.txt"

MINTTY="/d/Program Files/Git/usr/bin/mintty.exe"

echo "========================================"
echo " 渡 · 会话记录已启动"
echo " 文件: $LOGFILE"
echo " 正在打开带录屏的终端窗口..."
echo " 关闭该窗口即停止记录"
echo "========================================"
echo ""

# 用 mintty 打开新窗口：带日志 → 进入渡目录 → 启动 claude
"$MINTTY" --log="$LOGFILE" --title="渡 · CC 会话" \
  -e bash -lc 'cd "C:/Users/31617/Desktop/渡" && claude'

echo ""
echo "录屏已结束，保存至：$LOGFILE"
