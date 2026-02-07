"""
Worklog Checker plugin: one tool for worklogs (detail by employee or summary by team).
Uses single account/token for Jira and Tempo.
"""
from typing import Optional


async def get_worklogs(
    period: str,
    employee: Optional[str] = None,
    team: Optional[str] = None,
) -> str:
    """
    Get worklogs for a period. If employee is set — detail for that person;
    if team is set — summary for team/several people; otherwise prompt to specify.
    """
    try:
        from tools.base import get_plugin_setting

        jira_url = get_plugin_setting("worklog-checker", "jira_url")
        api_token = get_plugin_setting("worklog-checker", "api_token")
        if not jira_url or not api_token:
            return (
                "Worklog Checker: настройте Jira URL и API Token в разделе «Инструменты» админ-панели, "
                "затем включите инструмент get_worklogs."
            )
        if employee:
            # Один сотрудник — детальная проверка (часы, дефицит/переработки, задачи)
            # TODO: Jira user search + Tempo worklogs + required hours
            return (
                f"Проверка ворклогов для «{employee}» за период «{period}»: интеграция с Jira и Tempo в разработке. "
                "Настройте плагин в админке и обновите до версии с полной поддержкой."
            )
        if team:
            # Команда или список — сводка по людям
            # TODO: team resolution + per-user worklogs + aggregation
            return (
                f"Сводка ворклогов за период «{period}» по команде/списку «{team}»: "
                "полная интеграция в разработке. Настройте плагин в админке."
            )
        return (
            "Укажите employee (для детали по одному человеку) или team (для сводки по команде/списку)."
        )
    except Exception as e:
        return "Ошибка: " + str(e)
