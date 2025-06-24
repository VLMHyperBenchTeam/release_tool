# Инструмент автоматизации релизов `release_tool`

## 🚀 Описание проекта

**release_tool** — это мощный инструмент автоматизации релизов для UV workspace проектов с множественными пакетами. Он превращает долгий ручной процесс релиза в простую 4-этапную автоматизированную процедуру с интеграцией LLM для генерации качественных commit и tag сообщений.

### ✨ Ключевые преимущества

- **🎯 Автоматизация**: Автоматизирует весь цикл релиза от поиска изменений до публикации тегов
- **🧠 LLM-интеграция**: Использует ИИ для генерации осмысленных commit и tag сообщений
- **📦 UV Workspace поддержка**: Специально разработан для работы с UV workspace структурой
- **🔄 4-этапный процесс**: Четкое разделение на логические этапы для контроля и гибкости
- **⚡ Экономия времени**: Сокращает время релиза до нескольких команд
- **🛡️ Безопасность**: Dry-run режим для проверки без изменений + детальное логирование
- **🔧 Гибкая конфигурация**: Единый конфигурационный файл с умным поиском настроек
- **📊 Cемантическое версионирование**: Автоматическое управление версиями (patch/minor/major/dev)
- **🔗 Git Submodule**: Легкая интеграция в существующие проекты через submodule
- **📝 Подробная документация**: Исчерпывающие логи и понятные сообщения об ошибках

### 🎯 Что делает проект

1. **Обнаруживает изменения** в пакетах workspace
2. **Генерирует детальные отчеты** о незакоммиченных изменениях и коммитах
3. **Интегрируется с LLM** для создания качественных сообщений
4. **Автоматизирует git-операции** (commit, tag, push)
5. **Управляет версиями** с поддержкой семантического версионирования
6. **Обеспечивает контроль** через dry-run режим и поэтапное выполнение


> Минимальный набор Python-скриптов, упрощающих релиз пакетов внутри **UV workspace**-проекта.
>
> Работает в *четыре этапа* (Stage 1 → Stage 2 → Stage 3 → Stage 4) и описывается единственным конфигурационным файлом `release_tool.toml`.

---
## 1. Быстрый старт
```bash
# 1️⃣ Проверяем незакоммиченные файлы
uv run python -m release_tool.stage1          # создаёт *changes_uncommitted.txt*

# 2️⃣ Отдаём файлы LLM → заполняем *commit_message.txt*
uv run python -m release_tool.stage2 --commit --push   # коммитим (и пушим) все изменения

# 3️⃣ Собираем diff после последнего тега
uv run python -m release_tool.stage3          # создаёт *changes_since_tag.txt*

# 4️⃣ Отдаём в LLM → заполняем *tag_message.txt*, затем bump+tag
uv run python -m release_tool.stage4 --bump patch --push   # 1.2.3 → 1.2.4 + тег
#   (bump: patch|minor|major|dev)
```

**Очистка файлов изменений:**
```bash
uv run python -m release_tool.clear           # очищает release_tool/changes
```

`--dry-run` или `dry_run=true` в конфиге выводит шаги без изменения репозитория — удобно для проверки.

---
## 2. Установка в проекты

### Для новых проектов
```bash
# Добавляем release_tool как git submodule
git submodule add https://github.com/VLMHyperBenchTeam/release_tool.git release_tool

# Клонирование проектов с submodules
git clone --recursive https://github.com/your-username/your-project.git

# Или инициализация submodules в уже склонированном проекте
git submodule update --init --recursive
```

### Структура проекта после установки
```
your-project/
├── release_tool/           # ← Git submodule
│   ├── stage1.py
│   ├── stage2.py  
│   ├── stage3.py
│   ├── stage4.py
│   ├── config.py
│   ├── git_utils.py
│   ├── release_tool.toml   # ← Конфигурация
│   └── README.md
├── packages/               # ← Ваши пакеты
│   ├── package1/
│   └── package2/
└── .gitmodules            # ← Конфигурация submodules
```

### Обновление release_tool
```bash
# Переходим в папку submodule и обновляем
cd release_tool
git pull origin main

# Возвращаемся в основной проект и фиксируем обновление
cd ..
git add release_tool
git commit -m "update: обновить release_tool до последней версии"
git push
```

