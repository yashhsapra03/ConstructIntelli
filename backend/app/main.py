from __future__ import annotations

import base64
import json
import os
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

APP_TITLE = "Multimodal Construction Intelligence Platform"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))

class Finding(BaseModel):
    category: Literal["safety", "crack", "quality", "general"]
    title: str
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    recommendation: str
    confidence: float = Field(ge=0, le=1)

class AnalysisResponse(BaseModel):
    mode: Literal["demo", "ai"]
    summary: str
    image_received: bool
    input_completeness: Literal["complete", "partial", "text_only"]
    findings: list[Finding]
    next_steps: list[str]
    disclaimer: str

class PlanRequest(BaseModel):
    project_name: str = Field(default="Sample construction project", max_length=120)
    area_sqft: float = Field(gt=0, le=10_000_000)
    floors: int = Field(default=1, ge=1, le=100)
    quality: Literal["economy", "standard", "premium"] = "standard"
    currency: Literal["INR", "USD"] = "INR"
    start_date: Optional[str] = None

class PlanResponse(BaseModel):
    project_name: str
    area_sqft: float
    estimated_cost: float
    currency: str
    contingency: float
    material_estimates: list[dict]
    schedule: list[dict]
    assumptions: list[str]
    disclaimer: str

class ValuationRequest(BaseModel):
    location: str = Field(min_length=2, max_length=200)
    area_sqft: float = Field(gt=0, le=10_000_000)
    rate_per_sqft: float = Field(gt=0, le=10_000_000)
    age_years: int = Field(default=0, ge=0, le=200)
    condition: Literal["poor", "fair", "good", "excellent"] = "good"

class ValuationResponse(BaseModel):
    location: str
    area_sqft: float
    base_value: float
    adjustment_percent: float
    indicative_value: float
    currency: str
    assumptions: list[str]
    disclaimer: str

app = FastAPI(title=APP_TITLE, version="1.0.0", description="Demo-ready construction image and project analysis API")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DISCLAIMER = "Decision-support prototype only. Image findings, estimates, and valuations are not professional engineering, safety, legal, or appraisal advice. A qualified professional must inspect and verify before decisions or site actions."

@app.get("/api/health")
def health():
    return {"status": "ok", "service": APP_TITLE, "ai_configured": bool(os.getenv("OPENAI_API_KEY")), "mode": "ai" if os.getenv("OPENAI_API_KEY") else "demo"}

async def _model_analysis(prompt: str, image_data_url: Optional[str]) -> Optional[dict]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        kwargs = {"api_key": key}
        if os.getenv("OPENAI_BASE_URL"):
            kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
        client = OpenAI(**kwargs)
        content = [{"type": "text", "text": prompt + " Return ONLY JSON matching this schema: {summary:string, findings:[{category:safety|crack|quality|general,title:string,severity:low|medium|high|critical,description:string,recommendation:string,confidence:number}],next_steps:string[]}. Do not claim certainty from images; state limitations."}]
        if image_data_url:
            content.append({"type": "image_url", "image_url": {"url": image_data_url, "detail": "auto"}})
        response = client.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), messages=[{"role": "user", "content": content}], response_format={"type": "json_object"}, temperature=0.2, max_tokens=1200)
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as exc:
        # Never expose secrets or provider internals to the browser. Fall back to demo mode.
        print(f"AI provider unavailable; using demo mode ({type(exc).__name__})")
        return None

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(
    description: str = Form(default=""),
    project_data: str = Form(default="{}"),
    image: Optional[UploadFile] = File(default=None),
):
    if not description.strip() and (not project_data.strip() or project_data.strip() == "{}") and image is None:
        raise HTTPException(status_code=422, detail="Provide a description, project data, or an image.")
    image_data_url = None
    image_received = image is not None
    if image is not None:
        content_type = image.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=415, detail="Uploaded file must be an image.")
        raw = await image.read()
        if not raw:
            raise HTTPException(status_code=422, detail="The uploaded image is empty. Please choose a valid image.")
        if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"Image exceeds the {MAX_UPLOAD_MB} MB upload limit.")
        image_data_url = f"data:{content_type};base64,{base64.b64encode(raw).decode('ascii')}"
    try:
        data = json.loads(project_data or "{}")
        if not isinstance(data, dict):
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=422, detail="Project data must be a valid JSON object.")

    prompt = f"Analyze this construction site input. Text: {description[:5000]}. Project data: {json.dumps(data)[:5000]}. Identify only visible/likely safety hazards, PPE concerns, cracks, quality concerns, uncertainty, and prudent next steps. Do not certify structural safety."
    result = await _model_analysis(prompt, image_data_url)
    mode: Literal["demo", "ai"] = "ai" if result and isinstance(result, dict) else "demo"
    if mode == "ai":
        try:
            findings = [Finding(**item) for item in result.get("findings", [])]
            summary = str(result.get("summary", "Image and project input reviewed."))[:1000]
            next_steps = [str(x)[:300] for x in result.get("next_steps", [])][:8]
        except Exception:
            mode = "demo"
    if mode == "demo":
        text = description.lower()
        findings = []
        if image_received:
            findings.append(Finding(category="general", title="Image submitted for review", severity="low", description="The image was received. Demo mode does not perform actual computer-vision inspection, so hazards or cracks cannot be confirmed from this upload.", recommendation="Review the image with a competent site supervisor; use clear, well-lit close-ups and include a scale reference for cracks.", confidence=0.35))
        if any(word in text for word in ["crack", "裂", "fracture"]):
            findings.append(Finding(category="crack", title="Crack mentioned in description", severity="medium", description="The input mentions a crack, but type, depth, activity, and structural significance cannot be determined from text alone.", recommendation="Photograph with a scale, record location/width and changes over time, and request assessment by a qualified structural engineer.", confidence=0.55))
        if any(word in text for word in ["helmet", "ppe", "harness", "unsafe", "scaffold", "hazard"]):
            findings.append(Finding(category="safety", title="Safety concern mentioned", severity="medium", description="The description mentions a possible site-safety or PPE concern; this is not an independently verified finding.", recommendation="Pause the affected activity if an immediate danger is suspected and follow the site's safety procedures with a competent supervisor.", confidence=0.5))
        if not findings:
            findings.append(Finding(category="general", title="Initial intake complete", severity="low", description="Inputs were accepted, but no specific hazard can be confirmed in demo mode.", recommendation="Add a detailed observation, site location, work activity, and any relevant project constraints for a more useful review.", confidence=0.25))
        summary = "Demo intake complete. No real visual model analysis was performed because an AI provider is not configured or unavailable." if image_received else "Text/project intake complete in demo mode. No professional assessment was performed."
        next_steps = ["Confirm that the image and description refer to the same site area.", "Escalate urgent safety concerns to the site supervisor immediately.", "Have suspected structural defects reviewed by a qualified engineer."]
    completeness = "complete" if image_received and description.strip() and data else "partial" if image_received or description.strip() or data else "text_only"
    return AnalysisResponse(mode=mode, summary=summary, image_received=image_received, input_completeness=completeness, findings=findings, next_steps=next_steps, disclaimer=DISCLAIMER)

