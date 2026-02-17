# PowerMetrics Exporter for Prometheus

macOS 시스템 메트릭(CPU 온도, 전력 소비 등)을 Prometheus 형식으로 노출하는 exporter입니다.

## 기능

- **CPU 온도**: CPU die temperature
- **GPU 온도**: GPU die temperature
- **CPU 전력**: CPU 전력 소비 (mW)
- **GPU 전력**: GPU 전력 소비 (mW)
- **시스템 전력**: 총 시스템 전력 (CPU+GPU+ANE)
- **CPU 사용률**: Nominal frequency 대비 비율

## 설치

### 1. Python 3 설치 확인
```bash
python3 --version
```

### 2. 실행 권한 부여
```bash
chmod +x exporter.py
```

### 3. sudo 비밀번호 없이 실행 (선택)
powermetrics는 root 권한이 필요하므로, sudoers에 추가:

```bash
sudo visudo
```

다음 줄 추가:
```
jang-yeonghwan ALL=(ALL) NOPASSWD: /usr/bin/powermetrics
```

## 사용법

### 수동 실행
```bash
sudo python3 exporter.py --port 9101
```

### launchd 서비스로 실행 (자동 시작)

1. plist 파일 생성:
```bash
sudo tee /Library/LaunchDaemons/com.atlas.powermetrics-exporter.plist > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atlas.powermetrics-exporter</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/jang-yeonghwan/atlas-trading/monitoring/powermetrics-exporter/exporter.py</string>
        <string>--port</string>
        <string>9101</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/powermetrics-exporter.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/powermetrics-exporter.error.log</string>
</dict>
</plist>
EOF
```

2. 서비스 시작:
```bash
sudo launchctl load /Library/LaunchDaemons/com.atlas.powermetrics-exporter.plist
sudo launchctl start com.atlas.powermetrics-exporter
```

3. 상태 확인:
```bash
sudo launchctl list | grep powermetrics
```

## 엔드포인트

- **Metrics**: `http://localhost:9101/metrics`
- **Health**: `http://localhost:9101/health`

## Prometheus 설정

`prometheus.yml`에 추가:
```yaml
scrape_configs:
  - job_name: 'macos-powermetrics'
    static_configs:
      - targets: ['localhost:9101']
```

## 메트릭 예시

```
# HELP macos_cpu_temperature_celsius CPU die temperature in Celsius
# TYPE macos_cpu_temperature_celsius gauge
macos_cpu_temperature_celsius 45.5

# HELP macos_gpu_temperature_celsius GPU die temperature in Celsius
# TYPE macos_gpu_temperature_celsius gauge
macos_gpu_temperature_celsius 42.3

# HELP macos_cpu_power_milliwatts CPU power consumption in milliwatts
# TYPE macos_cpu_power_milliwatts gauge
macos_cpu_power_milliwatts 1234.5

# HELP macos_system_power_milliwatts Total system power (CPU+GPU+ANE) in milliwatts
# TYPE macos_system_power_milliwatts gauge
macos_system_power_milliwatts 3456.7
```

## 문제 해결

### "permission denied" 오류
- `sudo`로 실행했는지 확인
- sudoers에 powermetrics 추가 확인

### 메트릭이 0으로 표시됨
- powermetrics 명령어가 제대로 실행되는지 확인:
  ```bash
  sudo powermetrics --samplers smc,cpu_power,gpu_power -i 1000 -n 1
  ```

### 서비스가 시작되지 않음
- 로그 확인:
  ```bash
  cat /tmp/powermetrics-exporter.log
  cat /tmp/powermetrics-exporter.error.log
  ```
