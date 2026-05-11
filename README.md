# Практики 9-12: веб-приложение для бронирования переговорок

Этот репозиторий содержит полный цикл практических работ по методичке:

- Практика 1: архитектурное проектирование в нотации C4.
- Практика 2: MVP на микросервисах с автотестами и frontend на React.
- Практика 3: контейнеризация и деплой в Kubernetes (Minikube).
- Практика 4: мониторинг и наблюдаемость в Kubernetes.

## Структура проекта

- `practice1/` — C4-диаграммы, Problem Statement, критический анализ ИИ-генерации.
- `practice2/` — код микросервисов, frontend, тесты, `docker-compose.yml`.
- `practice3/` — Kubernetes-манифесты (`k8s/`), отчёт `PRACTICE3.md`.
- `practice4/` — ServiceMonitor, дашборд Grafana, нагрузочный скрипт, `PRACTICE4.md`.
- `FINAL_REPORT.md` — итоговый объединённый отчёт.

---

## Практика 2: быстрый старт локально (Docker Compose)

### Требования

- Установлены [Docker Desktop](https://www.docker.com/products/docker-desktop/) (или Docker Engine + Compose v2).

### Шаги

1. Откройте терминал и перейдите в каталог с compose-файлом:

   ```bash
   cd practice2
   ```

2. Создайте файл переменных окружения (секреты не хранятся в `docker-compose.yml`):

   ```bash
   copy .env.example .env
   ```

   Отредактируйте `.env` при необходимости (пароли БД, JWT, bootstrap-админ).

3. Соберите образы и поднимите сервисы в фоне:

   ```bash
   docker compose up -d --build
   ```

4. Дождитесь готовности контейнеров (первый запуск может занять несколько минут из-за сборки frontend и установки зависимостей Python).

5. Проверьте в браузере или через `curl`:

   | Что | URL |
   |-----|-----|
   | Frontend | http://localhost:3000 |
   | API Gateway | http://localhost:8000 |
   | Swagger (документация API) | http://localhost:8000/docs |
   | Health gateway | http://localhost:8000/health |
   | Список комнат через gateway | http://localhost:8000/api/rooms |

   **Авторизация:** на фронтенде вход или регистрация. Бронирование создаётся только для текущего пользователя. Управление переговорками (добавление, правка, удаление) — только у администратора. Учётная запись bootstrap-админа задаётся в файле **`.env`** (`BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`); значения по умолчанию см. в `.env.example`.

6. Остановка и удаление контейнеров:

   ```bash
   cd practice2
   docker compose down
   ```

---

## Практика 3: Minikube и Kubernetes (подробная инструкция)

Цель: собрать образы `gateway` и `booking-service`, загрузить их в Minikube, применить Secret и манифесты из `practice3/k8s/`, убедиться, что поды в `Running`, API доступен через Ingress или port-forward.

### 3.0. Что должно быть установлено

| Компонент | Назначение |
|-----------|------------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Драйвер Minikube `docker`, сборка образов |
| [Minikube](https://minikube.sigs.k8s.io/docs/start/) | Локальный Kubernetes |
| `kubectl` | Обычно идёт с Docker Desktop или ставится отдельно; совместимость с версией кластера см. ниже |

Рекомендация по версии `kubectl`: для Minikube с Kubernetes **1.31** удобно использовать встроенный клиент:

```bash
minikube kubectl -- get nodes
```

Если системный `kubectl` заметно новее кластера (например, 1.34 к 1.31), часть команд работает, но при `kubectl apply` иногда появляется ошибка вида **failed to download openapi** при недоступном API — это обращение к серверу за схемой, а не «битый» YAML. Решение: убедиться, что Minikube запущен (`minikube status`), контекст `minikube` (`kubectl config current-context`).

### 3.1. Запуск кластера Minikube

1. Запустите Minikube с драйвером Docker (как в методичке):

   ```bash
   minikube start --driver=docker
   ```

   При необходимости можно зафиксировать версию Kubernetes:

   ```bash
   minikube start --driver=docker --kubernetes-version=v1.31.0
   ```

2. Дождитесь сообщения о готовности (например, «Готово! kubectl настроен…»).

3. Включите Ingress (nginx):

   ```bash
   minikube addons enable ingress
   ```

4. Проверка узла:

   ```bash
   kubectl get nodes
   ```

### 3.2. Сборка образов приложения

Все команды ниже выполняйте из **корня репозитория** (каталог, где лежат `practice2/`, `practice3/`).

1. Соберите образ API-шлюза:

   ```bash
   docker build -t gateway:latest -f practice2/services/gateway/Dockerfile practice2/services/gateway
   ```

2. Соберите образ сервиса бронирований:

   ```bash
   docker build -t booking-service:latest -f practice2/services/booking_service/Dockerfile practice2/services/booking_service
   ```

Имена тегов **`gateway:latest`** и **`booking-service:latest`** должны совпадать с полем `image` в манифестах.

### 3.3. Загрузка образов в Minikube

Minikube использует свой Docker (или CRI), поэтому локально собранные образы нужно явно загрузить:

```bash
minikube image load gateway:latest
minikube image load booking-service:latest
```

Проверка, что образы видны внутри профиля:

```bash
minikube image ls | findstr gateway
minikube image ls | findstr booking-service
```

(В PowerShell можно заменить `findstr` на `Select-String`.)

### 3.4. Применение манифестов

1. Подготовьте Secret с учётными данными (файл `booking-secrets.yaml` в репозиторий не коммитится):

   ```bash
   copy practice3\k8s\booking-secrets.yaml.example practice3\k8s\booking-secrets.yaml
   ```

   Отредактируйте `practice3/k8s/booking-secrets.yaml`: пароль в `DATABASE_URL` должен совпадать с `DATABASE_PASSWORD`.

2. Примените Secret, затем остальные объекты (ConfigMap, Postgres, Redis, booking-service, gateway, Ingress):

   ```bash
   kubectl apply -f practice3/k8s/booking-secrets.yaml
   kubectl apply -f practice3/k8s/all-in-one.yaml
   ```

3. Дождитесь готовности деплойментов (таймаут можно увеличить при медленной машине):

   ```bash
   kubectl wait --for=condition=available deployment/postgres deployment/redis deployment/booking-service deployment/gateway --timeout=300s
   ```

4. Проверьте поды, сервисы и Ingress:

   ```bash
   kubectl get pods,svc,ingress
   ```

Ожидаемо: поды `postgres`, `redis`, `booking-service`, два реплики `gateway` — в статусе `Running`. У `booking-service` при первом старте возможны кратковременные рестарты, пока Postgres не готов — это нормально, если в итоге `READY 1/1`.

### 3.5. Доступ к API и UI

В манифесте Ingress указан хост **`myapp.local`**. Варианты доступа:

#### Вариант A: `minikube tunnel` (удобно для Ingress на localhost)

1. В **отдельном** терминале с **правами администратора** (на Windows часто нужно для привязки к порту 80):

   ```bash
   minikube tunnel
   ```

2. Оставьте процесс запущенным. В файле `hosts` добавьте строку (IP можно посмотреть `minikube ip`, либо использовать `127.0.0.1` в связке с tunnel — ориентируйтесь на вывод tunnel):

   ```
   127.0.0.1 myapp.local
   ```

3. Проверка:

   ```bash
   curl -H "Host: myapp.local" http://127.0.0.1/health
   curl -H "Host: myapp.local" http://127.0.0.1/api/rooms
   ```

#### Вариант B: Port-forward к gateway (без Ingress и без прав администратора)

Подходит для быстрой проверки API и отладки.

```bash
kubectl port-forward svc/gateway 18080:80
```

В другом терминале:

```bash
curl http://127.0.0.1:18080/api/rooms
curl http://127.0.0.1:18080/health
```

Frontend в Kubernetes в этом репозитории **не** входит в `all-in-one.yaml`; UI по-прежнему удобно открывать через **Docker Compose** (`http://localhost:3000`), указав в `.env` или переменной окружения Vite базовый URL API на port-forward или tunnel (например, `VITE_API_BASE_URL=http://127.0.0.1:18080` перед `docker compose build` для frontend).

#### Вариант C: NodePort контроллера Ingress

Узнайте порт NodePort для HTTP:

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller
```

Запрос (подставьте IP из `minikube ip` и порт из колонки `80:3xxxx/TCP`):

```bash
curl -H "Host: myapp.local" http://<MINIKUBE_IP>:<NODEPORT>/api/rooms
```

### 3.6. Остановка и очистка

```bash
minikube stop
```

Полное удаление профиля (освобождение ресурсов):

```bash
minikube delete
```

Если на Windows появляется ошибка про `.tunnel_lock`, сначала завершите процесс **`minikube tunnel`**, затем повторите `minikube delete`.

### 3.7. Отдельные файлы манифестов

В каталоге `practice3/k8s/` помимо `all-in-one.yaml` лежат разнесённые манифесты для удобства проверки (`deployment-*.yaml`, `service-*.yaml`, `ingress.yaml`). Их можно применять по отдельности, но тогда следите за порядком и отсутствием дублирования с уже созданными объектами.

---

## Практика 4: мониторинг (подробная инструкция)

Цель: поднять Prometheus и Grafana (чарт **`kube-prometheus-stack`**), подключить сбор метрик с `gateway` и `booking-service` через `ServiceMonitor`, импортировать дашборд, при желании запустить нагрузочный скрипт.

**Важно:** сначала должна быть успешно развёрнута **практика 3** (приложение в кластере, сервисы с метками `app: gateway` и `app: booking-service`, порт с именем **`http`** и путь **`/metrics`** уже заданы в манифестах сервисов).

### 4.0. Установка Helm

Helm нужен для установки чарта. Варианты:

- Официальный установщик: https://github.com/helm/helm/releases  
- Chocolatey: `choco install kubernetes-helm`  
- Скачать бинарник и добавить в `PATH`.

Проверка:

```bash
helm version
```

### 4.1. Установка kube-prometheus-stack

1. Добавьте репозиторий чартов и обновите индекс:

   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo update
   ```

2. Установите стек в отдельное пространство имён (имя релиза **`monitoring`** должно совпадать с меткой `release: monitoring` в файле `practice4/monitoring/servicemonitors.yaml`):

   ```bash
   helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
   ```

3. Дождитесь готовности подов (может занять 5–15 минут при первом скачивании образов):

   ```bash
   kubectl get pods -n monitoring -w
   ```

   Остановите просмотр: `Ctrl+C`.

### 4.2. Подключение ServiceMonitor к приложению

Файл описывает два ресурса `ServiceMonitor` для сбора `/metrics` с сервисов, у которых в селекторе метки `app: gateway` и `app: booking-service` (как в ваших `Service` из практики 3).

Из корня репозитория (только **после** успешной установки чарта в разделе 4.1, когда в кластере появились CRD `ServiceMonitor`):

```bash
kubectl apply -f practice4/monitoring/servicemonitors.yaml
```

Если команда завершилась ошибкой вида **`no matches for kind "ServiceMonitor"`** / **`ensure CRDs are installed first`** — чарт Prometheus Operator ещё не установлен или не до конца развернулся; вернитесь к шагу 4.1 и дождитесь готовности подов в `monitoring`.

Проверка:

```bash
kubectl get servicemonitor
```

Если Prometheus не подхватывает цели, проверьте в кластере настройки `Prometheus` (селекторы по namespace и по меткам `release`) — в стандартной установке `kube-prometheus-stack` часто собираются все `ServiceMonitor` с меткой релиза `monitoring` во всех namespace; при отличии имени релиза Helm измените метку `release` в `servicemonitors.yaml` на фактическое имя релиза.

### 4.3. Доступ к Grafana

1. Узнайте имя сервиса Grafana (часто содержит `grafana`):

   ```bash
   kubectl get svc -n monitoring
   ```

2. Проброс порта (пример для сервиса с именем вида `monitoring-grafana`; подставьте своё имя из вывода):

   ```bash
   kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
   ```

3. Откройте в браузере: http://localhost:3000  

4. Логин по умолчанию для чарта: пользователь **`admin`**, пароль — из секрета (имя секрета может отличаться; ищите `*-grafana`):

   ```bash
   kubectl get secrets -n monitoring
   ```

   Пример извлечения пароля (PowerShell):

   ```powershell
   $b = kubectl get secret -n monitoring monitoring-grafana -o jsonpath="{.data.admin-password}"
   [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($b))
   ```

### 4.4. Импорт дашборда

1. В Grafana: **Dashboards → New → Import**.
2. Загрузите файл `practice4/monitoring/grafana-dashboard.json` или вставьте его содержимое.
3. Выберите источник данных Prometheus (обычно создаётся чартом автоматически, имя вроде `Prometheus`).

На дашборде ожидаются панели по метрикам `gateway_http_requests_total`, `gateway_http_request_duration_seconds`, `bookings_created_total` и др. (см. `practice4/PRACTICE4.md`).

### 4.5. Нагрузочный тест

1. Установите зависимости Python (из корня репозитория или с указанием пути к httpx в вашем окружении):

   ```bash
   pip install httpx
   ```

2. Убедитесь, что хост **`myapp.local`** резолвится и доступен тот же URL, по которому реально ходит клиент (Ingress через tunnel / NodePort / либо измените URL в скрипте под port-forward).

3. Запуск:

   ```bash
   python practice4/load_test.py
   ```

   Базовый URL можно передать первым аргументом (удобно при проверке через port-forward):

   ```bash
   python practice4/load_test.py http://127.0.0.1:18080
   ```

   По умолчанию используется `http://myapp.local` (Ingress), см. `practice4/load_test.py`.

### 4.6. Удаление стека мониторинга

```bash
helm uninstall monitoring -n monitoring
```

При необходимости удалите namespace (осторожно: удалит все ресурсы в нём):

```bash
kubectl delete namespace monitoring
```

---

## Автотесты (практика 2)

```bash
pip install -r practice2/requirements-test.txt
pytest practice2/tests -q
```

---

## Использованный стек

- Backend: Python, FastAPI, SQLAlchemy  
- Data: PostgreSQL, Redis  
- Frontend: React + Vite, тёмная UI-тема  
- Infra: Docker, Docker Compose, Kubernetes, Minikube, Ingress  
- Monitoring: Prometheus + Grafana (`kube-prometheus-stack`), ServiceMonitor  