**Отслеживание конфигурации:**
При запуске любой команды в выводе указывается, какая конфигурация используется:
```
[stage1] Поиск незакоммиченных изменений в пакетах...
[stage1] Конфигурация: release_tool.toml          # ← корневая (приоритет)
[stage1] Конфигурация: release_tool/release_tool.toml  # ← из submodule
```

---
## 3. Установка зависимостей
```
pip install packaging
```
*(используется только пакет `packaging`; остальные модули — стандартная библиотека)*

---
## 4. Конфигурация `release_tool.toml`

### Умный поиск конфигурации
`release_tool` автоматически ищет конфигурацию в следующем порядке приоритета:

1. **`release_tool.toml` в корне проекта** — для кастомизации под конкретный проект
2. **`release_tool/release_tool.toml` в submodule** — дефолтная конфигурация
3. **Встроенные настройки** — если файлы не найдены

**Преимущества этого подхода:**
- ✅ **Гибкость**: можно кастомизировать настройки для каждого проекта
- ✅ **Простота**: работает "из коробки" без дополнительной настройки
- ✅ **Совместимость**: старые проекты продолжают работать
- ✅ **Переносимость**: submodule содержит рабочую конфигурацию по умолчанию

### Пример конфигурации
```toml
[tool.release_tool]
# Каталог, в котором лежат подпакеты (Git-репозитории)
packages_dir = "packages"

# Файлы с изменениями
changes_uncommitted_filename = "changes_uncommitted.txt"
changes_since_tag_filename   = "changes_since_tag.txt"

# Каталог, куда складываются файлы изменений
changes_output_dir = "release_tool/changes"

# Путь к prod/pyproject.toml для обновления тегов релизов
prod_pyproject_path = "prod/pyproject.toml"

# Файлы с сообщениями LLM
commit_message_filename = "commit_message.txt"
tag_message_filename    = "tag_message.txt"

# Префикс тега (итоговый тег = "<tag_prefix><version>")
tag_prefix = "v"

# Имя удалённого репозитория (git push <remote>)
git_remote = "origin"

# "Сухой" режим: только вывод шагов, без изменений
# (можно переопределить из CLI ключом --dry-run)
dry_run = false
```

### Кастомизация для проекта
Чтобы изменить настройки для конкретного проекта, создайте `release_tool.toml` в корне:

```bash
# Копируем дефолтную конфигурацию
cp release_tool/release_tool.toml .

# Редактируем под свои нужды
# Например, меняем packages_dir = "my_packages"
```

---
## 5. Этапы работы
### 5.1 Stage 1 — «Uncommitted»
`uv run python -m release_tool.stage1 [--dry-run]`

1. Проверяет `git status --porcelain`.
2. Если есть изменения → файл `<changes_output_dir>/<package>/<changes_uncommitted_filename>` с:
   * список файлов (`git status --porcelain`)
   * краткая сводка (`git diff --stat`)
   * **полный diff** (`git diff`) — все изменения построчно.

**Создаёт файлы:**
- `<changes_output_dir>/<package_name>/<changes_uncommitted_filename>` — изменения
- `<changes_output_dir>/<package_name>/<commit_message_filename>` — **пустой файл** для LLM

*(по умолчанию: `release_tool/changes/<package_name>/changes_uncommitted.txt` и `release_tool/changes/<package_name>/commit_message.txt`)*

**Когда есть изменения:**
```
[stage1] Поиск незакоммиченных изменений в пакетах...
[stage1] Проверяем каталог: packages
[stage1] Проверяем пакет: hello_world
[stage1]   ✅ hello_world: изменения сохранены в release_tool/changes/hello_world/changes_uncommitted.txt
[stage1]   📝 hello_world: создан пустой файл release_tool/changes/hello_world/commit_message.txt
[stage1] ✅ Завершено. Обработано пакетов с изменениями: 1
```

**Когда изменений нет:**
```
[stage1] Поиск незакоммиченных изменений в пакетах...
[stage1] Проверяем каталог: packages
[stage1] Проверяем пакет: hello_world
[stage1]   hello_world: нет незакоммиченных изменений
[stage1] ✅ Изменений не обнаружено — файлы изменений не созданы
```

### 5.2 Stage 2 — «Commit»
`uv run python -m release_tool.stage2 [--dry-run] [--commit] [--push]`

Выполняет коммит и/или push изменений. Параметры `--commit` и `--push` независимы.

