# Monitoring Stack - Prometheus + Grafana

## Installation

Prometheus와 Grafana 모니터링 스택이 k3d 클러스터(atlas-trading)에 설치되었습니다.

### 설치된 컴포넌트

- **Prometheus**: 메트릭 수집 및 저장
- **Grafana**: 시각화 대시보드
- **AlertManager**: 알림 관리
- **Node Exporter**: 노드 메트릭 수집
- **Kube State Metrics**: Kubernetes 리소스 메트릭

### 네임스페이스

```bash
monitoring
```

## 접근 방법

### Grafana 대시보드

Grafana는 NodePort를 통해 Tailscale 네트워크에서 접근 가능합니다.

**접속 URL (Tailscale 네트워크):**
```
http://100.110.86.86:31177
```

또는 로컬 네트워크:
```
http://172.30.1.61:31177
```

**로그인 정보:**
- Username: `admin`
- Password: 초기 배포 시 설정한 값 (내부 문서 참조)

### Prometheus UI

Prometheus는 ClusterIP로 실행됩니다. 접근하려면 포트 포워딩 사용:

```bash
ssh atlas
source ~/.zshrc
kubectl --namespace monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
```

그 후 `http://localhost:9090`에서 접근

### AlertManager UI

AlertManager도 ClusterIP로 실행됩니다. 포트 포워딩:

```bash
ssh atlas
source ~/.zshrc
kubectl --namespace monitoring port-forward svc/kube-prometheus-stack-alertmanager 9093:9093
```

그 후 `http://localhost:9093`에서 접근

## 주요 대시보드

Grafana에 사전 구성된 대시보드:

1. **Kubernetes / Compute Resources / Cluster**
   - 클러스터 전체 CPU, 메모리, 네트워크 사용량

2. **Kubernetes / Compute Resources / Namespace (Pods)**
   - 네임스페이스별 Pod 리소스 사용량

3. **Node Exporter / Nodes**
   - 노드 시스템 메트릭 (CPU, 메모리, 디스크, 네트워크)

4. **Kubernetes / Kubelet**
   - Kubelet 성능 메트릭

## 리소스 설정

### Prometheus
- Retention: 15일
- Storage: 10Gi PVC

### Grafana
- Persistence: 5Gi PVC
- Service: NodePort (31177)

## 모니터링 스택 관리

### Pod 상태 확인

```bash
ssh atlas
source ~/.zshrc
kubectl --namespace monitoring get pods
```

### 서비스 확인

```bash
kubectl --namespace monitoring get svc
```

### 로그 확인

```bash
# Prometheus 로그
kubectl --namespace monitoring logs -l app.kubernetes.io/name=prometheus

# Grafana 로그
kubectl --namespace monitoring logs -l app.kubernetes.io/name=grafana

# AlertManager 로그
kubectl --namespace monitoring logs -l app.kubernetes.io/name=alertmanager
```

### 재시작

```bash
# Grafana 재시작
kubectl --namespace monitoring rollout restart deployment kube-prometheus-stack-grafana

# Prometheus Operator 재시작
kubectl --namespace monitoring rollout restart deployment kube-prometheus-stack-operator
```

### 삭제 (필요시)

```bash
helm uninstall kube-prometheus-stack --namespace monitoring
kubectl delete namespace monitoring
```

## 커스터마이징

Helm values 파일 위치: `/tmp/prometheus-values.yaml` (Mac Mini)

설정 변경 후 업그레이드:

```bash
ssh atlas
source ~/.zshrc
helm upgrade kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values /tmp/prometheus-values.yaml
```

## 보안 고려사항

- Grafana는 Tailscale 네트워크 내에서만 접근 가능 (172.30.1.61)
- 외부 인터넷에서 직접 접근 불가
- 초기 비밀번호를 변경하려면 Grafana UI에서 Profile > Change Password

## 다음 단계

1. Grafana에서 커스텀 대시보드 생성
2. AlertManager 알림 규칙 설정 (Slack, Discord 등)
3. Trading 애플리케이션 메트릭 추가
4. 장기 메트릭 보존을 위한 Thanos 설치 (선택)

## 트러블슈팅

### Grafana 접속 안 될 때

```bash
# Pod 상태 확인
kubectl --namespace monitoring get pods -l app.kubernetes.io/name=grafana

# 로그 확인
kubectl --namespace monitoring logs -l app.kubernetes.io/name=grafana

# 서비스 확인
kubectl --namespace monitoring get svc kube-prometheus-stack-grafana
```

### 메트릭이 수집되지 않을 때

```bash
# Prometheus 타겟 확인 (포트 포워딩 후)
# Prometheus UI > Status > Targets

# Node Exporter 상태 확인
kubectl --namespace monitoring get pods -l app.kubernetes.io/name=prometheus-node-exporter
```

### 스토리지 부족

```bash
# PVC 사용량 확인
kubectl --namespace monitoring get pvc

# Prometheus retention 줄이기 (values.yaml 수정 후 업그레이드)
```
