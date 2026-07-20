"""获取本机局域网IP，写入文件供查找。"""
import socket
from pathlib import Path

def get_ips():
    hostname = socket.gethostname()
    ips = []
    try:
        # 主IP
        ips.append(("主IP", socket.gethostbyname(hostname)))
    except:
        pass

    # 尝试获取所有接口
    try:
        import netifaces
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            for addr in addrs.get(netifaces.AF_INET, []):
                ip = addr['addr']
                if not ip.startswith('127.'):
                    ips.append((iface, ip))
    except ImportError:
        pass

    return ips

if __name__ == "__main__":
    output = Path("C:/Users/31617/Desktop/渡/公共空间/当前IP.txt")
    ips = get_ips()
    lines = ["渡 · 当前访问地址", f"更新时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
    for name, ip in ips:
        lines.append(f"  http://{ip}:8765  ({name})")
    lines.append("")
    lines.append("手机浏览器打开以上地址。如果都不通，在电脑上打开 http://127.0.0.1:8765 确认服务端已启动。")

    output.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
