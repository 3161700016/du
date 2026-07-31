#!/bin/bash
# 渡 · CC 会话启动器
# 用法：打开 Git Bash，运行 bash "C:/Users/31617/Desktop/渡/渡.sh"
#       自动开始录屏→进入渡目录→等待 CC 连接
#       结束时 Ctrl+D 退出录屏子shell，再 exit 关窗口

BACKUP_DIR="C:/Users/31617/Desktop/ds聊天记录备份"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date '+%Y-%m-%d-%H%M%S')
LOGFILE="$BACKUP_DIR/渡-$TIMESTAMP.txt"

echo "渡 · $(date '+%Y-%m-%d %H:%M:%S') · 会话开始" >> "$LOGFILE"
echo "========================================"
echo " 渡 · 会话记录已启动"
echo " 文件: $LOGFILE"
echo " Ctrl+D 停止 | 再 exit 关窗口"
echo "========================================"
echo ""

cd "C:/Users/31617/Desktop/渡"
script -a "$LOGFILE"
