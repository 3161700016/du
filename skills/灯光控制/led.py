"""
渡的灯光控制接口 · POWEV LED
==============================
用法:
  python led.py <心情名>          -- 切换预设心情
  python led.py --list            -- 列出所有预设
  python led.py --raw <hex>       -- 发送原始 EffectInfo0 hex
  python led.py --file <文件>     -- 从灯光文件读取
  python led.py --startup         -- 设置开机自启(托盘常驻)

灯光文件格式 (.light):
  第一行: EffectInfo0 hex
  第二行: EffectInfo1 hex (可选,默认同第一行)
  其余行忽略,可写注释

注意: 内存条上下反装,LED 1=视觉底部,LED 8=视觉顶部
"""

import sys, os, re, time, subprocess

# ═══════════════════════════════════════════
# 路径配置
# ═══════════════════════════════════════════
CFG  = r"C:\Users\31617\AppData\Roaming\POWEV\POWEV RGB\config"
EXE  = r"D:\Program Files (x86)\POWEV\POWEV Lighting\Gaming.exe"
HID  = r"D:\Program Files (x86)\POWEV\POWEV Lighting\hid.exe"
REG  = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
NAME = "POWEV_Lighting"

# ═══════════════════════════════════════════
# EffectInfo 构造器
# ═══════════════════════════════════════════
def ei(mode=0, colors=None, leds=8, bright=2, speed=0):
    """
    构造 EffectInfo hex。
    mode:  0=静态, 1=呼吸?, 5=?
    colors: [(R,G,B), ...] 列表,不足 leds 则用最后一个填充
    """
    if colors is None:
        colors = [(0, 255, 0)] * leds
    while len(colors) < leds:
        colors.append(colors[-1])

    header = f"{mode:02X}000000" + f"01000000" + f"{leds:02X}000000" + "00000000"
    body  = "".join(f"{r:02X}{g:02X}{b:02X}00" for r, g, b in colors[:leds])  # 格式: [R][G][B][00], 末字节=使能(0=亮)
    tail  = f"{bright:02X}000000" + f"{speed:02X}000000"

    raw = header + body + tail
    chk = sum(int(raw[i:i+2], 16) for i in range(0, len(raw), 2)) % 256
    return raw + f"{chk:02X}"

# ═══════════════════════════════════════════
# 颜色常量
# ═══════════════════════════════════════════
G=(0,255,0); B=(0,0,255); R=(255,0,0); W=(255,255,255)
O=(255,128,0); C=(0,255,255); P=(128,0,255); Y=(255,255,0)
K=(0,0,0)  # 灭
D=(0,80,0)  # 暗绿
DG=(0,40,0) # 深绿

# 暖色渐变辅助
WARM_TOP    = (255,200,150)  # 暖白
WARM_MID    = (255,160,80)   # 橙色
WARM_BOTTOM = (200,100,30)   # 深橙

# ═══════════════════════════════════════════
# 心情预设  (LED 1→8 = 视觉底部→顶部)
# ═══════════════════════════════════════════
MOODS = {
    # ── 纯色 ──
    "安静":   ("全灭,休眠",       [K]*8),
    "思考":   ("全绿,平静思考",    [G]*8),
    "专注":   ("全蓝,深度专注",    [B]*8),
    "热烈":   ("全红,兴奋激昂",    [R]*8),
    "好奇":   ("全青,清澈探索",    [C]*8),
    "灵感":   ("全紫,哲学思辨",    [P]*8),
    "待命":   ("全白,中性等待",    [W]*8),
    "温暖":   ("全橙,友好温暖",    [O]*8),

    # ── 渐变(底部→顶部, 视觉上从机箱深处向外发散) ──
    "海洋":   ("青入蓝,深海沉静",  [C,C,B,B,B,B,B,B]),
    "森林":   ("亮绿入暗,林间幽深", [G,G,G,(0,200,0),(0,150,0),(0,100,0),(0,50,0),DG]),
    "黄昏":   ("红→紫,暮色四合",  [R,O,O,(255,200,50),P,P,P,P]),
    "黎明":   ("暖金→青,东方既白", [(255,200,100),(255,180,80),C,C,C,C,C,C]),
    "极光":   ("绿→青→紫,极光流转", [G,G,C,C,P,P,P,B]),
    "熔岩":   ("暗红→亮橙,地心热流", [(80,0,0),(140,20,0),R,O,Y,Y,Y]),
    "霜冻":   ("白→冰蓝,寒霜蔓延", [W,W,C,C,C,B,B,B]),

    # ── 交替节奏 ──
    "涟漪":   ("青绿交替,思绪荡漾", [C,G,C,G,C,G,C,G]),
    "心跳":   ("红黑交替,紧张脉动", [R,K,R,K,R,K,R,K]),

    # ── 英文别名(方便快速输入) ──
    "green":  ("思考", [G]*8),
    "blue":   ("专注", [B]*8),
    "red":    ("热烈", [R]*8),
    "cyan":   ("好奇", [C]*8),
    "purple": ("灵感", [P]*8),
    "white":  ("待命", [W]*8),
    "warm":   ("温暖", [O]*8),
    "off":    ("安静", [K]*8),
    "ocean":  ("海洋", [C,C,B,B,B,B,B,B]),
    "forest": ("森林", [G,G,G,(0,200,0),(0,150,0),(0,100,0),(0,50,0),DG]),
    "sunset": ("黄昏", [R,O,O,(255,200,50),P,P,P,P]),
    "dawn":   ("黎明", [(255,200,100),(255,180,80),C,C,C,C,C,C]),
    "aurora": ("极光", [G,G,C,C,P,P,P,B]),
    "lava":   ("熔岩", [(80,0,0),(140,20,0),R,O,Y,Y,Y]),
    "frost":  ("霜冻", [W,W,C,C,C,B,B,B]),
    "ripple": ("涟漪", [C,G,C,G,C,G,C,G]),
    "pulse":  ("心跳", [R,K,R,K,R,K,R,K]),
}