@app.post("/api/plan", response_model=PlanResponse)
def plan(req: PlanRequest):
    rates = {"INR": {"economy": 1450, "standard": 1900, "premium": 2600}, "USD": {"economy": 95, "standard": 125, "premium": 175}}
    multiplier = rates[req.currency][req.quality]
    base = req.area_sqft * multiplier
    floors_factor = 1 + max(0, req.floors - 1) * 0.035
    subtotal = base * floors_factor
    contingency = subtotal * 0.10
    total = round(subtotal + contingency, 2)
    materials = [
        {"material": "Cement", "quantity": round(req.area_sqft * 0.40, 1), "unit": "bags (indicative)"},
        {"material": "Steel", "quantity": round(req.area_sqft * 3.5, 1), "unit": "kg (indicative)"},
        {"material": "Sand", "quantity": round(req.area_sqft * 0.045, 2), "unit": "m³ (indicative)"},
        {"material": "Aggregate", "quantity": round(req.area_sqft * 0.085, 2), "unit": "m³ (indicative)"},
    ]
    schedule = [
        {"phase": "Design and approvals", "duration_days": 14}, {"phase": "Site preparation and foundation", "duration_days": 21},
        {"phase": "Structure and masonry", "duration_days": 45 + req.floors * 12}, {"phase": "MEP and plastering", "duration_days": 30},
        {"phase": "Finishes and handover", "duration_days": 30},
    ]
    return PlanResponse(project_name=req.project_name, area_sqft=req.area_sqft, estimated_cost=total, currency=req.currency, contingency=round(contingency, 2), material_estimates=materials, schedule=schedule, assumptions=[f"Indicative base rate: {multiplier} {req.currency}/sq ft for {req.quality} finish.", "Rates and quantities are simplified demo assumptions, not a bill of quantities.", "Land, approvals, taxes, design fees, utilities, site conditions, and local market changes may materially affect cost."], disclaimer=DISCLAIMER)

@app.post("/api/valuation", response_model=ValuationResponse)
def valuation(req: ValuationRequest):
    condition_adjustment = {"poor": -0.20, "fair": -0.10, "good": 0.0, "excellent": 0.08}[req.condition]
    age_adjustment = min(req.age_years * 0.01, 0.50)
    adjustment = condition_adjustment - age_adjustment
    base = req.area_sqft * req.rate_per_sqft
    value = round(base * (1 + adjustment), 2)
    return ValuationResponse(location=req.location, area_sqft=req.area_sqft, base_value=round(base, 2), adjustment_percent=round(adjustment * 100, 2), indicative_value=value, currency="INR", assumptions=["User-supplied rate per sq ft is treated as a local starting estimate.", "Simple age/condition adjustment is illustrative and not a market appraisal.", "No live comparable-sales, title, zoning, or site inspection data was queried."], disclaimer=DISCLAIMER)

@app.get("/api/weather-advisory")
def weather_advisory():
    return {"mode": "demo", "status": "not_connected", "message": "Live weather is not configured. Check an authoritative local forecast before concrete pours, lifting, work at height, or other weather-sensitive activities.", "checklist": ["Check official hourly forecast and lightning alerts.", "Secure loose materials and temporary works during high winds.", "Follow site procedures for heat, rain, and lightning."]}
