# Практики 9-12: веб-приложение для бронирования переговорок

Этот репозиторий содержит полный цикл практических работ по методичке:
- Практика 1: архитектурное проектирование в нотации C4.
- Практика 2: MVP на микросервисах с автотестами и frontend на React.
- Практика 3: контейнеризация и деплой в Kubernetes (Minikube).
- Практика 4: мониторинг и наблюдаемость в Kubernetes.

## Структура проекта

- `practice1/` - C4-диаграммы, Problem Statement, критический анализ ИИ-генерации.
- `practice2/` - код микросервисов, frontend, тесты, `docker-compose.yml`.
- `practice3/` - Kubernetes-манифесты и отчет по деплою.
- `practice4/` - конфигурации мониторинга, дашборд, нагрузочный скрипт.
- `FINAL_REPORT.md` - итоговый объединенный отчет.

## Быстрый старт (локально через Docker)

```bash
cd practice2
docker compose up -d --build
```

После запуска:
- Frontend: `http://localhost:3000`
- API Gateway: `http://localhost:8000`
- Swagger API Gateway: `http://localhost:8000/docs`

Остановка:

```bash
cd practice2
docker compose down
```

## Быстрый старт (Kubernetes / Minikube)

```bash
minikube start --driver=docker
minikube addons enable ingress
```

Сборка и загрузка образов:

```bash
docker build -t gateway:latest practice2/services/gateway
docker build -t booking-service:latest practice2/services/booking_service
minikube image load gateway:latest
minikube image load booking-service:latest
```

Деплой:

```bash
kubectl apply -f practice3/k8s/all-in-one.yaml
minikube tunnel
```

Проверка:

```bash
kubectl get pods,svc,ingress
curl -H "Host: myapp.local" http://127.0.0.1/health
curl -H "Host: myapp.local" http://127.0.0.1/api/rooms
```

## Автотесты

```bash
pip install -r practice2/requirements-test.txt
pytest practice2/tests -q
```

## Использованный стек

- Backend: Python, FastAPI, SQLAlchemy
- Data: PostgreSQL, Redis
- Frontend: React + Vite, темная UI-тема
- Infra: Docker, Docker Compose, Kubernetes, Minikube, Ingress
- Monitoring: Prometheus + Grafana
