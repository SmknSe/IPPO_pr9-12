# Практика 4. Мониторинг и наблюдаемость в Kubernetes

## Цель работы (по методичке)

1. Развернуть стек мониторинга в Kubernetes.
2. Экспортировать метрики приложения на `/metrics`.
3. Настроить сбор метрик Prometheus.
4. Создать дашборд и зафиксировать поведение системы под нагрузкой.

## Выбранная система мониторинга

Prometheus + Grafana (`kube-prometheus-stack`) как наиболее стандартный и совместимый стек для Minikube.

## Экспортируемые метрики приложения

- `gateway_http_requests_total` (Counter)  
  Счетчик HTTP-запросов в gateway по endpoint и status code.
- `gateway_http_request_duration_seconds` (Histogram)  
  Распределение времени ответа gateway.
- `booking_http_requests_total` (Counter)  
  Счетчик запросов в booking-service.
- `booking_http_request_duration_seconds` (Histogram)  
  Распределение времени ответа booking-service.
- `bookings_created_total` (Counter)  
  Бизнес-метрика числа успешно созданных бронирований.

## Конфигурации практики

- ServiceMonitor: `monitoring/servicemonitors.yaml`
- Dashboard JSON: `monitoring/grafana-dashboard.json`
- Нагрузочный скрипт: `load_test.py`
- Скриншоты: `screenshots/`

## Ход работы

### Шаг 1. Установка мониторинга

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack
```

### Шаг 2. Подключение метрик приложения

```bash
kubectl apply -f practice4/monitoring/servicemonitors.yaml
```

### Шаг 3. Доступ к Grafana

```bash
kubectl port-forward svc/monitoring-grafana 3000:80
```

### Шаг 4. Создание дашборда

Импортирован `monitoring/grafana-dashboard.json` с панелями:
- RPS через gateway;
- P95 latency;
- скорость создания бронирований.

### Шаг 5. Нагрузочное тестирование

```bash
python practice4/load_test.py
```

Скрипт отправляет 150 запросов к API и позволяет наблюдать рост RPS и latency на дашборде.

## Как интерпретировать результаты

- Рост `gateway_http_requests_total` подтверждает поступление нагрузки.
- Изменение квантилей `gateway_http_request_duration_seconds` показывает влияние нагрузки на задержки.
- Рост `bookings_created_total` отражает бизнес-активность системы.

## Вывод

Мониторинг дает прозрачность эксплуатации: можно вовремя замечать деградации, проверять эффект изменений и отслеживать бизнес-события в реальном времени.
