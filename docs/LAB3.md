# Лабораторная №3: интеграционные тесты и продвижение

## Что изменено и почему

1. `app/visits.py`: первый GET `/visits` добавляет запись PostgreSQL,
   считает строки и сохраняет число в Redis на 10 секунд. Ответ содержит
   `count`, `source: db`, `lastId`. Следующий запрос берёт число из Redis
   (`source: cache`) и не добавляет строку. Это учебная семантика из методички:
   счётчик считает обращения к БД, а не каждый HTTP-запрос.
2. `app/schema.sql`: таблица с идентификатором и временем создания.
   Команда `flask --app run init-db` создаёт её перед запуском приложения.
   Соединения закрываются в контекстных менеджерах и `finally`.
3. `tests/integration`: реальные PostgreSQL 16 и Redis 7 запускаются
   Testcontainers. Function-scoped fixture создаёт новые контейнеры для
   каждого теста. Порты получаем через API, фиксированных портов нет.
   Проверяем HTTP-ответы, реальные строки БД, значение кеша и TTL.
   Истечение кеша моделируем Redis EXPIRE 0, без нестабильного sleep.
4. `setup.cfg`: обычный `pytest` оставляет unit-тесты отдельно.
   Интеграционные тесты запускаются явным путём `tests/integration`.
   Покрытие unit-уровня исключает модуль интеграции и тело CLI-инициализации;
   порог 80% сохранён. Это не показатель общего покрытия приложения.
5. Workflow задаёт цепочку `unit-tests → integration-tests → build →
   promote-to-staging → update-manifest`. Каждый job имеет свой checkout
   и устанавливает необходимые ему зависимости. Сборка не ограничена main:
   поэтому её skipped при падении интеграционных тестов доказывает `needs`.
6. В интеграционном job выполняются последовательный и параллельный
   (`-n auto`) запуски с сохранением времени и JUnit-отчётов в артефакты.
   Три теста не гарантируют ускорения: накладные расходы могут преобладать.
   Первый запуск также может тратить время на скачивание образов.
7. Сохраняются сборка, Trivy Quality Gate и SBOM из ЛР2. Проверенный
   локальный образ публикуется без повторной сборки под коротким SHA.
   Skopeo копирует его в `ghcr.io/igumnovd/myapp-staging` с тем же тегом,
   после чего workflow сравнивает digest источника и назначения.
8. Только после копирования меняются образы приложения и init-контейнера
   в staging Deployment. GitOps job коммитит изменение в Git и не обращается
   к кластеру. Реальное применение выполняет оператор или ArgoCD.
   Условие main ограничивает публикацию, продвижение и изменение манифеста.
   Коммит манифеста исключён из повторного CI через paths-ignore и skip ci.

## Локальная проверка (PowerShell)

Запустите Docker Desktop в режиме Linux containers, дождитесь `docker info`.

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m flake8 app tests scripts
.\venv\Scripts\python.exe -m pytest
Measure-Command { .\venv\Scripts\python.exe -m pytest tests/integration --no-cov }
Measure-Command { .\venv\Scripts\python.exe -m pytest tests/integration --no-cov -n auto }
```

Сравните TotalSeconds и проверьте, что обе команды завершились успешно.
Для честного сравнения предварительно скачайте образы postgres:16 и redis:7,
затем повторите оба измерения несколько раз. Не указывайте выдуманные цифры.

Для ручного запуска приложения задайте DATABASE_URL и REDIS_URL,
выполните `flask --app run init-db`, затем `python run.py`.
`/health` доступен без запущенных БД и Redis.

## Проверка отказа и очистки окружения

Временно замените в `test_first_request_uses_database` ожидаемый `count: 1`
на `count: 999`. Сохраните исходный файл, чтобы вернуть точное содержимое.
Запустите тест с `--no-cov --log-cli-level=WARNING`: он должен упасть.
В teardown логируется остановка PostgreSQL и Redis; контекстные менеджеры
выполняют очистку и при ошибке assertion. Сверьте `docker ps` до и после.

Закоммитьте временно сломанный тест в рабочую ветку и отправьте её:

```powershell
git add app tests requirements.txt setup.cfg .github scripts k8s-manifests docs README.md
git commit -m "Add integration tests and staging promotion"
git push -u origin lab3-integration-promotion
```

В GitHub Actions сохраните ссылку и скриншот: integration-tests = failure,
build = skipped. Именно build подтверждает зависимость: promotion на рабочей
ветке пропускается ещё и по условию main. Верните правильное ожидание,
сделайте новый коммит и push. Получите успешный прогон и откройте PR в main.
Не сливайте сломанный вариант. На main та же цепочка needs предотвращает
продвижение непроверенного образа: предыдущий staging-тег остаётся прежним.
Это предотвращение изменения, а не откат уже развёрнутой версии.

## Проверка продвижения после merge

В настройках репозитория разрешите GitHub Actions запись в contents/packages.
Если main защищена от прямых push, GitOps-коммит потребует согласованного
правила доступа либо отдельного PR. Поведение зависит от настроек репозитория.

Из лога build возьмите 7 символов SHA и проверьте:

```bash
skopeo inspect docker://ghcr.io/igumnovd/myapp-staging:<SHA>
git pull
git log -p -1 -- k8s-manifests/staging/deployment.yaml
```

В артефакте staging-image также сохраняются метаданные. Убедитесь, что тег
равен тегу build, а diff меняет реальные поля image.

Deployment содержит начальный тег `initial` как явную заглушку до первого
успешного продвижения. Не применяйте его до обновления workflow.
Для реального кластера заранее создайте namespace staging и Secret
myapp-services с DATABASE_URL и REDIS_URL доступных PostgreSQL/Redis.
Для приватного GHCR требуется также настроенный imagePullSecret.
Эфемерные контейнеры тестов не являются сервисами staging.

## Что приложить к сдаче

- Ссылку на рабочую ветку и PR в main.
- Успешный запуск CI, включая integration-tests.
- Фактические времена последовательного и параллельного запусков и вывод.
- Неуспешный эксперимент: integration-tests failed, build skipped.
- Лог очистки контейнеров после неуспешного теста.
- Вывод skopeo inspect и diff коммита с новым staging-тегом после merge.

Не отмечайте внешние проверки выполненными до получения реальных логов.
