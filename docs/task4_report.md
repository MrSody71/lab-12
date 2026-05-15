# Задание 4 — CI/CD с AI Code Review
**Автор:** Артюх Виталий Валериевич  
**Группа:** 221131  

## Что реализовано
GitHub Actions workflow (.github/workflows/pr_review.yml) который:
- Запускается при создании Pull Request
- Job 1 (test): запускает pytest с покрытием
- Job 2 (ai-review): отправляет diff PR в Claude API и публикует комментарий

## Скриншот работы
![AI комментарий в PR](ci_screenshot.png)

## Ссылка на PR
[вставь URL своего тестового PR]

## Ссылка на Actions run
[вставь URL запуска workflow]

## Пример комментария от ИИ
[вставь текст комментария который оставил ИИ]
