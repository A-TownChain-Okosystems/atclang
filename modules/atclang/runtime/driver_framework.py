# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Driver Framework — Python Runtime Stub
=================================================
Version: 1.0.0-alpha | ATC-22+ | Sprint 3.1

Python-Implementierung des Treiber Layers für Tests.
Entspricht modules/kernel/drivers/driver_framework.atc
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import IntEnum


class DriverState(IntEnum):
    UNREGISTERED = 0
    LOADED = 1
    INITIALIZED = 2
    ACTIVE = 3
    SUSPENDED = 4
    ERROR = 5
    UNLOADING = 6


class DeviceClass(IntEnum):
    DISPLAY = 0
    INPUT = 1
    STORAGE = 2
    NETWORK = 3
    AUDIO = 4
    SERIAL = 5
    TIMER = 6
    INTERRUPT = 7
    BUS = 8
    CRYPTO = 9
    POWER = 10
    SENSOR = 11
    CUSTOM = 12


class BusType(IntEnum):
    PCI = 0
    USB = 1
    I2C = 2
    SPI = 3
    UART = 4
    ISA = 5
    MMIO = 6
    PORTIO = 7
    VIRTUAL = 8


class IoctlCode(IntEnum):
    GET_INFO = 0
    SET_MODE = 1
    RESET = 2
    FLUSH = 3
    GET_STATUS = 4
    SET_POWER = 5
    DMA_SETUP = 6
    IRQ_ENABLE = 7
    IRQ_DISABLE = 8
    CUSTOM = 9


class PowerState(IntEnum):
    ON = 0
    IDLE = 1
    STANDBY = 2
    OFF = 3


@dataclass
class DeviceInfo:
    device_id: int = 0
    device_class: DeviceClass = DeviceClass.CUSTOM
    bus: BusType = BusType.VIRTUAL
    vendor_id: int = 0
    product_id: int = 0
    bus_address: int = 0
    irq_line: int = 0xFF
    mmio_base: int = 0
    mmio_size: int = 0
    port_base: int = 0
    dma_channel: int = 0xFF
    name: str = ""
    description: str = ""
    driver_id: int = 0


@dataclass
class DriverInfo:
    driver_id: int = 0
    name: str = ""
    version: str = ""
    device_class: DeviceClass = DeviceClass.CUSTOM
    supported_vendors: list = field(default_factory=list)
    state: DriverState = DriverState.UNREGISTERED
    init_fn: str = ""
    cleanup_fn: str = ""
    load_count: int = 0
    error_count: int = 0
    last_error: str = ""
    sandbox_id: int = 0
    bound_devices: list = field(default_factory=list)
    gas_per_io: int = 10


@dataclass
class IRQRoute:
    irq_line: int = 0
    device_id: int = 0
    driver_id: int = 0
    handler_fn: str = ""
    priority: int = 0
    enabled: bool = True
    trigger_count: int = 0


@dataclass
class OpenHandle:
    handle_id: int = 0
    device_id: int = 0
    driver_id: int = 0
    flags: int = 0
    owner_pid: int = 0
    position: int = 0
    is_blocking: bool = True
    ref_count: int = 0


