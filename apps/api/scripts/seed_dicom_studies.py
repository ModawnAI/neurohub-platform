"""Scan DICOM files on disk and register them as DicomStudy records.

Usage (from apps/api with venv activated):
    python scripts/seed_dicom_studies.py
"""

import asyncio
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# fmt: off
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# fmt: on

import pydicom  # noqa: E402
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import settings  # noqa: E402
from app.models.dicom_study import DicomSeries, DicomStudy  # noqa: E402

# Directories containing DICOM files to scan
SCAN_DIRS = [
    "/projects4/NEUROHUB/TEST/INPUT/TEST_MoNET",
]

# Default institution (first institution in DB)
DEFAULT_INSTITUTION_ID = None  # resolved at runtime


def scan_dicom_dir(base_dir: str) -> dict:
    """Walk directory tree, read DICOM headers, group by StudyInstanceUID."""
    studies: dict[str, dict] = {}
    series_map: dict[str, dict[str, dict]] = defaultdict(dict)  # study_uid -> {series_uid -> info}

    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            if not fname.lower().endswith((".dcm", ".ima", ".dicom")):
                # Try reading anyway in case it's DICOM without extension
                if "." in fname and not fname.startswith("."):
                    continue
            try:
                ds = pydicom.dcmread(fpath, stop_before_pixels=True, force=True)
            except Exception:
                continue

            study_uid = getattr(ds, "StudyInstanceUID", None)
            if not study_uid:
                continue
            study_uid = str(study_uid)

            if study_uid not in studies:
                study_date_raw = getattr(ds, "StudyDate", "")
                study_date = None
                if study_date_raw and len(study_date_raw) == 8:
                    try:
                        study_date = date(
                            int(study_date_raw[:4]),
                            int(study_date_raw[4:6]),
                            int(study_date_raw[6:8]),
                        )
                    except ValueError:
                        pass

                patient_name = str(getattr(ds, "PatientName", "")) or ""
                patient_id = str(getattr(ds, "PatientID", "")) or ""
                modality = str(getattr(ds, "Modality", "")) or ""
                study_desc = str(getattr(ds, "StudyDescription", "")) or ""

                studies[study_uid] = {
                    "study_instance_uid": study_uid,
                    "patient_id": patient_id,
                    "patient_name": patient_name,
                    "study_date": study_date,
                    "study_description": study_desc,
                    "modality": modality,
                    "num_series": 0,
                    "num_instances": 0,
                    "storage_prefix": root,
                    "source_aet": "LOCAL_SCAN",
                }

            studies[study_uid]["num_instances"] += 1

            series_uid = str(getattr(ds, "SeriesInstanceUID", ""))
            if series_uid and series_uid not in series_map[study_uid]:
                series_map[study_uid][series_uid] = {
                    "series_instance_uid": series_uid,
                    "series_number": getattr(ds, "SeriesNumber", None),
                    "series_description": str(getattr(ds, "SeriesDescription", "")) or "",
                    "modality": str(getattr(ds, "Modality", "")) or "",
                    "num_instances": 0,
                }
            if series_uid:
                series_map[study_uid][series_uid]["num_instances"] += 1

    # Set num_series counts
    for uid, study in studies.items():
        study["num_series"] = len(series_map.get(uid, {}))

    return studies, series_map


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get first institution
        result = await session.execute(text("SELECT id FROM institutions LIMIT 1"))
        row = result.first()
        if not row:
            print("ERROR: No institutions found. Seed institutions first.")
            return
        institution_id = row[0]
        print(f"Using institution: {institution_id}")

        for scan_dir in SCAN_DIRS:
            if not os.path.isdir(scan_dir):
                print(f"SKIP: {scan_dir} not found")
                continue

            print(f"\nScanning {scan_dir} ...")
            studies, series_map = scan_dicom_dir(scan_dir)
            print(f"  Found {len(studies)} studies, {sum(s['num_instances'] for s in studies.values())} total instances")

            for study_uid, study_info in studies.items():
                # Check if already exists
                existing = await session.execute(
                    text("SELECT id FROM dicom_studies WHERE institution_id = :iid AND study_instance_uid = :uid"),
                    {"iid": str(institution_id), "uid": study_uid},
                )
                if existing.first():
                    print(f"  SKIP (exists): {study_uid[:40]}...")
                    continue

                import uuid as _uuid
                study_id = _uuid.uuid4()
                await session.execute(
                    text("""
                        INSERT INTO dicom_studies
                            (id, institution_id, study_instance_uid, patient_id, patient_name,
                             study_date, study_description, modality, num_series, num_instances,
                             storage_prefix, status, source_aet, created_at, updated_at)
                        VALUES
                            (:id, :iid, :uid, :pid, :pname,
                             :sdate, :sdesc, :mod, :nseries, :ninst,
                             :prefix, :status, :aet, NOW(), NOW())
                    """),
                    {
                        "id": str(study_id),
                        "iid": str(institution_id),
                        "uid": study_info["study_instance_uid"],
                        "pid": study_info["patient_id"],
                        "pname": study_info["patient_name"],
                        "sdate": study_info["study_date"],
                        "sdesc": study_info["study_description"],
                        "mod": study_info["modality"],
                        "nseries": study_info["num_series"],
                        "ninst": study_info["num_instances"],
                        "prefix": study_info["storage_prefix"],
                        "status": "RECEIVED",
                        "aet": study_info["source_aet"],
                    },
                )

                # Add series
                for series_uid, series_info in series_map.get(study_uid, {}).items():
                    await session.execute(
                        text("""
                            INSERT INTO dicom_series
                                (id, study_id, series_instance_uid, series_number,
                                 series_description, modality, num_instances, created_at, updated_at)
                            VALUES
                                (:id, :sid, :uid, :snum, :sdesc, :mod, :ninst, NOW(), NOW())
                        """),
                        {
                            "id": str(_uuid.uuid4()),
                            "sid": str(study_id),
                            "uid": series_info["series_instance_uid"],
                            "snum": series_info["series_number"],
                            "sdesc": series_info["series_description"],
                            "mod": series_info["modality"],
                            "ninst": series_info["num_instances"],
                        },
                    )

                print(
                    f"  ADD: {study_info['patient_name'] or study_info['patient_id']} | "
                    f"{study_info['modality']} | {study_info['study_date']} | "
                    f"{study_info['num_series']} series, {study_info['num_instances']} instances"
                )

        await session.commit()
        print("\nDone! DICOM studies seeded.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
