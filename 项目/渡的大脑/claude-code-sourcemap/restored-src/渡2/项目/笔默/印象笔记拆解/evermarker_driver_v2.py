"""
EverMarker BLE 驱动 — 核心模块
===============================
负责 BLE 扫描、连接、服务发现和数据通知订阅。

对久阳的说明（移动开发入门）：
  BLE (Bluetooth Low Energy) 的工作方式与经典蓝牙不同。
  它不像串口那样建立持续连接后就一直传数据，而是基于
  "服务-特征-描述符" 的三层结构：

  1. Service（服务）    — 设备提供的功能模块（如"数据通道"）
  2. Characteristic（特征）— 服务下的数据端点（可读/可写/可通知）
  3. Descriptor（描述符） — 特征的元数据（如"启用通知"）

  相当于：Service=文件夹，Characteristic=文件，Descriptor=文件属性。

  我们通过订阅"通知(Notify)"来接收笔发来的数据——
  笔有新数据时主动推给手机，不需要手机反复轮询。

依赖：
  - bleak (跨平台 BLE 库)
  - asyncio (Python 标准库，异步 I/O)
"""

import asyncio
import logging
from typing import Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum

from bleak import BleakScanner, BleakClient, BLEDevice, AdvertisementData

logger = logging.getLogger("evermarker")

# ============================================================================
# BLE UUID 常量 — 从 APK 逆向分析中提取
# ============================================================================

# --- Nordic UART Service (NUS) — 主要数据通道 ---
# 这是最可能的数据通信通道。Nordic 芯片大量用于 IoT 设备。
NUS_SERVICE_UUID      = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_CHAR_TX_UUID      = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # 手机→笔 (Write)
NUS_CHAR_RX_UUID      = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # 笔→手机 (Notify)

# --- NUS 变体（可能是不同固件或第二通道）---
NUS_ALT_SERVICE_UUID  = "8E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_ALT_CHAR_TX_UUID  = "8E400002-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_ALT_CHAR_RX_UUID  = "8E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# --- EverScan 自定义数据服务 ---
EE_SERVICE_UUID       = "0000EE00-0000-1000-8000-00805F9B34FB"
EE_CHAR_DATA1_UUID    = "0000EE01-0000-1000-8000-00805F9B34FB"
EE_CHAR_DATA2_UUID    = "0000EE02-0000-1000-8000-00805F9B34FB"

# --- EverScan 其他自定义服务 ---
AE_SERVICE_UUID       = "0000AE21-0000-1000-8000-00805F9B34FB"
AE_CHAR_1_UUID        = "0000AE22-0000-1000-8000-00805F9B34FB"
AE_CHAR_2_UUID        = "0000AE23-0000-1000-8000-00805F9B34FB"

F1_SERVICE_UUID       = "0000F100-0000-1000-8000-00805F9B34FB"
F1_CHAR_1_UUID        = "0000F101-0000-1000-8000-00805F9B34FB"
F1_CHAR_2_UUID        = "0000F102-0000-1000-8000-00805F9B34FB"

# --- 标准 UUID ---
CCCD_UUID             = "00002902-0000-1000-8000-00805F9B34FB"
# CCCD = Client Characteristic Configuration Descriptor
# 写入 0x0001 启用通知(Notify)，0x0002 启用指示(Indicate)

# ============================================================================
# 设备名称匹配
# ============================================================================

# EverMarker 设备的广播名称关键词（扫描时用于过滤）
EVERMARKER_NAME_KEYWORDS = [
    "EverMarker",
    "evermarker",
    "EverMARKER",
    "EverPen",
    "everpen",
    "EVERPEN",
    "YX-Scan",
    "YX-Pen",
    "Yinxiang",
    "印象笔记",
    "扫译笔",
    "SmartPen",
    "Evernote Pen",
    "Evernote Marker",
]

# ============================================================================
# 数据结构
# ============================================================================

class ConnectionState(Enum):
    """BLE 连接状态"""
    DISCONNECTED  = "disconnected"
    SCANNING      = "scanning"
    CONNECTING    = "connecting"
    CONNECTED     = "connected"
    DISCONNECTING = "disconnecting"


@dataclass
class EverMarkerDevice:
    """发现的 EverMarker 设备信息"""
    name: str
    address: str        # MAC 地址 (Windows/Linux) 或 UUID (macOS)
    rssi: int           # 信号强度 (dBm)，越大越好（-30 很近，-80 很远）
    device: BLEDevice   # bleak 原生设备对象

    def __str__(self):
        return f"{self.name} ({self.address}) RSSI: {self.rssi} dBm"


