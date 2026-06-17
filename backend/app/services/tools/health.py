"""Body metrics, body-weight logging, health profile and blood biomarker tools."""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fitness import (
    BloodMarker,
    BodyWeightLog,
    DayExercise,
    ExerciseResult,
    InjuryEpisode,
    PlanDay,
    PlanWeek,
    WorkoutLog,
    WorkoutPlan,
    WorkoutStatus,
)

logger = logging.getLogger(__name__)


HEALTH_TOOLS = [
    {
        "name": "get_body_metrics",
        "description": "Get the user's bodyweight history trend.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number of bodyweight entries to return (default 12)",
                    "default": 12
                }
            }
        }
    },
    {
        "name": "log_body_weight",
        "description": "Record a new bodyweight measurement.",
        "parameters": {
            "type": "object",
            "properties": {
                "weight_kg": {
                    "type": "number",
                    "description": "Bodyweight in kilograms (e.g. 82.5)"
                },
                "body_fat_pct": {
                    "type": "number",
                    "description": "Optional body-fat percentage"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes (e.g. 'morning weight')"
                }
            },
            "required": ["weight_kg"]
        }
    },
    {
        "name": "get_health_profile",
        "description": "Get structured injuries and health constraints for safe programming. Consult this to avoid loading injured areas.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_blood_markers",
        "description": "Get blood test panel results — the latest full panel, or the history trend of one marker.",
        "parameters": {
            "type": "object",
            "properties": {
                "marker": {
                    "type": "string",
                    "description": "Optional marker key (e.g. 'HDL', 'testosterone') to get its trend history. Empty = latest full panel."
                }
            }
        }
    },
    {
        "name": "log_blood_markers",
        "description": "Record a new blood test panel.",
        "parameters": {
            "type": "object",
            "properties": {
                "measured_at": {
                    "type": "string",
                    "description": "Date of draw, ISO format YYYY-MM-DD"
                },
                "markers": {
                    "type": "array",
                    "description": "List of markers with value, unit, ref range",
                    "items": {
                        "type": "object",
                        "properties": {
                            "marker": {
                                "type": "string",
                                "description": "Canonical key, e.g. 'HDL'"
                            },
                            "display_name": {
                                "type": "string",
                                "description": "Friendly label, e.g. 'HDL Cholesterol'"
                            },
                            "value": {
                                "type": "string",
                                "description": "Measured value (e.g. 1.2 or '> 120')"
                            },
                            "unit": {
                                "type": "string",
                                "description": "Unit of measurement (e.g. 'mmol/L')"
                            },
                            "ref_text": {
                                "type": "string",
                                "description": "Reference range"
                            },
                            "flag": {
                                "type": "string",
                                "description": "low | high | normal"
                            }
                        },
                        "required": ["marker", "value"]
                    }
                },
                "lab_name": {
                    "type": "string",
                    "description": "Optional lab name"
                }
            },
            "required": ["measured_at", "markers"]
        }
    },
]