class DriverRegistry:
    """Python Runtime für den ATCLang Driver Framework Contract."""

    def __init__(self):
        self.drivers: Dict[int, DriverInfo] = {}
        self.devices: Dict[int, DeviceInfo] = {}
        self.open_handles: Dict[int, OpenHandle] = {}
        self.irq_routes: Dict[int, IRQRoute] = {}
        self.next_driver_id = 1
        self.next_device_id = 1
        self.next_handle_id = 1
        self.total_io_ops = 0
        self.total_errors = 0
        self.events: list = []

    # ═══════════════════════════════════════════════════════════
    #  DRIVER MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    def register_driver(self, name, version, device_class, supported_vendors,
                        init_fn, cleanup_fn, gas_per_io=10):
        """Treiber registrieren → driver_id"""
        did = self.next_driver_id
        self.next_driver_id += 1
        driver = DriverInfo(
            driver_id=did, name=name, version=version,
            device_class=DeviceClass(device_class),
            supported_vendors=list(supported_vendors),
            state=DriverState.LOADED,
            init_fn=init_fn, cleanup_fn=cleanup_fn,
            load_count=1, gas_per_io=gas_per_io,
        )
        self.drivers[did] = driver
        self.events.append(("DriverRegistered", did, name))
        return did

    def init_driver(self, driver_id):
        """Treiber initialisieren → bool"""
        driver = self.drivers.get(driver_id)
        if not driver:
            raise ValueError(f"driver {driver_id} not found")
        if driver.state != DriverState.LOADED:
            raise ValueError(f"driver not in LOADED state (was {driver.state})")
        driver.sandbox_id = driver_id * 1000 + 1
        driver.state = DriverState.INITIALIZED
        return True

    def activate_driver(self, driver_id):
        """Treiber aktivieren → bool"""
        driver = self.drivers.get(driver_id)
        if not driver:
            raise ValueError(f"driver {driver_id} not found")
        if driver.state not in (DriverState.INITIALIZED, DriverState.SUSPENDED):
            raise ValueError(f"driver not initialized (state={driver.state})")
        driver.state = DriverState.ACTIVE
        for did in driver.bound_devices:
            dev = self.devices.get(did)
            if dev:
                dev.driver_id = driver_id
        return True

    def unload_driver(self, driver_id, reason=""):
        """Treiber entladen → bool"""
        driver = self.drivers.get(driver_id)
        if not driver:
            raise ValueError(f"driver {driver_id} not found")
        for did in driver.bound_devices:
            dev = self.devices.get(did)
            if dev:
                dev.driver_id = 0
                self.events.append(("DeviceUnbound", did, driver_id))
        driver.state = DriverState.UNLOADING
        self.events.append(("DriverUnloaded", driver_id, reason))
        return True

    def get_driver_info(self, driver_id):
        return self.drivers.get(driver_id)

    def list_drivers_by_class(self, device_class):
        return [did for did, d in self.drivers.items()
                if d.device_class == DeviceClass(device_class) and d.state == DriverState.ACTIVE]

    # ═══════════════════════════════════════════════════════════
    #  DEVICE MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    def enumerate_device(self, device_class, bus, vendor_id, product_id,
                         bus_address=0, irq_line=0xFF, mmio_base=0, mmio_size=0,
                         port_base=0, name="", description=""):
        """Gerät enumerieren → device_id"""
        did = self.next_device_id
        self.next_device_id += 1
        device = DeviceInfo(
            device_id=did, device_class=DeviceClass(device_class),
            bus=BusType(bus), vendor_id=vendor_id, product_id=product_id,
            bus_address=bus_address, irq_line=irq_line,
            mmio_base=mmio_base, mmio_size=mmio_size,
            port_base=port_base, name=name, description=description,
        )
        self.devices[did] = device
        self.events.append(("DeviceEnumerated", did, name))
        return did

    def bind_driver(self, device_id, driver_id):
        """Treiber an Gerät binden → bool"""
        device = self.devices.get(device_id)
        driver = self.drivers.get(driver_id)
        if not device or not driver:
            raise ValueError("device or driver not found")
        if driver.state != DriverState.ACTIVE:
            raise ValueError("driver not active")
        if device.driver_id != 0:
            raise ValueError("device already bound")
        if driver.supported_vendors and device.vendor_id not in driver.supported_vendors:
            raise ValueError("vendor not supported")
        if driver.device_class != device.device_class:
            raise ValueError("device class mismatch")
        device.driver_id = driver_id
        driver.bound_devices.append(device_id)
        self.events.append(("DeviceBound", device_id, driver_id))
        return True

    def unbind_driver(self, device_id):
        """Treiber von Gerät trennen → bool"""
        device = self.devices.get(device_id)
        if not device or device.driver_id == 0:
            raise ValueError("no driver bound")
        driver_id = device.driver_id
        device.driver_id = 0
        self.events.append(("DeviceUnbound", device_id, driver_id))
        return True

    def get_device_info(self, device_id):
        return self.devices.get(device_id)

    def list_devices_by_class(self, device_class):
        return [did for did, d in self.devices.items()
                if d.device_class == DeviceClass(device_class)]

    def list_devices_by_bus(self, bus_type):
        return [did for did, d in self.devices.items()
                if d.bus == BusType(bus_type)]

    # ═══════════════════════════════════════════════════════════
    #  I/O INTERFACE
    # ═══════════════════════════════════════════════════════════

    def open(self, device_id, flags=3, owner_pid=0):
        """Gerät öffnen → handle_id"""
        device = self.devices.get(device_id)
        if not device:
            raise ValueError("device not found")
        if device.driver_id == 0:
            raise ValueError("no driver bound to device")
        driver = self.drivers.get(device.driver_id)
        if not driver or driver.state != DriverState.ACTIVE:
            raise ValueError("driver not active")
        # Exclusive check — if any existing handle is exclusive OR new handle is exclusive
        for h in self.open_handles.values():
            if h.device_id == device_id and h.ref_count > 0:
                if (flags & 0x08) or (h.flags & 0x08):
                    raise ValueError("device already opened exclusively")
        hid = self.next_handle_id
        self.next_handle_id += 1
        handle = OpenHandle(
            handle_id=hid, device_id=device_id, driver_id=device.driver_id,
            flags=flags, owner_pid=owner_pid,
            is_blocking=(flags & 0x04) == 0, ref_count=1,
        )
        self.open_handles[hid] = handle
        self.total_io_ops += 1
        self.events.append(("HandleOpened", hid, device_id, owner_pid))
        return hid

    def read(self, handle_id, buffer_size=4096):
        """Von Gerät lesen → str"""
        handle = self.open_handles.get(handle_id)
        if not handle:
            raise ValueError("handle not found")
        if not (handle.flags & 0x01):
            raise ValueError("handle not opened for reading")
        driver = self.drivers.get(handle.driver_id)
        if not driver or driver.state != DriverState.ACTIVE:
            raise ValueError("driver not active")
        self.total_io_ops += 1
        device = self.devices.get(handle.device_id)
        return self._dispatch_read(device, buffer_size)

    def write(self, handle_id, data):
        """Auf Gerät schreiben → bytes written"""
        handle = self.open_handles.get(handle_id)
        if not handle:
            raise ValueError("handle not found")
        if not (handle.flags & 0x02):
            raise ValueError("handle not opened for writing")
        driver = self.drivers.get(handle.driver_id)
        if not driver or driver.state != DriverState.ACTIVE:
            raise ValueError("driver not active")
        self.total_io_ops += 1
        device = self.devices.get(handle.device_id)
        return self._dispatch_write(device, data)

    def ioctl(self, handle_id, code, arg=0):
        """I/O-Control → u64"""
        handle = self.open_handles.get(handle_id)
        if not handle:
            raise ValueError("handle not found")
        driver = self.drivers.get(handle.driver_id)
        if not driver or driver.state != DriverState.ACTIVE:
            raise ValueError("driver not active")
        self.total_io_ops += 1
        code = IoctlCode(code)
        if code == IoctlCode.GET_INFO:
            return handle.device_id
        elif code == IoctlCode.GET_STATUS:
            return int(driver.state)
        elif code == IoctlCode.IRQ_ENABLE:
            device = self.devices.get(handle.device_id)
            if device and device.irq_line != 0xFF:
                route = self.irq_routes.get(device.irq_line)
                if route:
                    route.enabled = True
            return 0
        elif code == IoctlCode.IRQ_DISABLE:
            device = self.devices.get(handle.device_id)
            if device and device.irq_line != 0xFF:
                route = self.irq_routes.get(device.irq_line)
                if route:
                    route.enabled = False
            return 0
        return arg

    def close(self, handle_id):
        """Gerät schließen → bool"""
        handle = self.open_handles.get(handle_id)
        if not handle:
            raise ValueError("handle not found")
        handle.ref_count -= 1
        if handle.ref_count <= 0:
            del self.open_handles[handle_id]
        self.events.append(("HandleClosed", handle_id))
        return True

    def seek(self, handle_id, offset, whence=0):
        handle = self.open_handles.get(handle_id)
        if not handle:
            raise ValueError("handle not found")
        if whence == 0:
            handle.position = offset
        elif whence == 1:
            handle.position += offset
        else:
            handle.position = offset
        return handle.position

    # ═══════════════════════════════════════════════════════════
    #  IRQ MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    def register_irq(self, irq_line, device_id, driver_id, handler_fn, priority=128):
        if irq_line >= 255:
            raise ValueError("invalid IRQ line")
        route = IRQRoute(
            irq_line=irq_line, device_id=device_id, driver_id=driver_id,
            handler_fn=handler_fn, priority=priority, enabled=True,
        )
        self.irq_routes[irq_line] = route
        return True

    def trigger_irq(self, irq_line):
        route = self.irq_routes.get(irq_line)
        if not route:
            raise ValueError("IRQ not registered")
        if not route.enabled:
            raise ValueError("IRQ disabled")
        route.trigger_count += 1
        self.events.append(("IRQTriggered", irq_line, route.device_id))
        return True

    def unregister_irq(self, irq_line):
        if irq_line in self.irq_routes:
            del self.irq_routes[irq_line]
        return True

    # ═══════════════════════════════════════════════════════════
    #  DMA MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    def setup_dma(self, device_id, size):
        device = self.devices.get(device_id)
        if not device:
            raise ValueError("device not found")
        if device.dma_channel == 0xFF:
            ch = self._find_free_dma_channel(device_id)
            if ch == 0xFF:
                raise ValueError("no DMA channel available")
            device.dma_channel = ch
        transfer_id = self.next_driver_id * 10000 + device_id
        self.events.append(("DMATransferSetup", transfer_id, device_id))
        return transfer_id

    def _find_free_dma_channel(self, device_id):
        used = {d.dma_channel for did, d in self.devices.items() if did != device_id}
        for ch in range(8):
            if ch not in used:
                return ch
        return 0xFF

    # ═══════════════════════════════════════════════════════════
    #  POWER MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    def set_power_state(self, device_id, state):
        device = self.devices.get(device_id)
        if not device or device.driver_id == 0:
            raise ValueError("device not found or no driver")
        driver = self.drivers.get(device.driver_id)
        ps = PowerState(state)
        if ps in (PowerState.OFF, PowerState.STANDBY):
            if driver:
                driver.state = DriverState.SUSPENDED
        elif ps == PowerState.ON:
            if driver:
                driver.state = DriverState.ACTIVE
        self.events.append(("PowerStateChanged", device_id, state))
        return True

    # ═══════════════════════════════════════════════════════════
    #  INTERNAL DISPATCH
    # ═══════════════════════════════════════════════════════════

    def _dispatch_read(self, device, buffer_size):
        cls = device.device_class
        if cls == DeviceClass.DISPLAY:
            return "display_read_ok"
        elif cls == DeviceClass.INPUT:
            return "input_event"
        elif cls == DeviceClass.STORAGE:
            return "storage_data"
        elif cls == DeviceClass.NETWORK:
            return "network_packet"
        elif cls == DeviceClass.SERIAL:
            return "serial_data"
        elif cls == DeviceClass.AUDIO:
            return "audio_sample"
        return "unknown"

    def _dispatch_write(self, device, data):
        cls = device.device_class
        if cls == DeviceClass.INPUT:
            return 0  # Read-only
        return len(data)

    # ═══════════════════════════════════════════════════════════
    #  STATS
    # ═══════════════════════════════════════════════════════════

    def get_stats(self):
        return (
            len(self.drivers),
            len(self.devices),
            len(self.open_handles),
            self.total_io_ops,
            self.total_errors,
        )

    def report_error(self, driver_id, error):
        driver = self.drivers.get(driver_id)
        if driver:
            driver.error_count += 1
            driver.last_error = error
            self.total_errors += 1
            self.events.append(("DriverError", driver_id, error))
        return True
