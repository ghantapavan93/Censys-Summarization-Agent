from typing import Dict

_MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "summary.title": "Executive Summary",
        "summary.key_findings": "Key Findings",
        "summary.risks": "Risks",
        "summary.viz": "Visualizations",
        "summary.risk_matrix": "Risk Matrix",
        "summary.notes": "Notes",
        "summary.uncertainty": "Uncertainty",
    },
    "es": {
        "summary.title": "Resumen Ejecutivo",
        "summary.key_findings": "Hallazgos Clave",
        "summary.risks": "Riesgos",
        "summary.viz": "Visualizaciones",
        "summary.risk_matrix": "Matriz de Riesgo",
        "summary.notes": "Notas",
        "summary.uncertainty": "Incertidumbre",
    },
}


def t(lang: str, key: str, default: str | None = None) -> str:
    lang = (lang or "en").lower()[0:2]
    bundle = _MESSAGES.get(lang) or _MESSAGES["en"]
    return bundle.get(key) or default or key