class HealthToolsMixin:
    """Body metrics, body-weight logging, health profile and blood biomarker tools."""

    async def _get_body_metrics(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get the user's bodyweight history trend"""
        limit = args.get("limit", 12)
        if limit <= 0 or limit > 100:
            limit = 12

        try:
            query = (
                select(BodyWeightLog)
                .where(BodyWeightLog.user_id == self.user_id)
                .order_by(BodyWeightLog.logged_at.desc())
                .limit(limit)
            )
            result = await self.db.execute(query)
            logs = result.scalars().all()

            weights = []
            for log in logs:
                weights.append({
                    "weight_kg": log.weight_kg,
                    "body_fat_pct": log.body_fat_pct,
                    "notes": log.notes,
                    "logged_at": log.logged_at.isoformat(),
                })

            return {
                "bodyweight_log": weights,
            }
        except Exception as e:
            logger.error(f"get_body_metrics failed: {e}")
            return {"error": str(e)}

    async def _log_body_weight(self, args: dict[str, Any]) -> dict[str, Any]:
        """Record a new bodyweight measurement"""
        weight_kg = args.get("weight_kg")
        body_fat_pct = args.get("body_fat_pct")
        notes = args.get("notes")

        if not weight_kg or weight_kg <= 0 or weight_kg > 400:
            return {"error": "weight_kg must be a realistic positive number"}

        try:
            log = BodyWeightLog(
                id=uuid.uuid4(),
                user_id=self.user_id,
                weight_kg=weight_kg,
                body_fat_pct=body_fat_pct,
                notes=notes,
                logged_at=datetime.utcnow()
            )
            self.db.add(log)
            await self.db.commit()
            return {"logged": True, "weight_kg": weight_kg}
        except Exception as e:
            await self.db.rollback()
            logger.error(f"log_body_weight failed: {e}")
            return {"error": str(e)}

    async def _get_health_profile(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get active and past injuries for safe programming"""
        try:
            query = (
                select(InjuryEpisode)
                .where(InjuryEpisode.user_id == self.user_id)
                .order_by(InjuryEpisode.occurred_at.desc())
            )
            result = await self.db.execute(query)
            episodes = result.scalars().all()

            injuries = []
            for ep in episodes:
                injuries.append({
                    "body_part": ep.body_part,
                    "description": ep.description,
                    "severity": ep.severity,
                    "status": ep.status.value if hasattr(ep.status, "value") else str(ep.status),
                    "occurred_at": ep.occurred_at.isoformat() if ep.occurred_at else None,
                    "resolved_at": ep.resolved_at.isoformat() if ep.resolved_at else None,
                    "exercises_to_avoid": ep.exercises_to_avoid,
                    "notes": ep.notes,
                })

            return {
                "injuries": injuries,
            }
        except Exception as e:
            logger.error(f"get_health_profile failed: {e}")
            return {"error": str(e)}

    async def _get_blood_markers(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get blood test panel results — the latest full panel, or the history trend of one marker"""
        marker = args.get("marker")

        try:
            if marker and marker.strip():
                query = (
                    select(BloodMarker)
                    .where(BloodMarker.user_id == self.user_id)
                    .where(func.lower(BloodMarker.marker) == marker.strip().lower())
                    .order_by(BloodMarker.measured_at.asc())
                )
                result = await self.db.execute(query)
                rows = result.scalars().all()
                trend = []
                for r in rows:
                    trend.append({
                        "marker": r.marker,
                        "display_name": r.display_name,
                        "value_text": r.value_text,
                        "value_num": r.value_num,
                        "unit": r.unit,
                        "ref_text": r.ref_text,
                        "flag": r.flag,
                        "measured_at": r.measured_at.isoformat() if r.measured_at else None,
                        "lab_name": r.lab_name,
                    })
                return {"marker": marker, "data_points": len(trend), "trend": trend}

            # If no marker, return latest date's full panel
            last_date_query = select(func.max(BloodMarker.measured_at)).where(BloodMarker.user_id == self.user_id)
            last_date_res = await self.db.execute(last_date_query)
            latest_date = last_date_res.scalar()

            if latest_date is None:
                return {"latest_date": None, "panel": [], "note": "No lab results recorded yet."}

            panel_query = (
                select(BloodMarker)
                .where(BloodMarker.user_id == self.user_id)
                .where(BloodMarker.measured_at == latest_date)
                .order_by((BloodMarker.flag != "normal").desc(), BloodMarker.marker)
            )
            panel_res = await self.db.execute(panel_query)
            rows = panel_res.scalars().all()

            panel = []
            out_of_range = []
            for r in rows:
                item = {
                    "marker": r.marker,
                    "display_name": r.display_name,
                    "value_text": r.value_text,
                    "value_num": r.value_num,
                    "unit": r.unit,
                    "ref_text": r.ref_text,
                    "flag": r.flag,
                    "measured_at": r.measured_at.isoformat() if r.measured_at else None,
                }
                panel.append(item)
                if r.flag and r.flag != "normal":
                    out_of_range.append(item)

            return {
                "latest_date": latest_date.isoformat(),
                "out_of_range": out_of_range,
                "panel": panel,
            }
        except Exception as e:
            logger.error(f"get_blood_markers failed: {e}")
            return {"error": str(e)}

    async def _log_blood_markers(self, args: dict[str, Any]) -> dict[str, Any]:
        """Record a new blood test panel"""
        measured_at_str = args.get("measured_at")
        markers = args.get("markers")
        lab_name = args.get("lab_name")

        if not measured_at_str or not markers:
            return {"error": "measured_at and markers list are required"}

        try:
            measured_date = datetime.strptime(measured_at_str.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            return {"error": "measured_at must be YYYY-MM-DD"}

        saved = []
        errors = []
        try:
            for idx, m in enumerate(markers):
                key = (m.get("marker") or "").strip()
                if not key:
                    errors.append({"index": idx, "error": "missing marker key"})
                    continue
                raw_val = m.get("value")
                value_text = str(raw_val) if raw_val is not None else None
                value_num = None
                if isinstance(raw_val, (int, float)):
                    value_num = float(raw_val)
                elif isinstance(raw_val, str):
                    cleaned = raw_val.replace(",", ".").lstrip("<>≤≥ ").strip()
                    try:
                        value_num = float(cleaned)
                    except ValueError:
                        value_num = None

                db_marker = BloodMarker(
                    id=uuid.uuid4(),
                    user_id=self.user_id,
                    marker=key,
                    display_name=m.get("display_name"),
                    value_num=value_num,
                    value_text=value_text,
                    unit=m.get("unit"),
                    ref_text=m.get("ref_text"),
                    flag=m.get("flag") or "normal",
                    measured_at=measured_date,
                    lab_name=lab_name,
                    created_at=datetime.utcnow()
                )
                self.db.add(db_marker)
                saved.append(key)

            await self.db.commit()
            payload = {"saved_count": len(saved), "saved": saved, "measured_at": measured_at_str}
            if errors:
                payload["errors"] = errors
            return payload
        except Exception as e:
            await self.db.rollback()
            logger.error(f"log_blood_markers failed: {e}")
            return {"error": str(e)}
