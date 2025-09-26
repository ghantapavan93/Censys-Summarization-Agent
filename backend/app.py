from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import json

from schemas import Host, SummaryResponse, DatasetInsights
from summarizer_rule import summarize_host_llm as summarize_host_rule
from summarizer_llm import summarize_host_llm, llm_available
from analytics import derive_dataset_insights

api = FastAPI(title="Censys Summarization Agent", version="0.1.0")
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@api.get("/health")
def health():
    return {"ok": True}

@api.post("/summarize", response_model=SummaryResponse)
async def summarize(file: UploadFile = File(...)):
    raw = await file.read()
    payload = json.loads(raw)

    if isinstance(payload, list):
        hosts_raw: List[Dict[str, Any]] = payload
    else:
        hosts_raw = (
            payload.get("hosts")
            or payload.get("result", {}).get("resources")
            or []
        )

    hosts_parsed: List[Host] = []
    summaries: List[Dict[str, Any]] = []

    for h in hosts_raw:
        try:
            host_obj = Host.model_validate(h)
            hosts_parsed.append(host_obj)
            if llm_available():
                s = summarize_host_llm(host_obj)
            else:
                s = summarize_host_rule(host_obj)
            summaries.append(s)
        except Exception as e:
            summaries.append({
                "ip": h.get("ip", "unknown"),
                "summary": f"Error parsing host: {e}",
                "severity_hint": "UNKNOWN",
            })

    insights: DatasetInsights = derive_dataset_insights(hosts_parsed)
    return SummaryResponse(count=len(summaries), summaries=summaries, insights=insights)