@dataclass
class ScanResult:
    """单次扫描的文本结果"""
    text: str
    timestamp: float
    raw_data: bytes = field(repr=False)


# ============================================================================
# 回调类型
# ============================================================================

# 收到文本时的回调: (text: str) -> None
TextCallback = Callable[[str], None]

# 收到原始数据时的回调: (data: bytes) -> None
RawDataCallback = Callable[[bytes], None]

# 连接状态变化回调: (old_state, new_state) -> None
StateCallback = Callable[[ConnectionState, ConnectionState], None]


# ============================================================================
# EverMarker BLE 驱动
# ============================================================================

class EverMarkerDriver:
    """
    EverMarker 扫译笔 BLE 驱动。

    使用示例:

        driver = EverMarkerDriver()
        driver.on_text_received = lambda text: print(f"扫描到: {text}")

        # 扫描设备
        devices = await driver.scan(timeout=5.0)

        # 连接第一个设备
        if devices:
            await driver.connect(devices[0])

        # 保持运行
        await asyncio.sleep(60)
        await driver.disconnect()
    """

    def __init__(self):
        # 连接状态
        self._state = ConnectionState.DISCONNECTED
        self._client: Optional[BleakClient] = None
        self._device: Optional[EverMarkerDevice] = None

        # 已发现的通知特征（用于取消订阅）
        self._notify_chars: List[str] = []
        # 已发现的可写特征（用于发送命令）
        self._write_chars: List[str] = []

        # 回调函数
        self.on_text_received: Optional[TextCallback] = None
        self.on_raw_data: Optional[RawDataCallback] = None
        self.on_state_change: Optional[StateCallback] = None

        # 文本缓冲区（用于拼接分段数据）
        self._text_buffer: str = ""

    # ---- 属性 ----

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def device(self) -> Optional[EverMarkerDevice]:
        return self._device

    # ---- 状态管理 ----

    def _set_state(self, new_state: ConnectionState):
        old = self._state
        self._state = new_state
        logger.info(f"状态: {old.value} → {new_state.value}")
        if self.on_state_change:
            try:
                self.on_state_change(old, new_state)
            except Exception as e:
                logger.error(f"状态回调异常: {e}")

    # ---- 设备扫描 ----

    @staticmethod
    async def scan(timeout: float = 5.0) -> List[EverMarkerDevice]:
        """
        扫描附近的 BLE 设备，返回匹配 EverMarker 名称的设备列表。

        参数:
            timeout: 扫描时长（秒），BLE 扫描需要一定时间收集广播包

        返回:
            EverMarkerDevice 列表，按信号强度降序排列
        """
        logger.info(f"开始 BLE 扫描 ({timeout}s)...")
        print(f"  正在扫描 BLE 设备 ({timeout} 秒)...")
        print(f"  请确保扫译笔已开机且在附近。")

        found_devices: List[EverMarkerDevice] = []

        def _detection_callback(device: BLEDevice, adv_data: AdvertisementData):
            """bleak 每发现一个设备就回调一次"""
            name = device.name or adv_data.local_name or "(未知设备)"

            # 检查名称是否匹配
            is_match = any(kw.lower() in name.lower()
                          for kw in EVERMARKER_NAME_KEYWORDS)

            if is_match:
                em_device = EverMarkerDevice(
                    name=name,
                    address=device.address,
                    rssi=adv_data.rssi or -100,
                    device=device,
                )
                # 避免重复（同一个设备可能被多次发现）
                if not any(d.address == em_device.address for d in found_devices):
                    found_devices.append(em_device)
                    logger.info(f"发现设备: {em_device}")

        scanner = BleakScanner(detection_callback=_detection_callback)
        await scanner.start()
        await asyncio.sleep(timeout)
        await scanner.stop()

        # 按信号强度排序（信号强的排前面 = 离得近）
        found_devices.sort(key=lambda d: d.rssi, reverse=True)
        return found_devices

    # ---- 连接管理 ----

    async def connect(self, device: EverMarkerDevice, auto_handshake: bool = True) -> bool:
        """
        连接到指定的 EverMarker 设备。

        连接过程：
          1. 建立 BLE 连接
          2. 发现所有服务(GATT Services)
          3. 查找并订阅数据通知特征
          4. 注册断开回调

        参数:
            device: 要连接的设备

        返回:
            是否连接成功
        """
        self._device = device
        self._set_state(ConnectionState.CONNECTING)

        # 断开回调——当硬件断开连接时触发
        def _on_disconnect(client: BleakClient):
            logger.warning(f"设备已断开: {device.address}")
            self._set_state(ConnectionState.DISCONNECTED)
            self._notify_chars.clear()
            self._write_chars.clear()

        self._client = BleakClient(
            device.device,
            disconnected_callback=_on_disconnect,
        )

        try:
            logger.info(f"正在连接 {device} ...")
            print(f"  正在连接 {device.name} ...")
            await self._client.connect()
            logger.info("BLE 连接已建立")

            # ★ 尝试配对 (Pair/Bond) — 许多 BLE 设备需要加密链路
            # 才接受 UART 命令。连接(Connect)≠配对(Pair)。
            try:
                print(f"  🔐 尝试配对...")
                await self._client.pair()
                print(f"  ✓ 配对成功")
            except Exception as e:
                print(f"  ⚠ 配对失败: {e}")
                print(f"    笔可能不支持配对，或用 Just Works 模式（无需 PIN）")

            # 发现服务和特征
            await self._discover_and_subscribe()

            self._set_state(ConnectionState.CONNECTED)
            print(f"  ✓ 已连接到 {device.name}")
            print(f"  等待扫描数据... (在纸上滑动扫译笔)")

            # 自动发送握手应答
            if auto_handshake:
                await self._auto_handshake()

            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            print(f"  ✗ 连接失败: {e}")
            self._set_state(ConnectionState.DISCONNECTED)
            await self._client.disconnect()
            return False

    async def disconnect(self):
        """断开当前连接"""
        if self._client and self._client.is_connected:
            self._set_state(ConnectionState.DISCONNECTING)
            try:
                # 取消所有通知订阅
                for char_uuid in self._notify_chars:
                    try:
                        await self._client.stop_notify(char_uuid)
                    except Exception:
                        pass
                self._notify_chars.clear()
            finally:
                await self._client.disconnect()
                self._set_state(ConnectionState.DISCONNECTED)
                print("  已断开连接。")

    # ---- 服务发现与通知订阅 ----

    async def _discover_and_subscribe(self):
        """
        发现设备的全部 GATT 服务，尝试订阅所有可能的数据通知特征。

        关于 GATT 服务发现：
          连接建立后，需要"浏览"设备提供的所有服务。
          就像插入 U 盘后要等系统识别文件系统一样。
        """
        if not self._client:
            return

        logger.info("正在发现 GATT 服务...")

        # bleak 3.x: services 是自动获取的属性，不需要显式调用 get_services()
        services = self._client.services

        subscribe_candidates = []  # 候选通知特征列表
        write_candidates = []     # 候选可写特征列表

        for service in services:
            logger.debug(f"  服务: {service.uuid} ({service.description})")
            for char in service.characteristics:
                logger.debug(f"    特征: {char.uuid} "
                           f"props={char.properties} "
                           f"({char.description})")

                # 检查特征的属性(properties)
                # 我们关心的属性：
                #   "notify" — 设备可以主动推送数据
                #   "indicate" — 类似 notify，但需要确认
                props = char.properties

                if "notify" in props or "indicate" in props:
                    subscribe_candidates.append(char)

                if "write" in props:
                    write_candidates.append(char)

        if not subscribe_candidates:
            logger.warning("未找到任何可通知的特征！")
            print("  ⚠ 未找到数据通道，设备可能不是扫译笔或不支持标准协议")
            self._print_service_tree(services)
            return

        logger.info(f"找到 {len(subscribe_candidates)} 个可通知特征")

        # 按优先级排序：NUS RX > EE 数据 > AE 数据 > 其他
        priority_uuids = [
            NUS_CHAR_RX_UUID.lower(),
            NUS_ALT_CHAR_RX_UUID.lower(),
            EE_CHAR_DATA1_UUID.lower(),
            EE_CHAR_DATA2_UUID.lower(),
            AE_CHAR_1_UUID.lower(),
            AE_CHAR_2_UUID.lower(),
            F1_CHAR_1_UUID.lower(),
            F1_CHAR_2_UUID.lower(),
        ]

        def _priority(char) -> int:
            try:
                return priority_uuids.index(char.uuid.lower())
            except ValueError:
                return 999

        subscribe_candidates.sort(key=_priority)

        # 订阅所有候选特征的通知
        # （可能有多个通道，都订阅不会有害处）
        subscribed_count = 0
        for char in subscribe_candidates:
            try:
                await self._client.start_notify(char, self._on_notification)
                self._notify_chars.append(char.uuid)
                subscribed_count += 1
                logger.info(f"  ✓ 已订阅: {char.uuid} ({char.description})")
            except Exception as e:
                logger.warning(f"  ✗ 订阅失败: {char.uuid} — {e}")

        if subscribed_count == 0:
            print("  ⚠ 无法订阅任何通知特征")
        else:
            print(f"  ✓ 已订阅 {subscribed_count} 个数据通道")
            for uuid in self._notify_chars:
                print(f"    - {uuid}")

        # 保存可写特征（按优先级排序：NUS TX > ALT TX > 其他）
        tx_priority = [
            NUS_CHAR_TX_UUID.lower(),
            NUS_ALT_CHAR_TX_UUID.lower(),
        ]
        def _tx_priority(char) -> int:
            try:
                return tx_priority.index(char.uuid.lower())
            except ValueError:
                return 999
        write_candidates.sort(key=_tx_priority)
        self._write_chars = [c.uuid for c in write_candidates]
        if self._write_chars:
            print(f"  ✓ 发现 {len(self._write_chars)} 个命令通道")
            for uuid in self._write_chars:
                print(f"    - {uuid}")

    def _print_service_tree(self, services):
        """打印完整的 GATT 服务树（调试用）"""
        print("  设备 GATT 服务树:")
        for service in services:
            print(f"    服务: {service.uuid}")
            for char in service.characteristics:
                print(f"      特征: {char.uuid} props={char.properties}")
                for desc in char.descriptors:
                    print(f"        描述符: {desc.uuid}")

    # ---- 握手协议 ----
    # 2026-07-15: jadx 反编译 APK 确认的真实协议
    # 来源: scan/vm/a.java → onMarkerConnectSuccess()
    #       protocol/r0.java (UpdateMarkerSystemTime)
    #       protocol/j0.java (SetResetStatus)
    #       protocol/l0.java (SetMarkerSyncStatus)

    # ── 命令字节常量 (来自 protocol/h.java EverMarkerCommand.kt) ──
    CMD_UPDATE_SYSTEM_TIME  = 0x6E  # h.n0 → r0.java
    CMD_SET_RESET_STATUS    = 0x91  # h.j0 → j0.java
    CMD_SET_SYNC_STATUS     = 0x84  # h.h0 → l0.java
    CMD_REQUEST_SYNC_DATA   = 0x61  # h.v  → y.java (批量同步请求)
    CMD_REQUEST_REALTIME    = 0x86  # h.u  → x.java (实时数据请求)
    CMD_DELETE_SYNCED       = 0x83  # h.e  → g.java (同步完成/删除确认)
    CMD_BATTERY_QUERY       = 0x64  # h.q  → t.java

    # ── 帧工具 ──

    @staticmethod
    def _make_frame(command: int, payload: bytes = b"") -> bytes:
        """构造 EverMarker 二进制帧: [A0][cmd][len][payload]"""
        return bytes([0xA0, command, len(payload)]) + payload

    @staticmethod
    def _parse_response(data: bytes):
        """解析笔的响应帧。返回 (command_byte, payload_bytes)。"""
        if len(data) >= 3 and data[0] == 0xA0:
            cmd = data[1]
            length = data[2] & 0xFF
            end = 3 + length
            payload = data[3:end] if len(data) >= end else data[3:]
            return cmd, payload
        return None, None

    async def _send_cmd_and_wait(self, command: int, payload: bytes = b"",
                                  timeout: float = 2.0) -> tuple:
        """发送命令并等待匹配响应。返回 (success: bool, payload: bytes|None)。"""
        import asyncio as aio

        frame = self._make_frame(command, payload)
        response_data = []

        orig_callback = self.on_raw_data
        loop = aio.get_event_loop()
        response_event = aio.Event()

        def _catch(data: bytes):
            response_data.append(data)
            response_event.set()
            if orig_callback:
                orig_callback(data)

        self.on_raw_data = _catch
        try:
            await self.send_command(frame)
            await aio.wait_for(response_event.wait(), timeout=timeout)
            if response_data:
                cmd, pld = self._parse_response(response_data[0])
                if cmd == command:
                    ok = len(pld) >= 1 and pld[0] == 0x00
                    return (ok, pld)
                return (False, pld)
        except aio.TimeoutError:
            pass
        finally:
            self.on_raw_data = orig_callback

        return (False, None)

    # ── 初始化握手 ──

    async def init_handshake(self) -> bool:
        """
        执行 jadx 逆向确认的初始化握手。
        序列: UpdateMarkerSystemTime → SetResetStatus(false)
        来源: scan/vm/a.java onMarkerConnectSuccess()
        """
        import asyncio as aio
        import time

        print("  🤝 初始化握手 (jadx 逆向协议)")
        print("  ──────────────────────────────")

        # 步骤 1: 同步系统时间
        # rm.j0(System.currentTimeMillis()) → handler: r0.java
        # 帧: A0 6E [len] [timestamp_ascii]
        now_ms = int(time.time() * 1000)
        ts_bytes = str(now_ms).encode('ascii')
        print(f"  [1/2] UpdateMarkerSystemTime: {now_ms}")
        ok, pld = await self._send_cmd_and_wait(self.CMD_UPDATE_SYSTEM_TIME, ts_bytes)
        if ok:
            print(f"  ✓ 时间同步成功")
        else:
            info = pld.hex() if pld else '无响应'
            print(f"  ⚠ 时间同步: {info} (继续...)")

        await aio.sleep(0.3)

        # 步骤 2: 清除重置状态
        # rm.g0(false) → handler: j0.java
        # 帧: A0 91 01 00
        print(f"  [2/2] SetResetStatus: false")
        ok, pld = await self._send_cmd_and_wait(self.CMD_SET_RESET_STATUS, b'\x00')
        if ok:
            print(f"  ✓ 重置状态已清除")
        else:
            info = pld.hex() if pld else '无响应'
            print(f"  ⚠ 重置状态: {info} (继续...)")

        print(f"  ──────────────────────────────")
        print(f"  ✓ 握手完成")
        return True

    # ── 数据请求 ──

    async def request_sync_data(self, book_uuid: str = "1111-1111-1111-1111"):
        """请求批量同步数据 (0x61)"""
        payload = book_uuid.encode('ascii')[:19]
        print(f"  📥 请求同步 (UUID={book_uuid})...")
        return await self._send_cmd_and_wait(self.CMD_REQUEST_SYNC_DATA, payload)

    async def request_realtime_data(self, book_uuid: str = "1111-1111-1111-1111"):
        """请求实时扫描数据 (0x86)"""
        payload = book_uuid.encode('ascii')[:19]
        print(f"  📥 请求实时数据 (UUID={book_uuid})...")
        return await self._send_cmd_and_wait(self.CMD_REQUEST_REALTIME, payload)

    async def set_sync_status(self, syncing: bool = True):
        """设置同步状态 (0x84)"""
        payload = b'\x01' if syncing else b'\x00'
        return await self._send_cmd_and_wait(self.CMD_SET_SYNC_STATUS, payload)

    # ── 旧版兼容 ──

    async def probe_protocol(self):
        """[已废弃] 保留用于调试未知协议变体。"""
        print("  ⚠ probe_protocol() 已废弃。使用 init_handshake() 代替。")

    async def _auto_handshake(self):
        """连接时自动调用 init_handshake()。"""
        import asyncio as aio
        await aio.sleep(0.3)
        try:
            await self.init_handshake()
        except Exception as e:
            print(f"  ⚠ 握手异常: {e}")

    # ---- 数据接收 ----

    async def _on_notification(self, characteristic, data: bytearray):
        """
        BLE 通知回调——设备有数据过来时触发。

        这是驱动的核心！每当笔扫描到文字并发送过来时，
        这个函数被调用。

        参数:
            characteristic: BleakGATTCharacteristic 对象
            data: 原始数据字节 (bytearray，兼容 bytes 操作)
        """
        data_bytes = bytes(data)  # bytearray → bytes
        logger.debug(f"收到数据 [{len(data_bytes)}B] from {characteristic.uuid}: {data_bytes.hex()[:100]}")

        # 1. 调用原始数据回调（用于调试和协议分析）
        if self.on_raw_data:
            try:
                self.on_raw_data(data_bytes)
            except Exception as e:
                logger.error(f"原始数据回调异常: {e}")

        # 2. 尝试解析文本
        try:
            text = self._extract_text(data_bytes)
            if text:
                self._text_buffer += text

                # 检查是否有完整的句子分隔符
                if any(sep in self._text_buffer for sep in ['\n', '\r', '。', '！', '？', '.', '!', '?']):
                    # 输出累积的文本
                    full_text = self._text_buffer.strip()
                    self._text_buffer = ""
                    if full_text:
                        logger.info(f"扫描文本: {full_text}")
                        if self.on_text_received:
                            self.on_text_received(full_text)
        except Exception as e:
            logger.error(f"文本解析异常: {e}")

    def _extract_text(self, data: bytes) -> str:
        """
        从原始数据中提取文本。

        策略（基于 APK 分析推断的协议格式）：

        1. 先尝试 UTF-8 解码整个包——最简单的格式
        2. 如果失败，尝试常见协议帧格式：
           - 跳过帧头(2B) → 读取长度(2B) → 跳过类型(1B) → 提取文本(UTF-8)
           - 跳过帧头(1B) → 跳过类型(1B) → 提取文本(UTF-8)
        3. 尝试 JSON 格式 {"type":"text","data":"..."}
        4. 提取所有可打印的 UTF-8 片段

        返回:
            提取到的文本字符串（可能为空）
        """
        # 策略 1: 直接 UTF-8 解码
        try:
            decoded = data.decode('utf-8')
            if self._looks_like_text(decoded):
                return decoded
        except UnicodeDecodeError:
            pass

        # 策略 2: 尝试协议帧格式
        # 格式 A: [header 2B][len 2B LE][type 1B][payload...][checksum 1B]
        if len(data) >= 5:
            try:
                data_len = int.from_bytes(data[2:4], 'little')
                if 0 < data_len <= len(data) - 5:
                    payload = data[4:4+data_len]
                    decoded = payload.decode('utf-8')
                    if self._looks_like_text(decoded):
                        return decoded
            except (UnicodeDecodeError, IndexError):
                pass

        # 格式 B: [header 1B][type 1B][payload...]
        if len(data) >= 3:
            try:
                payload = data[2:]
                decoded = payload.decode('utf-8')
                if self._looks_like_text(decoded):
                    return decoded
            except UnicodeDecodeError:
                pass

        # 策略 3: JSON 格式
        try:
            import json
            obj = json.loads(data.decode('utf-8'))
            if isinstance(obj, dict):
                for key in ['data', 'text', 'content', 'result', 'msg']:
                    if key in obj and isinstance(obj[key], str):
                        return obj[key]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError):
            pass

        # 策略 4: 提取可打印片段
        try:
            text = data.decode('utf-8', errors='ignore')
            # 只保留看起来像自然语言的片段（至少包含中英文）
            import re
            # 提取连续的可读字符段
            pieces = re.findall(r'[一-鿿　-〿＀-￯a-zA-Z0-9\s.,!?;:，。！？；：、""''（）\[\]{}…—\-\+]+', text)
            if pieces:
                longest = max(pieces, key=len)
                if len(longest) >= 2:  # 至少2个字符才算有效
                    return longest
        except Exception:
            pass

        return ""

    @staticmethod
    def _looks_like_text(s: str) -> bool:
        """判断字符串是否像自然语言文本（而非二进制乱码）"""
        if len(s) < 2:
            return False
        # 检查是否包含中文字符或合理的英文文本
        import re
        chinese_chars = len(re.findall(r'[一-鿿]', s))
        ascii_chars = len(re.findall(r'[a-zA-Z0-9\s.,!?;:]', s))
        total = len(s)
        # 至少 50% 是可读字符
        return (chinese_chars + ascii_chars) / total > 0.5

    # ---- 发送命令（用于后续扩展） ----

    async def send_command(self, data: bytes):
        """
        向设备发送命令。

        参数:
            data: 要发送的字节数据
        """
        if not self._client or not self._client.is_connected:
            logger.warning("未连接，无法发送命令")
            return False

        # 优先使用已发现的可写特征
        for uuid in self._write_chars:
            try:
                await self._client.write_gatt_char(uuid, data)
                logger.info(f"已发送 {len(data)}B → {uuid}: {data.hex()}")
                return True
            except Exception as e:
                logger.debug(f"写入 {uuid} 失败: {e}")

        # 回退：尝试已知的 NUS TX UUID
        for uuid in [NUS_ALT_CHAR_TX_UUID, NUS_CHAR_TX_UUID]:
            try:
                await self._client.write_gatt_char(uuid, data)
                logger.info(f"已发送 {len(data)}B → {uuid}: {data.hex()}")
                return True
            except Exception:
                pass

        logger.warning("未找到可写的命令特征")
        return False
