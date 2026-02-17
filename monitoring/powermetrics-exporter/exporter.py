#!/usr/bin/env python3
"""
PowerMetrics Exporter for Prometheus

Exports macOS system metrics (CPU temperature, power consumption, etc.)
in Prometheus format.

Usage:
    sudo python3 exporter.py --port 9101
"""

import subprocess
import re
import time
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional


class PowerMetrics:
    """Collects metrics from macOS powermetrics command"""

    def __init__(self):
        self.last_metrics = {}
        self.last_update = 0
        self.cache_duration = 5  # seconds

    def parse_powermetrics(self, output: str) -> Dict[str, float]:
        """Parse powermetrics output"""
        metrics = {}

        # CPU Temperature (e.g., "CPU die temperature: 45.5 C")
        temp_match = re.search(r'CPU die temperature:\s+([\d.]+)\s+C', output)
        if temp_match:
            metrics['cpu_temperature_celsius'] = float(temp_match.group(1))

        # GPU Temperature
        gpu_temp_match = re.search(r'GPU die temperature:\s+([\d.]+)\s+C', output)
        if gpu_temp_match:
            metrics['gpu_temperature_celsius'] = float(gpu_temp_match.group(1))

        # CPU Power (e.g., "CPU Power: 1234 mW")
        cpu_power_match = re.search(r'CPU Power:\s+([\d.]+)\s+mW', output)
        if cpu_power_match:
            metrics['cpu_power_milliwatts'] = float(cpu_power_match.group(1))

        # GPU Power
        gpu_power_match = re.search(r'GPU Power:\s+([\d.]+)\s+mW', output)
        if gpu_power_match:
            metrics['gpu_power_milliwatts'] = float(gpu_power_match.group(1))

        # System Power
        sys_power_match = re.search(r'Combined Power \(CPU \+ GPU \+ ANE\):\s+([\d.]+)\s+mW', output)
        if sys_power_match:
            metrics['system_power_milliwatts'] = float(sys_power_match.group(1))

        # CPU Usage (%)
        cpu_usage_match = re.search(r'CPU Average frequency as fraction of nominal:\s+([\d.]+)%', output)
        if cpu_usage_match:
            metrics['cpu_usage_percent'] = float(cpu_usage_match.group(1))

        return metrics

    def get_metrics(self) -> Dict[str, float]:
        """Get current metrics (with caching)"""
        now = time.time()

        # Return cached metrics if recent
        if now - self.last_update < self.cache_duration:
            return self.last_metrics

        try:
            # Run powermetrics for 1 sample
            result = subprocess.run(
                ['sudo', 'powermetrics', '--samplers', 'smc,cpu_power,gpu_power', '-i', '1000', '-n', '1'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.last_metrics = self.parse_powermetrics(result.stdout)
                self.last_update = now

        except subprocess.TimeoutExpired:
            print("ERROR: powermetrics command timed out")
        except Exception as e:
            print(f"ERROR: Failed to run powermetrics: {e}")

        return self.last_metrics


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint"""

    power_metrics = PowerMetrics()

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/metrics':
            self.serve_metrics()
        elif self.path == '/health':
            self.serve_health()
        else:
            self.send_error(404)

    def serve_metrics(self):
        """Serve metrics in Prometheus format"""
        metrics = self.power_metrics.get_metrics()

        # Build Prometheus response
        lines = [
            "# HELP macos_cpu_temperature_celsius CPU die temperature in Celsius",
            "# TYPE macos_cpu_temperature_celsius gauge",
            f"macos_cpu_temperature_celsius {metrics.get('cpu_temperature_celsius', 0)}",
            "",
            "# HELP macos_gpu_temperature_celsius GPU die temperature in Celsius",
            "# TYPE macos_gpu_temperature_celsius gauge",
            f"macos_gpu_temperature_celsius {metrics.get('gpu_temperature_celsius', 0)}",
            "",
            "# HELP macos_cpu_power_milliwatts CPU power consumption in milliwatts",
            "# TYPE macos_cpu_power_milliwatts gauge",
            f"macos_cpu_power_milliwatts {metrics.get('cpu_power_milliwatts', 0)}",
            "",
            "# HELP macos_gpu_power_milliwatts GPU power consumption in milliwatts",
            "# TYPE macos_gpu_power_milliwatts gauge",
            f"macos_gpu_power_milliwatts {metrics.get('gpu_power_milliwatts', 0)}",
            "",
            "# HELP macos_system_power_milliwatts Total system power (CPU+GPU+ANE) in milliwatts",
            "# TYPE macos_system_power_milliwatts gauge",
            f"macos_system_power_milliwatts {metrics.get('system_power_milliwatts', 0)}",
            "",
            "# HELP macos_cpu_usage_percent CPU usage as percentage of nominal frequency",
            "# TYPE macos_cpu_usage_percent gauge",
            f"macos_cpu_usage_percent {metrics.get('cpu_usage_percent', 0)}",
            "",
        ]

        response = '\n'.join(lines)

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4')
        self.end_headers()
        self.wfile.write(response.encode())

    def serve_health(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')

    def log_message(self, format, *args):
        """Override to reduce log noise"""
        pass  # Silent logging


def main():
    parser = argparse.ArgumentParser(description='PowerMetrics Exporter for Prometheus')
    parser.add_argument('--port', type=int, default=9101, help='Port to listen on (default: 9101)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MetricsHandler)
    print(f"PowerMetrics Exporter listening on {args.host}:{args.port}")
    print(f"Metrics endpoint: http://{args.host}:{args.port}/metrics")
    print("Note: Requires sudo privileges to run powermetrics")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