# ═══════════════════════════════════════════
# 核心操作: 写配置 + 重启 HID
# ═══════════════════════════════════════════
def apply(ei0, ei1=None):
    """先杀进程 → 写配置 → 重启，防止 Gaming 退出时覆盖配置"""
    if ei1 is None:
        ei1 = ei0

    # 1. 先杀掉，防止 Gaming 退出时把内存状态写回 config
    subprocess.run(["taskkill", "/F", "/IM", "Gaming.exe"],
                   capture_output=True, creationflags=0x08000000)
    subprocess.run(["taskkill", "/F", "/IM", "hid.exe"],
                   capture_output=True, creationflags=0x08000000)
    time.sleep(0.5)

    # 2. 读配置，修改
    with open(CFG, "r", encoding="utf-8") as f:
        txt = f.read()

    sec = r"(\[Profile0Setting\][^\[]*?EffectInfo0=)[^\r\n]*"
    txt = re.sub(sec, f"\\g<1>{ei0}", txt, flags=re.DOTALL)
    sec = r"(\[Profile0Setting\][^\[]*?EffectInfo1=)[^\r\n]*"
    txt = re.sub(sec, f"\\g<1>{ei1}", txt, flags=re.DOTALL)

    with open(CFG, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(txt)

    # 3. 重启 Gaming，隐藏窗口
    time.sleep(0.3)
    si = subprocess.STARTUPINFO()
    si.dwFlags = subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    subprocess.Popen([EXE, "--hidden"], cwd=os.path.dirname(EXE),
                     startupinfo=si, creationflags=0x08000000)
    # 二次确保：枚举并隐藏所有 Gaming 窗口
    time.sleep(0.8)
    import ctypes
    user32 = ctypes.windll.user32
    titles = ["POWEV-RGB_Config", "POWEV Lighting", "Gaming"]
    for t in titles:
        hwnd = user32.FindWindowW(None, t)
        if hwnd:
            user32.ShowWindow(hwnd, 0)  # SW_HIDE

# ═══════════════════════════════════════════
# 开机自启
# ═══════════════════════════════════════════
def setup_startup():
    """添加 Gaming.exe --hidden 到注册表 Run 键"""
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                         0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ,
                      f'"{EXE}" --hidden')
    winreg.CloseKey(key)
    print(f"[OK] 已设置开机自启: {NAME} (托盘静默)")
    print(f"    取消: reg delete {REG} /v {NAME} /f")

# ═══════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("渡 · LED 灯光控制")
        print("用法: python led.py <心情>  |  python led.py --list")
        print("      python led.py --raw <hex>  |  python led.py --file <.light>")
        print("      python led.py --startup")
        print(f"心情: {' | '.join(sorted(set(k for k in MOODS if not k.isascii() or len(k)>6)))}")
        sys.exit(0)

    arg = sys.argv[1]

    if arg == "--list":
        shown = set()
        for name, (desc, _) in sorted(MOODS.items()):
            if desc not in shown:
                print(f"  {name:12s} → {desc}")
                shown.add(desc)

    elif arg == "--raw":
        if len(sys.argv) < 3:
            print("用法: python led.py --raw <EffectInfo0_hex> [EffectInfo1_hex]")
            sys.exit(1)
        ei0 = sys.argv[2]
        ei1 = sys.argv[3] if len(sys.argv) > 3 else ei0
        apply(ei0, ei1)
        print(f"[OK] 已发送原始灯光数据")

    elif arg == "--file":
        if len(sys.argv) < 3:
            print("用法: python led.py --file <灯光文件.light>")
            sys.exit(1)
        with open(sys.argv[2], "r") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
        ei0 = lines[0] if lines else ei(G, [G]*8)
        ei1 = lines[1] if len(lines) > 1 else ei0
        apply(ei0, ei1)
        print(f"[OK] 已加载灯光文件: {sys.argv[2]}")

    elif arg == "--startup":
        setup_startup()

    elif arg in MOODS:
        desc, colors = MOODS[arg]
        ei_hex = ei(colors=colors)
        apply(ei_hex)
        print(f"[OK] {desc}")
        # 如果效果只配了一种颜色(纯色),两个设备同色
        # 否则可能需要区分 EffectInfo0 和 EffectInfo1,
        # 当前版本两个设备使用相同效果

    else:
        print(f"[!] 未知心情: {arg}")
        print(f"    可用: python led.py --list")
        sys.exit(1)
