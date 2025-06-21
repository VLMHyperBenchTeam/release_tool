# Инструмент автоматизации релизов `release_tool`

> Минимальный набор Python-скриптов, упрощающих релиз пакетов внутри **UV workspace**-проекта.
>
> Работает в *четыре этапа* (Stage 1 → Stage 2 → Stage 3 → Stage 4) и описывается единственным конфигурационным файлом `release_tool.toml`.

---
## 1. Быстрый старт
```bash
# 1️⃣ Проверяем незакоммиченные файлы
python -m release_tool.stage1          # создаёт *changes_uncommitted.txt*

# 2️⃣ Отдаём файлы LLM → заполняем *commit_message.txt*
python -m release_tool.stage2 --push   # коммитим (и пушим) все изменения

# 3️⃣ Собираем коммиты после последнего тега
python -m release_tool.stage3          # создаёт *changes_since_tag.txt*

# 4️⃣ Отдаём в LLM → заполняем *tag_message.txt*, затем bump+tag
python -m release_tool.stage4 --bump patch --push   # 1.2.3 → 1.2.4 + тег
#   (bump: patch|minor|major|dev)
```

`--dry-run` или `dry_run=true` в конфиге выводит шаги без изменения репозитория — удобно для проверки.

---
## 2. Установка зависимостей
```
pip install packaging
```
*(используется только пакет `packaging`; остальные модули — стандартная библиотека)*

---
## 3. Конфигурация `release_tool.toml`
```toml
[tool.release_tool]
# Каталог, в котором лежат подпакеты (Git-репозитории)
packages_dir = "packages"

# Файлы с изменениями
changes_uncommitted_filename = "changes_uncommitted.txt"
changes_since_tag_filename   = "changes_since_tag.txt"

# Файлы с сообщениями LLM
commit_message_filename = "commit_message.txt"
tag_message_filename    = "tag_message.txt"

# Префикс тега (итоговый тег = "<tag_prefix><version>")
tag_prefix = "v"

# Имя удалённого репозитория (git push <remote>)
git_remote = "origin"

# "Сухой" режим: только вывод шагов, без изменений
# (можно переопределить из CLI ключом --dry-run)
dry_run = true
```

---
## 4. Этапы работы
### 4.1 Stage 1 — «Uncommitted»
`python -m release_tool.stage1 [--dry-run]`

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

### 4.2 Stage 2 — «Commit»
`python -m release_tool.stage2 [--dry-run] [--push]`

Коммитит все изменения (`git add -A`) используя `<commit_message_filename>`.

**Читает файлы:** `<changes_output_dir>/<package_name>/<commit_message_filename>`  
*(по умолчанию: `release_tool/changes/<package_name>/commit_message.txt`)*

**Когда есть подготовленные сообщения:**
```
[stage2] Выполняем коммит и push для пакетов с подготовленными сообщениями...
[stage2] Проверяем пакет: hello_world
[stage2]   ✅ hello_world: commit создан и отправлен
[stage2] ✅ Завершено. Обработано пакетов: 1
```

**Когда сообщений нет:**
```
[stage2] Выполняем коммит и push для пакетов с подготовленными сообщениями...
[stage2] Проверяем пакет: hello_world
[stage2]   hello_world: файл commit-сообщения не найден
[stage2] ✅ Нет пакетов с подготовленными commit-сообщениями
```

### 4.3 Stage 3 — «Since Tag»
`python -m release_tool.stage3 [--dry-run]`

Собирает `git log <last_tag>..HEAD` → `<changes_output_dir>/<package>/<changes_since_tag_filename>`.

**Создаёт файлы:**
- `<changes_output_dir>/<package_name>/<changes_since_tag_filename>` — коммиты
- `<changes_output_dir>/<package_name>/<tag_message_filename>` — **пустой файл** для LLM

*(по умолчанию: `release_tool/changes/<package_name>/changes_since_tag.txt` и `release_tool/changes/<package_name>/tag_message.txt`)*

