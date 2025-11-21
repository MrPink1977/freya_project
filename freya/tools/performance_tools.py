"""System performance monitoring tools for Freya."""

from __future__ import annotations

try:
    import psutil
except ImportError:
    psutil = None

from .base import FreyaTool, ToolResult


class PerformanceMonitorTool(FreyaTool):
    """Monitor system performance - CPU, memory, disk, network, GPU."""

    @property
    def name(self) -> str:
        return "performance_monitor"

    @property
    def description(self) -> str:
        return "Monitor system performance: CPU, RAM, disk usage, network, processes, and GPU (if available)"

    def execute(self, metric: str = "all") -> ToolResult:
        """Get system performance metrics.

        Args:
            metric: What to monitor - 'all', 'cpu', 'memory', 'disk', 'network', 'processes', 'gpu'

        Returns:
            ToolResult with performance data
        """
        if psutil is None:
            return ToolResult(
                success=False, output="", error="psutil not installed. Run: pip install psutil"
            )

        try:
            parts = []

            if metric in ("all", "cpu"):
                cpu_info = self._get_cpu_info()
                parts.append(cpu_info)

            if metric in ("all", "memory"):
                mem_info = self._get_memory_info()
                parts.append(mem_info)

            if metric in ("all", "disk"):
                disk_info = self._get_disk_info()
                parts.append(disk_info)

            if metric in ("all", "network"):
                net_info = self._get_network_info()
                parts.append(net_info)

            if metric in ("all", "processes"):
                proc_info = self._get_process_info()
                parts.append(proc_info)

            if metric in ("all", "gpu"):
                gpu_info = self._get_gpu_info()
                if gpu_info:
                    parts.append(gpu_info)

            output = "\n\n".join(parts) if parts else "No metrics available"

            return ToolResult(success=True, output=output)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Performance monitoring failed: {e}")

    @staticmethod
    def _get_cpu_info() -> str:
        """Get CPU usage information."""
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()

        info = "CPU Usage:\n"
        info += f"  Overall: {cpu_percent}%\n"
        info += f"  Cores: {cpu_count} logical CPUs\n"

        if cpu_freq:
            info += f"  Frequency: {cpu_freq.current:.0f} MHz (max: {cpu_freq.max:.0f} MHz)"

        # Per-core breakdown
        per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
        if len(per_cpu) <= 16:  # Only show if reasonable number of cores
            info += "\n  Per-core: "
            cores_str = ", ".join(f"{i}={p:.0f}%" for i, p in enumerate(per_cpu[:8]))
            info += cores_str
            if len(per_cpu) > 8:
                info += "..."

        return info

    @staticmethod
    def _get_memory_info() -> str:
        """Get memory usage information."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        total_gb = mem.total / (1024**3)
        used_gb = mem.used / (1024**3)
        available_gb = mem.available / (1024**3)

        info = "Memory (RAM):\n"
        info += f"  Total: {total_gb:.1f} GB\n"
        info += f"  Used: {used_gb:.1f} GB ({mem.percent}%)\n"
        info += f"  Available: {available_gb:.1f} GB\n"

        if swap.total > 0:
            swap_total_gb = swap.total / (1024**3)
            swap_used_gb = swap.used / (1024**3)
            info += "\nSwap:\n"
            info += f"  Total: {swap_total_gb:.1f} GB\n"
            info += f"  Used: {swap_used_gb:.1f} GB ({swap.percent}%)"

        return info

    @staticmethod
    def _get_disk_info() -> str:
        """Get disk usage information."""
        partitions = psutil.disk_partitions()

        info = "Disk Usage:\n"

        # Focus on main partitions
        for partition in partitions:
            # Skip special filesystems
            if partition.fstype in ("", "tmpfs", "devtmpfs", "squashfs"):
                continue

            try:
                usage = psutil.disk_usage(partition.mountpoint)
                total_gb = usage.total / (1024**3)
                used_gb = usage.used / (1024**3)
                free_gb = usage.free / (1024**3)

                mount = partition.mountpoint
                if mount == "/":
                    mount = "Root (C: equivalent)"
                elif len(mount) > 20:
                    mount = mount[:17] + "..."

                info += f"  {mount}:\n"
                info += f"    Total: {total_gb:.1f} GB\n"
                info += f"    Used: {used_gb:.1f} GB ({usage.percent}%)\n"
                info += f"    Free: {free_gb:.1f} GB\n"

            except PermissionError:
                continue

        return info

    @staticmethod
    def _get_network_info() -> str:
        """Get network statistics."""
        net_io = psutil.net_io_counters()

        sent_mb = net_io.bytes_sent / (1024**2)
        recv_mb = net_io.bytes_recv / (1024**2)

        info = "Network (since boot):\n"
        info += f"  Sent: {sent_mb:.1f} MB\n"
        info += f"  Received: {recv_mb:.1f} MB\n"
        info += f"  Packets sent: {net_io.packets_sent}\n"
        info += f"  Packets received: {net_io.packets_recv}"

        return info

    @staticmethod
    def _get_process_info() -> str:
        """Get top processes by CPU and memory."""
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Sort by CPU usage
        processes.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
        top_cpu = processes[:5]

        # Sort by memory usage
        processes.sort(key=lambda x: x.get("memory_percent", 0) or 0, reverse=True)
        top_mem = processes[:5]

        info = "Top 5 Processes (CPU):\n"
        for proc in top_cpu:
            name = proc.get("name", "Unknown")[:25]
            cpu = proc.get("cpu_percent", 0) or 0
            info += f"  {name}: {cpu:.1f}% CPU\n"

        info += "\nTop 5 Processes (Memory):\n"
        for proc in top_mem:
            name = proc.get("name", "Unknown")[:25]
            mem = proc.get("memory_percent", 0) or 0
            info += f"  {name}: {mem:.1f}% RAM"
            if proc != top_mem[-1]:
                info += "\n"

        return info

    @staticmethod
    def _get_gpu_info() -> str | None:
        """Get GPU information (NVIDIA only via pynvml)."""
        try:
            import pynvml

            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()

            if device_count == 0:
                return None

            info = "GPU Information:\n"

            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

                total_gb = mem_info.total / (1024**3)
                used_gb = mem_info.used / (1024**3)

                info += f"  GPU {i}: {name}\n"
                info += f"    Utilization: {utilization.gpu}%\n"
                info += (
                    f"    Memory: {used_gb:.1f}/{total_gb:.1f} GB ({(used_gb/total_gb)*100:.0f}%)\n"
                )
                info += f"    Temperature: {temp}°C"

                if i < device_count - 1:
                    info += "\n"

            pynvml.nvmlShutdown()
            return info

        except (ImportError, Exception):
            # GPU monitoring not available
            return None


__all__ = ["PerformanceMonitorTool"]
