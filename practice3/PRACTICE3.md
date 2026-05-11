# Практика 3. Контейнеризация и деплой микросервисов в Kubernetes

## Цель работы (по методичке)

1. Упаковать микросервисы из практики 2 в Docker-образы.
2. Развернуть приложение в Minikube.
3. Использовать базовые объекты K8s: `Deployment`, `Service`, `Ingress`, `ConfigMap`, `Secret`.
4. Подтвердить работоспособность API через ingress.

## Состав развертываемых компонентов

- `gateway` (`gateway:latest`)
- `booking-service` (`booking-service:latest`)
- `postgres` (`postgres:16-alpine`)
- `redis` (`redis:7-alpine`)

## Структура манифестов

- Единый манифест: `k8s/all-in-one.yaml`
- Отдельные файлы (для удобства проверки):
  - `k8s/deployment-gateway.yaml`
  - `k8s/deployment-booking-service.yaml`
  - `k8s/service-gateway.yaml`
  - `k8s/service-booking-service.yaml`
  - `k8s/ingress.yaml`

## Ход работы

### Шаг 1. Подготовка Minikube

```bash
minikube start --driver=docker
minikube addons enable ingress
```

### Шаг 2. Сборка и загрузка образов

```bash
docker build -t gateway:latest ../practice2/services/gateway
docker build -t booking-service:latest ../practice2/services/booking_service
minikube image load gateway:latest
minikube image load booking-service:latest
```

### Шаг 3. Применение манифестов

```bash
kubectl apply -f k8s/all-in-one.yaml
```

### Шаг 4. Проверка готовности

```bash
kubectl wait --for=condition=available deployment/postgres deployment/redis deployment/booking-service deployment/gateway --timeout=240s
kubectl get pods,svc,ingress
```

### Шаг 5. Проверка ingress

```bash
minikube tunnel
```

Отдельно:

```bash
curl -H "Host: myapp.local" http://127.0.0.1/health
curl -H "Host: myapp.local" http://127.0.0.1/api/rooms
```

## Ожидаемый результат

- Все pod в состоянии `Running`.
- Ingress `booking-ingress` активен.
- Эндпоинты API доступны через ingress и возвращают валидный ответ.

## Диагностика при ошибках

```bash
kubectl get pods -o wide
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```
