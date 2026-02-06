"""
Worklog Checker plugin: check employee worklogs (Jira + Tempo).
Phase 6: stub implementation — returns message to configure in admin.
Full Jira/Tempo integration can be added later.
"""
from typing import Optional


async def check_worklogs(employee: str, period: str) -> str:
    """
    Checks worklogs for an employee for a period.
    Stub: requires Jira and Tempo to be configured in admin.
    """
    try:
        from tools.base import get_plugin_setting
        jira_url = get_plugin_setting("worklog-checker", "jira_url")
        tempo_token = get_plugin_setting("worklog-checker", "tempo_token")
        if not jira_url or not tempo_token:
            return (
                "Worklog Checker: настройте Jira URL и Tempo API token в разделе «Инструменты» админ-панели, "
                "затем включите инструмент check_worklogs."
            )
        # TODO: implement Jira user search + Tempo worklogs fetch + required hours calculation
        return (
            f"Проверка ворклогов для «{employee}» за период «{period}»: интеграция с Jira и Tempo в разработке. "
            "Настройте плагин в админке и обновите плагин до версии с полной поддержкой."
        )
    except Exception as e:
        return "Ошибка: " + str(e)


async def get_worklog_summary(period: str, team: Optional[str] = None) -> str:
    """
    Summary of worklogs for team or period.
    Stub: requires configuration.
    """
    try:
        from tools.base import get_plugin_setting
        jira_url = get_plugin_setting("worklog-checker", "jira_url")
        if not jira_url:
            return "Worklog Checker: настройте Jira и Tempo в админ-панели (раздел «Инструменты»)."
        # TODO: implement team resolution + per-user worklogs + aggregation
        return (
            f"Сводка ворклогов за период «{period}»"
            + (f" по команде «{team}»" if team else "")
            + ": полная интеграция в разработке. Настройте плагин в админке."
        )
    except Exception as e:
        return "Ошибка: " + str(e)
