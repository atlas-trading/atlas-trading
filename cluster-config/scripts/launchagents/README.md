# macOS LaunchAgents - Port Forwards

홈서버(Mac Mini) 재시작 후에도 port-forward가 자동으로 유지되도록 하는 LaunchAgent 설정 파일입니다.

## 서비스 목록

| 서비스 | 로컬 포트 | 대상 |
|--------|-----------|------|
| ArgoCD UI | 8081 | argocd/svc/argocd-server:80 |
| Grafana | 3000 | monitoring/svc/kube-prometheus-stack-grafana:80 |
| Ingress | 32660 | ingress-nginx/svc/ingress-nginx-controller:80 |

## 설치 방법 (최초 1회)

```bash
# plist 파일을 LaunchAgents 디렉토리에 복사
cp cluster-config/scripts/launchagents/*.plist ~/Library/LaunchAgents/

# 각 서비스 로드
launchctl load ~/Library/LaunchAgents/com.atlas-trading.argocd-portforward.plist
launchctl load ~/Library/LaunchAgents/com.atlas-trading.grafana-portforward.plist
launchctl load ~/Library/LaunchAgents/com.atlas-trading.ingress-portforward.plist
```

## 관리 명령어

```bash
# 상태 확인
launchctl list | grep atlas-trading

# 서비스 재시작
launchctl unload ~/Library/LaunchAgents/com.atlas-trading.argocd-portforward.plist
launchctl load   ~/Library/LaunchAgents/com.atlas-trading.argocd-portforward.plist

# 로그 확인
tail -f /tmp/argocd-portforward.log
tail -f /tmp/grafana-portforward.log
tail -f /tmp/ingress-portforward.log
```
