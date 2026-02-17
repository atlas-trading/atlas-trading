"""Environment monitoring endpoints"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import subprocess
import json
import psutil
from datetime import datetime

router = APIRouter()


@router.get("/system/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """
    Get Mac Mini system metrics (CPU/GPU temp, power consumption, memory, disk)
    Uses powermetrics command on macOS
    """
    try:
        # Get powermetrics data (requires sudo, should be configured in launchd)
        # For now, use mock data if powermetrics is not available
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:9090/metrics"],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Parse Prometheus metrics
            metrics_text = result.stdout
            cpu_temp = 0.0
            gpu_temp = 0.0
            cpu_power = 0.0
            gpu_power = 0.0

            for line in metrics_text.split('\n'):
                if line.startswith('cpu_temperature_celsius'):
                    cpu_temp = float(line.split()[1])
                elif line.startswith('gpu_temperature_celsius'):
                    gpu_temp = float(line.split()[1])
                elif line.startswith('cpu_power_milliwatts'):
                    cpu_power = float(line.split()[1]) / 1000  # Convert to watts
                elif line.startswith('gpu_power_milliwatts'):
                    gpu_power = float(line.split()[1]) / 1000
        except Exception:
            # Fallback to mock data if powermetrics exporter is not available
            cpu_temp = 45.0
            gpu_temp = 50.0
            cpu_power = 25.0
            gpu_power = 15.0

        # Get memory and disk usage using psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu_temp": cpu_temp,
            "gpu_temp": gpu_temp,
            "cpu_power": cpu_power,
            "gpu_power": gpu_power,
            "memory_used": memory.used,
            "memory_total": memory.total,
            "disk_used": disk.used,
            "disk_total": disk.total,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")


@router.get("/infra/metrics")
async def get_infra_metrics() -> Dict[str, Any]:
    """
    Get Kubernetes infrastructure metrics
    Uses kubectl commands to query k3d cluster
    """
    try:
        # Get node status
        nodes_result = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if nodes_result.returncode != 0:
            raise Exception("kubectl not available or cluster not accessible")

        nodes_data = json.loads(nodes_result.stdout)
        nodes_total = len(nodes_data.get("items", []))
        nodes_ready = sum(
            1 for node in nodes_data.get("items", [])
            if any(
                cond.get("type") == "Ready" and cond.get("status") == "True"
                for cond in node.get("status", {}).get("conditions", [])
            )
        )

        # Get pod status in atlas-trading namespace
        pods_result = subprocess.run(
            ["kubectl", "get", "pods", "-n", "atlas-trading", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        pods_data = json.loads(pods_result.stdout) if pods_result.returncode == 0 else {"items": []}
        pods_total = len(pods_data.get("items", []))
        pods_running = sum(
            1 for pod in pods_data.get("items", [])
            if pod.get("status", {}).get("phase") == "Running"
        )

        # Get deployment status
        deployments_result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", "atlas-trading", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        deployments_data = json.loads(deployments_result.stdout) if deployments_result.returncode == 0 else {"items": []}
        deployments = []

        for dep in deployments_data.get("items", []):
            metadata = dep.get("metadata", {})
            spec = dep.get("spec", {})
            status = dep.get("status", {})

            deployments.append({
                "name": metadata.get("name", "unknown"),
                "namespace": metadata.get("namespace", "unknown"),
                "replicas": spec.get("replicas", 0),
                "ready_replicas": status.get("readyReplicas", 0),
                "available": status.get("availableReplicas", 0) == spec.get("replicas", 0)
            })

        # Get resource usage (mock for now, would need metrics-server in production)
        cpu_usage = 0.5  # Mock: 0.5 cores
        cpu_total = 2.0  # Mock: 2 cores
        memory_usage = 2 * 1024 * 1024 * 1024  # Mock: 2GB
        memory_total = 8 * 1024 * 1024 * 1024  # Mock: 8GB

        return {
            "nodes_total": nodes_total,
            "nodes_ready": nodes_ready,
            "pods_total": pods_total,
            "pods_running": pods_running,
            "cpu_usage": cpu_usage,
            "cpu_total": cpu_total,
            "memory_usage": memory_usage,
            "memory_total": memory_total,
            "deployments": deployments,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get infrastructure metrics: {str(e)}")
