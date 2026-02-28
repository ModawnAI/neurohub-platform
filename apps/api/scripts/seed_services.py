"""Seed 7 clinical services from Services_Metadata.json + link technique weights.

Reads psalmhim/neurohub Services_Metadata.json and creates:
1. Missing technique modules (SPECT_SISCOM, EEG_Source, Sleep_Apnea_Analysis)
2. 7 ServiceDefinition rows with clinical_config JSONB
3. PipelineDefinition (default) per service
4. ServiceTechniqueWeight linkages with base_weight from metadata

Usage:
    python scripts/seed_services.py
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.database import async_session_factory  # noqa: E402
from app.models.service import PipelineDefinition, ServiceDefinition  # noqa: E402
from app.models.technique import ServiceTechniqueWeight, TechniqueModule  # noqa: E402

METADATA_PATH = Path(__file__).parent / "Services_Metadata.json"

DEFAULT_INSTITUTION_ID = uuid.UUID(settings.default_institution_id)
DEFAULT_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

# Stable UUIDs for the 7 clinical services
SERVICE_UUIDS = {
    "svc_epilepsy_lesion": uuid.UUID("a0000001-0000-0000-0000-000000000001"),
    "svc_epilepsy_meds": uuid.UUID("a0000002-0000-0000-0000-000000000002"),
    "svc_sz_meds": uuid.UUID("a0000003-0000-0000-0000-000000000003"),
    "svc_dementia_dx": uuid.UUID("a0000004-0000-0000-0000-000000000004"),
    "svc_pd_dx": uuid.UUID("a0000005-0000-0000-0000-000000000005"),
    "svc_brain_checkup": uuid.UUID("a0000006-0000-0000-0000-000000000006"),
    "svc_sleep_dx": uuid.UUID("a0000007-0000-0000-0000-000000000007"),
}

PIPELINE_UUIDS = {
    "svc_epilepsy_lesion": uuid.UUID("b0000001-0000-0000-0000-000000000001"),
    "svc_epilepsy_meds": uuid.UUID("b0000002-0000-0000-0000-000000000002"),
    "svc_sz_meds": uuid.UUID("b0000003-0000-0000-0000-000000000003"),
    "svc_dementia_dx": uuid.UUID("b0000004-0000-0000-0000-000000000004"),
    "svc_pd_dx": uuid.UUID("b0000005-0000-0000-0000-000000000005"),
    "svc_brain_checkup": uuid.UUID("b0000006-0000-0000-0000-000000000006"),
    "svc_sleep_dx": uuid.UUID("b0000007-0000-0000-0000-000000000007"),
}

SERVICE_SLUGS = {
    "svc_epilepsy_lesion": "epilepsy-lesion-analysis",
    "svc_epilepsy_meds": "epilepsy-medication-response",
    "svc_sz_meds": "schizophrenia-medication-response",
    "svc_dementia_dx": "dementia-diagnosis",
    "svc_pd_dx": "parkinson-diagnosis",
    "svc_brain_checkup": "brain-health-checkup",
    "svc_sleep_dx": "sleep-diagnosis",
}

SERVICE_CATEGORIES = {
    "svc_epilepsy_lesion": "Multi-modal",
    "svc_epilepsy_meds": "EEG/fMRI",
    "svc_sz_meds": "MRI/EEG/fMRI",
    "svc_dementia_dx": "PET/MRI",
    "svc_pd_dx": "PET/MRI/fMRI",
    "svc_brain_checkup": "MRI/EEG/fMRI",
    "svc_sleep_dx": "PSG/EEG",
}

SERVICE_PRICING = {
    "svc_epilepsy_lesion": {"base_price": 200000, "currency": "KRW"},
    "svc_epilepsy_meds": {"base_price": 80000, "currency": "KRW"},
    "svc_sz_meds": {"base_price": 80000, "currency": "KRW"},
    "svc_dementia_dx": {"base_price": 150000, "currency": "KRW"},
    "svc_pd_dx": {"base_price": 100000, "currency": "KRW"},
    "svc_brain_checkup": {"base_price": 50000, "currency": "KRW"},
    "svc_sleep_dx": {"base_price": 60000, "currency": "KRW"},
}

# 3 technique modules referenced by services but missing from technical_metadata.json
EXTRA_TECHNIQUES = {
    "SPECT_SISCOM": {
        "title_ko": "SPECT SISCOM 분석",
        "title_en": "SPECT SISCOM Analysis",
        "modality": "SPECT",
        "category": "Perfusion Imaging",
        "description": "발작기와 발작간기 SPECT 영상의 차이를 MRI에 중첩하여 발작 시작 부위의 혈류 변화를 시각화하는 SISCOM 분석입니다.",
        "docker_image": "neurohub/spect-siscom:1.0.0",
        "resource_requirements": {"gpu": True, "memory_gb": 8, "cpus": 4},
    },
    "EEG_Source": {
        "title_ko": "뇌파 소스 분석 (EEG Source Localization)",
        "title_en": "EEG Source Localization",
        "modality": "EEG",
        "category": "Source Imaging",
        "description": "두피 뇌파에서 뇌 내 전류원 위치를 추정하여 발작 시작 영역이나 비정상 활동의 3차원 위치를 매핑합니다.",
        "docker_image": "neurohub/eeg-source:1.0.0",
        "resource_requirements": {"gpu": False, "memory_gb": 8, "cpus": 4},
    },
    "Sleep_Apnea_Analysis": {
        "title_ko": "수면 무호흡 분석",
        "title_en": "Sleep Apnea Analysis",
        "modality": "PSG",
        "category": "Sleep Analysis",
        "description": "수면다원검사(PSG) 데이터에서 호흡 이벤트, 산소 포화도 변화, 수면 단계를 자동 감지하여 무호흡-저호흡 지수(AHI)를 산출합니다.",
        "docker_image": "neurohub/sleep-apnea:1.0.0",
        "resource_requirements": {"gpu": False, "memory_gb": 4, "cpus": 2},
    },
}

FIELD_TRANSLATIONS = {
    "Age": "나이", "Sex": "성별", "BMI": "체질량지수",
    "Seizure_type": "발작 유형", "Seizure_frequency": "발작 빈도",
    "Age_of_onset": "발병 연령", "Medication_history": "투약 이력",
    "Medication_list": "복용 약물", "Surgery_planning_question": "수술 계획 관련 질문",
    "Symptom_severity_scale": "증상 심각도 척도", "Symptom_duration": "증상 지속 기간",
    "Cognitive_test_scores": "인지 검사 점수", "Motor_symptom_duration": "운동 증상 기간",
    "UPDRS_or_equivalent": "UPDRS 또는 동등 척도", "Sleep_questionnaire_scores": "수면 설문 점수",
    "Education_years": "교육 연수", "Sleep_quality": "수면의 질",
    "Stress_level": "스트레스 수준", "Vascular_risk_factors": "혈관 위험 인자",
    "Family_history": "가족력", "Illness_duration": "유병 기간",
    "Cognitive_testing_summary": "인지 검사 요약", "Comorbidities": "동반 질환",
    "Nonmotor_symptoms": "비운동 증상", "Sleep_status": "수면 상태",
    "Triggers": "유발 요인", "Adherence_estimate": "복약 순응도",
    "EEG_report_summary": "뇌파 검사 소견", "MRI_radiology_report": "MRI 판독 소견",
    "Neuropsych_summary": "신경심리 검사 요약",
}


def _infer_field_type(name: str) -> str:
    n = name.lower()
    if "age" in n and "onset" not in n:
        return "number"
    if "sex" in n:
        return "select"
    if "bmi" in n:
        return "number"
    if any(x in n for x in ["score", "scale", "frequency", "duration", "years"]):
        return "number"
    if any(x in n for x in ["history", "list", "summary", "question", "factors"]):
        return "textarea"
    return "text"


def _build_input_schema(svc_data: dict) -> dict:
    inp = svc_data.get("input_requirements", {})
    fields = []
    for name in inp.get("clinical_data_minimum", []):
        fields.append({
            "key": name.lower().replace(" ", "_"),
            "type": _infer_field_type(name),
            "label": FIELD_TRANSLATIONS.get(name, name.replace("_", " ")),
            "label_en": name.replace("_", " "),
            "required": True,
        })
    for name in inp.get("clinical_data_optional", []):
        fields.append({
            "key": name.lower().replace(" ", "_"),
            "type": _infer_field_type(name),
            "label": FIELD_TRANSLATIONS.get(name, name.replace("_", " ")),
            "label_en": name.replace("_", " "),
            "required": False,
        })
    return {"fields": fields}


def _slot_from_modality(name: str, required: bool) -> dict:
    key = name.lower().replace(" ", "_").replace("-", "_")
    upper = name.upper()
    if any(x in upper for x in ["MRI", "PET", "SPECT", "FLAIR", "DTI", "T1", "T2"]):
        accepted, ext = ["DICOM", "NIfTI"], [".dcm", ".zip", ".nii", ".nii.gz"]
    elif any(x in upper for x in ["EEG", "PSG"]):
        accepted, ext = ["EDF", "BDF"], [".edf", ".bdf", ".zip"]
    elif any(x in upper for x in ["MEG"]):
        accepted, ext = ["FIF", "CTF"], [".fif", ".zip"]
    elif any(x in upper for x in ["SPO2", "RESPIRATORY", "ECG", "EMG", "EOG", "SNORE", "BODY"]):
        accepted, ext = ["CSV", "EDF"], [".csv", ".edf", ".zip"]
    else:
        accepted, ext = ["DICOM", "NIfTI", "ZIP"], [".dcm", ".nii", ".zip"]
    return {
        "key": key, "label": name, "label_en": name, "required": required,
        "accepted_types": accepted, "accepted_extensions": ext,
        "min_files": 1 if required else 0, "max_files": 10,
    }


def _build_upload_slots(svc_data: dict) -> list[dict]:
    slots = []
    inp = svc_data.get("input_requirements", {})
    for section in ["imaging", "electrophysiology", "physiology"]:
        sec = inp.get(section, {})
        for group in ["mandatory_all", "mandatory_any_of"]:
            for item in sec.get(group, []):
                if isinstance(item, list):
                    for sub in item:
                        slots.append(_slot_from_modality(sub, required=True))
                else:
                    slots.append(_slot_from_modality(item, required=True))
        for item in sec.get("optional", []):
            slots.append(_slot_from_modality(item, required=False))
    seen = set()
    return [s for s in slots if not (s["key"] in seen or seen.add(s["key"]))]


async def ensure_extra_techniques(session: AsyncSession) -> None:
    for key, info in EXTRA_TECHNIQUES.items():
        existing = (await session.execute(
            select(TechniqueModule).where(TechniqueModule.key == key)
        )).scalar_one_or_none()
        if existing:
            print(f"  TECHNIQUE SKIP {key} (exists)")
            continue
        session.add(TechniqueModule(
            key=key, title_ko=info["title_ko"], title_en=info["title_en"],
            modality=info["modality"], category=info["category"],
            description=info["description"], docker_image=info["docker_image"],
            version="1.0.0", status="ACTIVE",
            resource_requirements=info["resource_requirements"],
        ))
        print(f"  TECHNIQUE CREATE {key}")
    await session.flush()


async def seed_services(session: AsyncSession) -> int:
    if not METADATA_PATH.exists():
        print(f"ERROR: {METADATA_PATH} not found")
        return 0

    with open(METADATA_PATH) as f:
        services = json.load(f)["services"]

    await ensure_extra_techniques(session)

    # Build technique key → id map
    tech_map = {
        t.key: t.id
        for t in (await session.execute(select(TechniqueModule))).scalars().all()
    }

    created = 0
    for svc_key, svc_data in services.items():
        svc_id_str = svc_data["service_id"]
        svc_uuid = SERVICE_UUIDS.get(svc_id_str)
        if not svc_uuid:
            print(f"  SKIP {svc_key} (no UUID mapping)")
            continue

        existing = (await session.execute(
            select(ServiceDefinition).where(ServiceDefinition.id == svc_uuid)
        )).scalar_one_or_none()
        if existing:
            print(f"  SERVICE SKIP {svc_data['service_name']} (exists)")
            continue

        integration = svc_data.get("integration_model", {})
        qc_policy = svc_data.get("qc_policy", {})
        techniques = svc_data.get("techniques", [])
        slug = SERVICE_SLUGS.get(svc_id_str, svc_key.lower().replace("_", "-"))

        clinical_config = {
            "fusion_method": integration.get("fusion_method", ""),
            "fusion_type": integration.get("type", ""),
            "core_outputs": integration.get("core_outputs", []),
            "qc_policy": qc_policy,
            "clinical_intent": svc_data.get("clinical_intent", ""),
            "clinical_use_level": svc_data.get("clinical_use_level", ""),
            "target_population": svc_data.get("target_population", []),
            "expected_diagnostic_scope": svc_data.get("expected_diagnostic_scope", []),
            "report_structure": svc_data.get("report_structure", []),
            "regulatory_metadata": svc_data.get("regulatory_metadata", {}),
            "contraindications_or_limits": svc_data.get("contraindications_or_limits", []),
            "minimum_dataset_profiles": svc_data.get("minimum_dataset_profiles", []),
            "technique_count": len(techniques),
        }

        svc = ServiceDefinition(
            id=svc_uuid,
            institution_id=DEFAULT_INSTITUTION_ID,
            name=slug,
            display_name=svc_data["service_name"],
            description=svc_data.get("description_public", ""),
            version=1,
            version_label=svc_data.get("service_version", "2.0.0"),
            status="PUBLISHED",
            department="신경과",
            category=SERVICE_CATEGORIES.get(svc_id_str, "General"),
            service_type="AUTOMATIC",
            requires_evaluator=False,
            is_immutable=True,
            upload_slots=_build_upload_slots(svc_data),
            input_schema=_build_input_schema(svc_data),
            output_schema=svc_data.get("output_spec"),
            pricing=SERVICE_PRICING.get(svc_id_str, {"base_price": 50000, "currency": "KRW"}),
            clinical_config=clinical_config,
            created_by=DEFAULT_USER_ID,
        )
        session.add(svc)
        await session.flush()

        # Default pipeline
        steps = [{"name": t, "type": "technique_module"} for t in techniques]
        steps += [{"name": "fusion", "type": "fusion_engine"}, {"name": "report", "type": "report_generator"}]
        session.add(PipelineDefinition(
            id=PIPELINE_UUIDS.get(svc_id_str),
            service_id=svc_uuid,
            name=f"{slug}-default",
            version=svc_data.get("service_version", "2.0.0"),
            is_default=True,
            steps=steps,
            qc_rules=qc_policy,
            resource_requirements={"gpu": True, "memory_gb": 16},
        ))

        # Link technique weights
        weights = integration.get("base_weights_default", {})
        wc = 0
        for tech_key, weight in weights.items():
            tech_id = tech_map.get(tech_key)
            if not tech_id:
                print(f"    WARNING: technique {tech_key} not found, skipping")
                continue
            session.add(ServiceTechniqueWeight(
                service_id=svc_uuid,
                technique_module_id=tech_id,
                base_weight=weight,
                is_required=(tech_key in techniques),
            ))
            wc += 1

        await session.flush()
        created += 1
        print(f"  SERVICE CREATE {svc_data['service_name']} ({len(techniques)} techniques, {wc} weights)")

    return created


async def main():
    print("Seeding 7 clinical services from Services_Metadata.json...")
    async with async_session_factory() as session:
        async with session.begin():
            count = await seed_services(session)
            await session.commit()
    print(f"Done. Created {count} clinical services.")


if __name__ == "__main__":
    asyncio.run(main())