**Параметры:**
- `--commit` — создать коммит по подготовленным сообщениям
- `--push` — выполнить git push для пакетов
- Без параметров по умолчанию выполняется только `--commit`

**Читает файлы:** `<changes_output_dir>/<package_name>/<commit_message_filename>`  
*(по умолчанию: `release_tool/changes/<package_name>/commit_message.txt`)*

**Когда есть подготовленные сообщения:**
```
[stage2] Выполняем коммит и push для пакетов с подготовленными сообщениями...
[stage2] Проверяем пакет: hello_world
[stage2]   ✅ hello_world: commit создан и отправлен
[stage2] ✅ Завершено. Обработано пакетов: 1
```

**При push показывает статус каждого пакета:**
```
[stage2] Выполняем push для пакетов...
[stage2] Проверяем пакет: hello_world
[stage2]   ✅ hello_world: изменения отправлены
[stage2] Проверяем пакет: bench_utils
[stage2]   📭 bench_utils: изменений нет
```

### 5.3 Stage 3 — «Since Tag»
`uv run python -m release_tool.stage3 [--dry-run] [--tag TAG_NAME]`

Собирает **полный diff** изменений между тегом и HEAD → `<changes_output_dir>/<package>/<changes_since_tag_filename>`.

**Параметры:**
- `--tag TAG_NAME` — собрать изменения с указанного тега (по умолчанию — последний тег)
- `--dry-run` — показать, что будет сохранено, без создания файлов

**Создаёт файлы:**
- `<changes_output_dir>/<package_name>/<changes_since_tag_filename>` — **только diff**
- `<changes_output_dir>/<package_name>/<tag_message_filename>` — **пустой файл** для LLM

**Примеры использования:**
```bash
# От последнего тега
uv run python -m release_tool.stage3

# От конкретного тега
uv run python -m release_tool.stage3 --tag v1.0.0

# Проверка без создания файлов
uv run python -m release_tool.stage3 --tag v0.5.0 --dry-run
```

### 5.4 Stage 4 — «Release / Tag»
`uv run python -m release_tool.stage4 [--dry-run] [--bump …] [--push]`

*Параметры `--bump` и `--push` независимы — можно указать один из них или оба сразу.*

1. Если передан `--bump` — увеличивает номер версии (`patch|minor|major|dev`), делает `git add -A && git commit` и ставит локальный тег `v<version>`.
2. Если передан `--push` — отправляет все непушенные коммиты *и* теги в удалённый репозиторий.
3. При наличии обоих флагов сначала выполняется bump, затем push.

**Читает файлы:** `<changes_output_dir>/<package_name>/<tag_message_filename>`  
*(по умолчанию: `release_tool/changes/<package_name>/tag_message.txt`)*

**Пример: bump + push:**
```
[stage4] Выполняем bump версий (patch) с последующим push...
[stage4] Проверяем пакет: hello_world
[stage4]   📦 hello_world: 0.0.1.dev0 -> 0.0.1.dev1
[stage4]   ✅ hello_world: версия 0.0.1.dev1 выпущена и отправлена
[stage4] ✅ Завершено. Обработано пакетов: 1
```

**Пример: только push (bump сделан заранее):**
```
[stage4] Выполняем push подготовленных релизов без изменения версий...
[stage4] Проверяем пакет: hello_world
[stage4]   hello_world: файл tag-сообщения не найден
[stage4] ✅ Нет пакетов с подготовленными tag-сообщениями
```

**Пример: только bump (без push):**
```
[stage4] Выполняем bump версий (patch) без push...
[stage4] Проверяем пакет: hello_world
[stage4]   📦 hello_world: 0.0.1.dev1 -> 0.0.1.dev2
[stage4]   ✅ hello_world: версия 0.0.1.dev2 выпущена (без push)
[stage4] ✅ Завершено. Обработано пакетов: 1
```

**Пример: только push (без bump):**
```bash
# Предположим версия уже bump-нута и тег создан ранее
uv run python -m release_tool.stage4 --push
```

### Полный цикл
```
uv run python -m release_tool.stage1            # uncommitted
# → заполняем commit_message.txt
uv run python -m release_tool.stage2 --commit --push

uv run python -m release_tool.stage3            # diff since tag
# → заполняем tag_message.txt
uv run python -m release_tool.stage4 --bump patch --push
```

### Только коммиты (без релиза)
```bash
uv run python -m release_tool.stage1
# Заполняем commit_message.txt
uv run python -m release_tool.stage2 --commit  # только коммит
```

