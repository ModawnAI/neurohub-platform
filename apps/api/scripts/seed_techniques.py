"""Seed 18 technique modules from technical_metadata.json."""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import async_session_factory  # noqa: E402
from app.models.technique import TechniqueModule  # noqa: E402

METADATA_PATH = Path(__file__).parent / "technical_metadata.json"

# Map metadata keys to docker image placeholders (to be updated with real images)
DOCKER_IMAGES = {
    "FDG_PET": "neurohub/fdg-pet:1.0.0",
    "Amyloid_PET": "neurohub/amyloid-pet:1.0.0",
    "Tau_PET": "neurohub/tau-pet:1.0.0",
    "Cortical_Thickness": "neurohub/cortical-thickness:1.0.0",
    "VBM": "neurohub/vbm:1.0.0",
    "Diffusion_Properties": "neurohub/diffusion-properties:1.0.0",
    "Tractography": "neurohub/tractography:1.0.0",
    "EEG_Spectrum": "neurohub/eeg-spectrum:1.0.0",
    "EEG_Connectivity": "neurohub/eeg-connectivity:1.0.0",
    "EEG_MEM": "neurohub/eeg-mem:1.0.0",
    "EEG_DCM": "neurohub/eeg-dcm:1.0.0",
    "MEG_Source": "neurohub/meg-source:1.0.0",
    "MEG_Connectivity": "neurohub/meg-connectivity:1.0.0",
    "MEG_DCM": "neurohub/meg-dcm:1.0.0",
    "fMRI_Task": "neurohub/fmri-task:1.0.0",
    "fMRI_Connectivity": "neurohub/fmri-connectivity:1.0.0",
    "fMRI_DCM": "neurohub/fmri-dcm:1.0.0",
    "fMRI_MEM": "neurohub/fmri-mem:1.0.0",
}

# GPU requirements by modality
RESOURCE_REQUIREMENTS = {
    "PET": {"gpu": True, "memory_gb": 8, "cpus": 4},
    "MRI": {"gpu": True, "memory_gb": 12, "cpus": 4},
    "EEG": {"gpu": False, "memory_gb": 4, "cpus": 2},
    "MEG": {"gpu": False, "memory_gb": 8, "cpus": 4},
    "fMRI": {"gpu": True, "memory_gb": 16, "cpus": 4},
}


async def seed_techniques(session: AsyncSession) -> int:
    with open(METADATA_PATH) as f:
        metadata = json.load(f)

    created = 0
    for key, tech in metadata.items():
        existing = (await session.execute(
            select(TechniqueModule).where(TechniqueModule.key == key)
        )).scalar_one_or_none()
        if existing:
            print(f"  SKIP {key} (already exists)")
            continue

        qc_config = tech.get("qc", {})
        output_schema = {
            "outcome": tech.get("outcome", []),
            "procedure": tech.get("procedure", []),
        }

        tm = TechniqueModule(
            key=key,
            title_ko=tech["title"],
            title_en=tech["title"],  # Korean title used as fallback; can be updated
            modality=tech["modality"],
            category=tech.get("category", "General"),
            description=tech.get("description", tech.get("overview", "")),
            docker_image=DOCKER_IMAGES.get(key, f"neurohub/{key.lower()}:1.0.0"),
            version="1.0.0",
            status="ACTIVE",
            qc_config=qc_config if qc_config else None,
            output_schema=output_schema,
            resource_requirements=RESOURCE_REQUIREMENTS.get(tech["modality"], {"gpu": False, "memory_gb": 4, "cpus": 2}),
        )
        session.add(tm)
        created += 1
        print(f"  CREATE {key} ({tech['modality']}/{tech.get('category', '?')})")

    await session.flush()
    return created


async def main():
    print(f"Seeding techniques from {METADATA_PATH}")
    async with async_session_factory() as session:
        async with session.begin():
            count = await seed_techniques(session)
            await session.commit()
    print(f"Done. Created {count} technique modules.")


if __name__ == "__main__":
    asyncio.run(main())
