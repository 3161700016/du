"""
渡的灯光控制接口 v2 — 直接 HID 裸协议
绕过 POWEV Gaming.exe，直接通过 HID 发送灯光数据
"""
import hid
import time
import sys
import os

# ═══════════════════════════════════════════
# HID 设备定位
# ═══════════════════════════════════════════
TARGET_VID = 0x30FA
TARGET_PID = 0x1701
TARGET_USAGE = 0xFF01  # Col04 — 怀疑是 RGB 控制接口

# ═══════════════════════════════════════════
# EffectInfo 构造器 (与 led.py 一致)
# ═══════════════════════════════════════════
def ei(mode=0, colors=None, leds=8, bright=2, speed=0):
    """构造 57 字节 EffectInfo hex"""
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
# 颜色定义
# ═══════════════════════════════════════════
G=(0,255,0); B=(0,0,255); R=(255,0,0); W=(255,255,255)
O=(255,128,0); C=(0,255,255); P=(128,0,255)
Y=(255,255,0); K=(0,0,0)

MOODS = {
    "green":  ("全绿·思考", [G]*8),
    "blue":   ("全蓝·专注", [B]*8),
    "red":    ("全红·热烈", [R]*8),
    "cyan":   ("全青·好奇", [C]*8),
    "purple": ("全紫·灵感", [P]*8),
    "white":  ("全白·待命", [W]*8),
    "warm":   ("全橙·温暖", [O]*8),
    "off":    ("全灭·安静", [K]*8),
    "ocean":  ("海洋", [C,C,B,B,B,B,B,B]),
    "sunset": ("黄昏", [R,O,O,(255,200,50),P,P,P,P]),
    "aurora": ("极光", [G,G,C,C,P,P,P,B]),
    "forest": ("森林", [G,G,G,(0,200,0),(0,150,0),(0,100,0),(0,50,0),(0,40,0)]),
    "dawn":   ("黎明", [(255,200,100),(255,180,80),C,C,C,C,C,C]),
    "lava":   ("熔岩", [(80,0,0),(140,20,0),R,O,Y,Y,Y]),
    "frost":  ("霜冻", [W,W,C,C,C,B,B,B]),
    "ripple": ("涟漪", [C,G,C,G,C,G,C,G]),
    "pulse":  ("心跳", [R,K,R,K,R,K,R,K]),
}

# ═══════════════════════════════════════════
# HID 设备发现
# ═══════════════════════════════════════════
def find_device():
    """找到 POWEV LED 控制器的 HID 路径"""
    candidates = []
    for dev in hid.enumerate():
        if dev['vendor_id'] == TARGET_VID and dev['product_id'] == TARGET_PID:
            usage = dev.get('usage_page', 0)
            if usage in [0xFF00, 0xFF01]:
                candidates.append((usage, dev['path']))
    return candidates

# ═══════════════════════════════════════════
# 发送 HID 报告
# ═══════════════════════════════════════════
def send_effect(hex_str):
    """把 EffectInfo 通过 HID 报告发给设备"""
    data = bytes.fromhex(hex_str)

    # 找到设备
    devs = find_device()
    if not devs:
        print("[ERR] 未找到 LED HID 设备")
        return False

    print(f"[*] 找到 {len(devs)} 个候选设备")

    success = False
    for usage, path in devs:
        try:
            d = hid.device()
            d.open_path(path)
            print(f"[*] 已连接: usage=0x{usage:04X}")

            # 尝试多种发送方式
            # 方式1: 发送 Output Report (report_id=0)
            try:
                # 57字节数据 + 1字节 report_id(0) = 58字节
                report = b'\x00' + data
                # 补齐到 64 字节
                report = report.ljust(64, b'\x00')
                written = d.write(report)
                print(f"[*] Output report sent: {written} bytes")
                success = True
            except Exception as e:
                print(f"[!] Output report failed: {e}")

            # 方式2: 发送 Feature Report
            if not success:
                try:
                    d.send_feature_report(data.ljust(64, b'\x00'))
                    print(f"[*] Feature report sent")
                    success = True
                except Exception as e:
                    print(f"[!] Feature report failed: {e}")

            d.close()
        except Exception as e:
            print(f"[!] Device error: {e}")

    return success

# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python led_raw.py <心情>")
        print(f"心情: {', '.join(sorted(MOODS.keys()))}")
        sys.exit(0)

    arg = sys.argv[1]
    if arg == "--list":
        for name, (desc, _) in sorted(MOODS.items()):
            print(f"  {name:12s} -> {desc}")
        sys.exit(0)

    if arg == "--scan":
        devs = find_device()
        print(f"找到 {len(devs)} 个设备:")
        for u, p in devs:
            print(f"  usage=0x{u:04X} path={p}")
        sys.exit(0)

    if arg in MOODS:
        desc, colors = MOODS[arg]
        hex_str = ei(colors=colors)
        print(f"[*] 效果: {desc}")
        print(f"[*] hex: {hex_str[:40]}...")
        if send_effect(hex_str):
            print(f"[OK] {desc}")
        else:
            print(f"[FAIL] 发送失败")
    else:
        print(f"[!] 未知: {arg}")