### Только push (коммиты уже есть)
```bash
uv run python -m release_tool.stage2 --push  # только отправка
```

### Очистка рабочих файлов
```bash
# Удаляет все файлы в release_tool/changes
uv run python -m release_tool.clear

# Показать, что будет удалено
uv run python -m release_tool.clear --dry-run
```

### Дополнительные действия Stage 4
> Дополнительно Stage&nbsp;4 автоматически:
> • удаляет строки `workspace = true` из секции `[tool.uv.sources]` в `pyproject.toml` перед созданием тега (чтобы тег ссылался на «чистую» версию без workspace-зависимостей);
> • после релиза начинает новый dev-цикл, делая коммит `chore: start X.Y.Z.dev0 development`;
> • обновляет тег пакета в файле `prod/pyproject.toml` (путь задаётся ключом `prod_pyproject_path` в конфиге).

---
## 6. Дополнительные команды

### 6.1 Очистка файлов изменений
`uv run python -m release_tool.clear [--dry-run]`

Полностью очищает каталог `changes_output_dir` (по умолчанию `release_tool/changes`).

**Когда нужно использовать:**
- После завершения релиза для очистки временных файлов
- При переключении между разными ветками/проектами
- Для "чистого старта" процесса релиза

**Пример вывода:**
```
[clear] ✅ Каталог release_tool/changes очищен
```

**С --dry-run:**
```
[clear] --dry-run: будет удалён каталог release_tool/changes
  release_tool/changes/hello_world/changes_uncommitted.txt
  release_tool/changes/hello_world/commit_message.txt
```

---
## 7. Алгоритмы и детали реализации
• Git-операции выполняются через `subprocess` (см. `release_tool/git_utils.py`).  
• Проверка «есть ли изменения» — `git rev-list <last_tag>..HEAD --count` (>0 → есть).  
• Инкремент версий — `packaging.version.Version` + RegExp; поддерживаются уровни `patch`/`minor`/`major` и `dev`.

---

## 8. Типовые сценарии

### Проверка без изменений (dry-run)
```bash
# Проверяем все этапы без реальных действий
uv run python -m release_tool.stage1 --dry-run
uv run python -m release_tool.stage2 --dry-run
uv run python -m release_tool.stage3 --dry-run
uv run python -m release_tool.stage4 --dry-run --bump patch
```

### Полный цикл commit → release
```bash
# 1. Фиксируем рабочие изменения
uv run python -m release_tool.stage1
# Заполняем commit_message.txt в каждом пакете
uv run python -m release_tool.stage2 --commit --push

# 2. Готовим релиз
uv run python -m release_tool.stage3
# Заполняем tag_message.txt в каждом пакете
uv run python -m release_tool.stage4 --bump patch --push
```

### Только коммиты (без релиза)
```bash
uv run python -m release_tool.stage1
# Заполняем commit_message.txt
uv run python -m release_tool.stage2 --commit  # только коммит
```

### Только релиз (после коммитов)
```bash
uv run python -m release_tool.stage3
# Заполняем tag_message.txt
uv run python -m release_tool.stage4 --bump minor --push  # bump + push

### Только bump (без push)
```bash
# Версию можно увеличить, находясь офлайн; push сделаем позже
uv run python -m release_tool.stage4 --bump patch
```

### Разные уровни bump
```bash
# Патч-релиз (исправления)
uv run python -m release_tool.stage4 --bump patch --push

# Минорный релиз (новые возможности)
uv run python -m release_tool.stage4 --bump minor --push

# Мажорный релиз (breaking changes)
uv run python -m release_tool.stage4 --bump major --push

# Dev-релиз (разработка)
uv run python -m release_tool.stage4 --bump dev --push
```

---
## 9. Частые вопросы
| Вопрос | Ответ |
|--------|-------|
| **Нужен ли отдельный виртуальный env?** | Нет, достаточно установить зависимость `packaging`. |
| **Можно ли использовать без LLM?** | Да — вручную заполните `release_commit_message.txt`. |
| **Как работает bump для обычных версий?** | Поддерживаются три уровня: *patch*, *minor*, *major*. |
| **Как работает bump для dev-версий?** | Если версия содержит `.devN` — увеличивается `N`; если `.dev` нет — добавляется `.dev1`. |

---
## 10. Лицензия
MIT © 2025 