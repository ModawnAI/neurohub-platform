import asyncio
import uuid

from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models.institution import Institution, InstitutionMember
from app.models.service import PipelineDefinition, ServiceDefinition
from app.models.user import User

DEFAULT_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEFAULT_SERVICE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEFAULT_PIPELINE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
WATERMARK_SERVICE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
WATERMARK_PIPELINE_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


async def upsert_institution(session, institution_id: uuid.UUID) -> None:
    result = await session.execute(select(Institution).where(Institution.id == institution_id))
    inst = result.scalar_one_or_none()
    if inst:
        return

    session.add(
        Institution(
            id=institution_id,
            code="DEFAULT",
            name="Default Institution",
            status="ACTIVE",
        )
    )


async def upsert_user(session, institution_id: uuid.UUID) -> None:
    result = await session.execute(select(User).where(User.id == DEFAULT_USER_ID))
    user = result.scalar_one_or_none()
    if not user:
        session.add(
            User(
                id=DEFAULT_USER_ID,
                username="dev-user",
                display_name="개발 사용자",
                email="dev@neurohub.local",
                department="연구",
                is_active=True,
            )
        )

    membership = await session.execute(
        select(InstitutionMember).where(
            InstitutionMember.institution_id == institution_id,
            InstitutionMember.user_id == DEFAULT_USER_ID,
        )
    )
    if membership.scalar_one_or_none() is None:
        session.add(
            InstitutionMember(
                institution_id=institution_id,
                user_id=DEFAULT_USER_ID,
                role_scope="SYSTEM_ADMIN",
            )
        )


async def upsert_service_and_pipeline(session, institution_id: uuid.UUID) -> None:
    service_result = await session.execute(select(ServiceDefinition).where(ServiceDefinition.id == DEFAULT_SERVICE_ID))
    service = service_result.scalar_one_or_none()
    if not service:
        service = ServiceDefinition(
            id=DEFAULT_SERVICE_ID,
            institution_id=institution_id,
            name="brain-mri-basic",
            display_name="뇌 MRI 기본 분석",
            description="표준 뇌 MRI 분석 파이프라인",
            version=1,
            version_label="1.0.0",
            status="ACTIVE",
            department="영상의학과",
            service_type="AUTOMATIC",
            requires_evaluator=False,
            inputs_schema={
                "required": ["dicom_t1"],
                "properties": {
                    "dicom_t1": {"type": "file", "label": "T1 DICOM"},
                },
            },
            options_schema={
                "properties": {
                    "fast_mode": {"type": "boolean", "default": False},
                },
            },
            created_by=DEFAULT_USER_ID,
        )
        session.add(service)

    pipeline_result = await session.execute(
        select(PipelineDefinition).where(PipelineDefinition.id == DEFAULT_PIPELINE_ID)
    )
    pipeline = pipeline_result.scalar_one_or_none()
    if pipeline:
        return

    session.add(
        PipelineDefinition(
            id=DEFAULT_PIPELINE_ID,
            service_id=DEFAULT_SERVICE_ID,
            name="brain-mri-basic-default",
            version="1.0.0",
            is_default=True,
            steps=[
                {"name": "preprocess", "image": "neurohub/preprocess:1.0.0"},
                {"name": "segment", "image": "neurohub/segment:1.0.0"},
                {"name": "report", "image": "neurohub/report:1.0.0"},
            ],
            qc_rules={"min_score": 0.85},
            resource_requirements={"gpu": False, "memory_gb": 8},
        )
    )


async def upsert_watermark_service(session, institution_id: uuid.UUID) -> None:
    result = await session.execute(
        select(ServiceDefinition).where(ServiceDefinition.id == WATERMARK_SERVICE_ID)
    )
    if result.scalar_one_or_none():
        return

    session.add(
        ServiceDefinition(
            id=WATERMARK_SERVICE_ID,
            institution_id=institution_id,
            name="image-watermark-demo",
            display_name="이미지 워터마크 데모",
            description="전문가가 이미지를 검토하고 워터마크를 추가하는 데모 서비스",
            version=1,
            version_label="1.0.0",
            status="ACTIVE",
            department="연구",
            service_type="HUMAN_IN_LOOP",
            requires_evaluator=True,
            pricing={"base_price": 1000, "per_case_price": 0, "currency": "KRW"},
            upload_slots=[
                {
                    "key": "image",
                    "label": "이미지 파일",
                    "label_en": "Image File",
                    "required": True,
                    "accepted_types": ["JPEG", "PNG"],
                    "accepted_extensions": [".jpg", ".jpeg", ".png"],
                    "min_files": 1,
                    "max_files": 1,
                }
            ],
            input_schema={
                "fields": [
                    {
                        "key": "description",
                        "type": "textarea",
                        "label": "이미지 설명",
                        "label_en": "Image Description",
                        "required": False,
                    }
                ]
            },
            created_by=DEFAULT_USER_ID,
        )
    )

    pipeline_result = await session.execute(
        select(PipelineDefinition).where(PipelineDefinition.id == WATERMARK_PIPELINE_ID)
    )
    if not pipeline_result.scalar_one_or_none():
        session.add(
            PipelineDefinition(
                id=WATERMARK_PIPELINE_ID,
                service_id=WATERMARK_SERVICE_ID,
                name="watermark-demo-default",
                version="1.0.0",
                is_default=True,
                steps=[{"name": "watermark", "type": "human_review"}],
                qc_rules={},
                resource_requirements={"gpu": False, "memory_gb": 2},
            )
        )


async def main() -> None:
    institution_id = uuid.UUID(settings.default_institution_id)

    async with async_session_factory() as session:
        await upsert_institution(session, institution_id)
        await upsert_user(session, institution_id)
        await upsert_service_and_pipeline(session, institution_id)
        await upsert_watermark_service(session, institution_id)
        await session.commit()

    print("Seed completed")
    print(f"institution_id={institution_id}")
    print(f"user_id={DEFAULT_USER_ID}")
    print(f"service_id={DEFAULT_SERVICE_ID}")
    print(f"pipeline_id={DEFAULT_PIPELINE_ID}")
    print(f"watermark_service_id={WATERMARK_SERVICE_ID}")
    print(f"watermark_pipeline_id={WATERMARK_PIPELINE_ID}")


if __name__ == "__main__":
    asyncio.run(main())