**Когда есть новые коммиты:**
```
[stage3] Поиск коммитов после последнего тега...
[stage3] Проверяем каталог: packages
[stage3] Проверяем пакет: hello_world
[stage3]   ✅ hello_world: коммиты сохранены в release_tool/changes/hello_world/changes_since_tag.txt
[stage3]   📝 hello_world: создан пустой файл release_tool/changes/hello_world/tag_message.txt
[stage3] ✅ Завершено. Обработано пакетов: 1
```

**Когда новых коммитов нет:**
```
[stage3] Поиск коммитов после последнего тега...
[stage3] Проверяем каталог: packages
[stage3] Проверяем пакет: hello_world
[stage3]   hello_world: нет новых коммитов после последнего тега
[stage3] ✅ Нет пакетов с новыми коммитами после последнего тега
```

### 4.4 Stage 4 — «Release / Tag»
`python -m release_tool.stage4 [--dry-run] [--bump …] [--push]`

1. Bump версии (`patch|minor|major|dev`).
2. Создаёт аннотированный тег `v<version>` с текстом из `<tag_message_filename>`.
3. `git add -A && git commit` (с тем же текстом) и `git push --tags`, если указан `--push`.

**Читает файлы:** `<changes_output_dir>/<package_name>/<tag_message_filename>`  
*(по умолчанию: `release_tool/changes/<package_name>/tag_message.txt`)*

**Когда есть подготовленные tag-сообщения:**
```
[stage4] Выполняем bump версий (patch) и push для пакетов с подготовленными tag-сообщениями...
[stage4] Проверяем пакет: hello_world
[stage4]   📦 hello_world: 0.0.1.dev0 -> 0.0.1.dev1
[stage4]   ✅ hello_world: версия 0.0.1.dev1 выпущена и отправлена
[stage4] ✅ Завершено. Обработано пакетов: 1
```

**Когда tag-сообщений нет:**
```
[stage4] Выполняем bump версий (patch) и push для пакетов с подготовленными tag-сообщениями...
[stage4] Проверяем пакет: hello_world
[stage4]   hello_world: файл tag-сообщения не найден
[stage4] ✅ Нет пакетов с подготовленными tag-сообщениями
```

### Полный цикл
```
python -m release_tool.stage1            # uncommitted
# → заполняем commit_message.txt
python -m release_tool.stage2 --push

python -m release_tool.stage3            # log since tag
# → заполняем tag_message.txt
python -m release_tool.stage4 --bump patch --push
```

---
## 5. Алгоритмы и детали реализации
• Git-операции выполняются через `subprocess` (см. `release_tool/git_utils.py`).  
• Проверка «есть ли изменения» — `git rev-list <last_tag>..HEAD --count` (>0 → есть).  
• Инкремент версий — `packaging.version.Version` + RegExp; поддерживаются уровни `patch`/`minor`/`major` и `dev`.

---

## 6. Типовые сценарии

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
uv run python -m release_tool.stage2 --push

# 2. Готовим релиз
uv run python -m release_tool.stage3
# Заполняем tag_message.txt в каждом пакете
uv run python -m release_tool.stage4 --bump patch --push
```

### Только коммиты (без релиза)
```bash
uv run python -m release_tool.stage1
# Заполняем commit_message.txt
uv run python -m release_tool.stage2  # без --push
```

### Только релиз (после коммитов)
```bash
uv run python -m release_tool.stage3
# Заполняем tag_message.txt
uv run python -m release_tool.stage4 --bump minor --push
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
## 8. Частые вопросы
| Вопрос | Ответ |
|--------|-------|
| **Нужен ли отдельный виртуальный env?** | Нет, достаточно установить зависимость `packaging`. |
| **Можно ли использовать без LLM?** | Да — вручную заполните `release_commit_message.txt`. |
| **Как работает bump для обычных версий?** | Поддерживаются три уровня: *patch*, *minor*, *major*. |
| **Как работает bump для dev-версий?** | Если версия содержит `.devN` — увеличивается `N`; если `.dev` нет — добавляется `.dev1`. |

---
## 9. Лицензия
MIT © 2025 