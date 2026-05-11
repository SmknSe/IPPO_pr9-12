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

- Единый манифест без Secret: `k8s/all-in-one.yaml` (Secret создаётся отдельно из шаблона).
- Шаблон секретов (в репозитории): `k8s/booking-secrets.yaml.example` → скопируйте в `k8s/booking-secrets.yaml` (локальный файл в `.gitignore`) и задайте значения.
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
copy k8s\booking-secrets.yaml.example k8s\booking-secrets.yaml
# отредактируйте k8s/booking-secrets.yaml
kubectl apply -f k8s/booking-secrets.yaml
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

### Сообщение вида «error validating data: failed to download openapi»

`kubectl apply` (в том числе с `--dry-run=client`) в новых версиях клиента обращается к API Kubernetes за схемой OpenAPI. Если **minikube не запущен** или в `kubectl config` указан недоступный кластер (например, старый порт `127.0.0.1:...`), команда падает с ошибкой про **openapi**, хотя манифесты при этом могут быть корректными.

Что сделать:

1. Запустить кластер: `minikube start`
2. Убедиться в контексте: `kubectl config use-context minikube`
3. Повторить: `kubectl apply -f k8s/all-in-one.yaml`

Если нужно только проверить синтаксис YAML без кластера, используйте отдельный валидатор (например, [kubeconform](https://github.com/yannh/kubeconform)) или временно отключите обращение к серверу, задав рабочий `KUBECONFIG` к доступному кластеру.

В манифестах значения URL в `ConfigMap` и `DATABASE_URL` в `Deployment` заданы в **кавычках**, чтобы YAML-парсер не спутал двоеточия в строках с синтаксисом мапы.
