"""Seed the 9 neuroimaging service definitions with full JSON schemas.

Usage:
    python scripts/seed_services.py
"""

import asyncio
import uuid

from app.database import async_session_factory
from app.models.service import PipelineDefinition, ServiceDefinition

# Default institution for dev
DEV_INSTITUTION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEV_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

# Common demographics fields
COMMON_DEMOGRAPHICS = [
    {
        "key": "patient_name",
        "type": "text",
        "label": "환자명",
        "label_en": "Patient Name",
        "required": True,
        "validation": {"min_length": 1, "max_length": 100},
        "group": "환자 정보",
    },
    {
        "key": "patient_id",
        "type": "text",
        "label": "환자 ID",
        "label_en": "Patient ID",
        "required": True,
        "group": "환자 정보",
    },
    {
        "key": "birth_date",
        "type": "date",
        "label": "생년월일",
        "label_en": "Date of Birth",
        "required": True,
        "group": "환자 정보",
    },
    {
        "key": "sex",
        "type": "radio",
        "label": "성별",
        "label_en": "Sex",
        "required": True,
        "options": [
            {"value": "M", "label": "남성"},
            {"value": "F", "label": "여성"},
        ],
        "group": "환자 정보",
    },
    {
        "key": "scan_date",
        "type": "date",
        "label": "검사일",
        "label_en": "Scan Date",
        "required": True,
        "group": "검사 정보",
    },
]

SERVICES = [
    # 1. Cortical Thickness Analysis
    {
        "name": "cortical_thickness",
        "display_name": "피질 두께 분석 (Cortical Thickness)",
        "description": "MRI T1 영상을 이용한 대뇌 피질 두께 측정 및 분석. 뇌 발달, 노화, 신경퇴행성 질환 연구에 활용.",
        "category": "MRI",
        "department": "신경과",
        "input_schema": {
            "fields": [
                *COMMON_DEMOGRAPHICS,
                {
                    "key": "clinical_diagnosis",
                    "type": "select",
                    "label": "임상 진단",
                    "label_en": "Clinical Diagnosis",
                    "required": False,
                    "options": [
                        {"value": "AD", "label": "알츠하이머병"},
                        {"value": "MCI", "label": "경도인지장애"},
                        {"value": "FTD", "label": "전두측두엽 치매"},
                        {"value": "PD", "label": "파킨슨병"},
                        {"value": "NORMAL", "label": "정상"},
                        {"value": "OTHER", "label": "기타"},
                    ],
                    "group": "임상 정보",
                },
                {
                    "key": "clinical_note",
                    "type": "textarea",
                    "label": "임상 메모",
                    "label_en": "Clinical Note",
                    "required": False,
                    "condition": {"field": "clinical_diagnosis", "value": "OTHER"},
                    "group": "임상 정보",
                },
            ]
        },
        "upload_slots": [
            {
                "key": "mri_t1",
                "label": "MRI T1 영상",
                "label_en": "MRI T1 Image",
                "required": True,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
                "description": "3D T1-weighted MRI 영상 (DICOM 시리즈 또는 NIfTI)",
                "help_text": "DICOM 파일을 폴더째 업로드하거나, NIfTI (.nii.gz) 파일을 업로드하세요.",
            }
        ],
        "options_schema": {
            "fields": [
                {
                    "key": "atlas",
                    "type": "select",
                    "label": "아틀라스",
                    "label_en": "Atlas",
                    "default": "DK",
                    "options": [
                        {"value": "DK", "label": "Desikan-Killiany"},
                        {"value": "DKT", "label": "DKT Atlas"},
                        {"value": "Destrieux", "label": "Destrieux"},
                    ],
                    "help_text": "피질 영역 구분에 사용할 아틀라스를 선택하세요.",
                },
                {
                    "key": "include_subcortical",
                    "type": "checkbox",
                    "label": "피질하 구조물 포함",
                    "label_en": "Include Subcortical Structures",
                    "default": True,
                },
            ]
        },
        "pricing": {
            "base_price": 50000,
            "per_case_price": 30000,
            "currency": "KRW",
            "volume_discounts": [
                {"min_cases": 10, "discount_percent": 10},
                {"min_cases": 50, "discount_percent": 20},
            ],
        },
        "output_schema": {
            "fields": [
                {"key": "thickness_map", "type": "image", "label": "피질 두께 맵"},
                {"key": "roi_table", "type": "csv", "label": "ROI별 두께 데이터"},
                {"key": "report_pdf", "type": "pdf", "label": "분석 보고서"},
                {"key": "comparison_chart", "type": "chart", "label": "정상군 비교 차트"},
            ]
        },
    },
    # 2. Voxel-based Morphometry
    {
        "name": "vbm",
        "display_name": "복셀 기반 형태계측 (VBM)",
        "description": "MRI T1 영상의 복셀 단위 회백질/백질 밀도 분석.",
        "category": "MRI",
        "department": "신경과",
        "input_schema": {
            "fields": [
                *COMMON_DEMOGRAPHICS,
                {
                    "key": "clinical_diagnosis",
                    "type": "select",
                    "label": "임상 진단",
                    "required": False,
                    "options": [
                        {"value": "AD", "label": "알츠하이머병"},
                        {"value": "MCI", "label": "경도인지장애"},
                        {"value": "NORMAL", "label": "정상"},
                        {"value": "OTHER", "label": "기타"},
                    ],
                    "group": "임상 정보",
                },
            ]
        },
        "upload_slots": [
            {
                "key": "mri_t1",
                "label": "MRI T1 영상",
                "required": True,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
                "description": "3D T1-weighted MRI 영상",
            }
        ],
        "options_schema": {
            "fields": [
                {
                    "key": "smoothing_fwhm",
                    "type": "number",
                    "label": "스무딩 FWHM (mm)",
                    "label_en": "Smoothing FWHM (mm)",
                    "default": 8,
                    "validation": {"min": 2, "max": 16},
                },
                {
                    "key": "tissue_type",
                    "type": "select",
                    "label": "분석 조직",
                    "default": "GM",
                    "options": [
                        {"value": "GM", "label": "회백질 (Gray Matter)"},
                        {"value": "WM", "label": "백질 (White Matter)"},
                        {"value": "BOTH", "label": "회백질 + 백질"},
                    ],
                },
            ]
        },
        "pricing": {
            "base_price": 50000,
            "per_case_price": 30000,
            "currency": "KRW",
            "volume_discounts": [{"min_cases": 10, "discount_percent": 10}],
        },
        "output_schema": {
            "fields": [
                {"key": "vbm_map", "type": "image", "label": "VBM 결과 맵"},
                {"key": "cluster_table", "type": "csv", "label": "유의미 클러스터 테이블"},
                {"key": "report_pdf", "type": "pdf", "label": "분석 보고서"},
            ]
        },
    },
    # 3. ROI Analysis FDG-PET
    {
        "name": "roi_fdg_pet",
        "display_name": "ROI FDG-PET 분석",
        "description": "FDG-PET 영상의 관심 영역(ROI) 기반 포도당 대사 정량 분석.",
        "category": "PET",
        "department": "핵의학과",
        "input_schema": {
            "fields": [
                *COMMON_DEMOGRAPHICS,
                {
                    "key": "tracer",
                    "type": "select",
                    "label": "추적자",
                    "label_en": "Tracer",
                    "required": True,
                    "default": "FDG",
                    "options": [{"value": "FDG", "label": "18F-FDG"}],
                    "group": "검사 정보",
                },
                {
                    "key": "injection_dose_mbq",
                    "type": "number",
                    "label": "투여량 (MBq)",
                    "label_en": "Injection Dose (MBq)",
                    "required": False,
                    "validation": {"min": 0, "max": 1000},
                    "group": "검사 정보",
                },
            ]
        },
        "upload_slots": [
            {
                "key": "pet_fdg",
                "label": "FDG-PET 영상",
                "required": True,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
                "description": "FDG-PET 영상 (DICOM 시리즈 또는 NIfTI)",
            },
            {
                "key": "mri_t1",
                "label": "MRI T1 영상 (선택)",
                "required": False,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
                "description": "공간 정규화를 위한 MRI T1 영상 (선택사항)",
            },
        ],
        "options_schema": {
            "fields": [
                {
                    "key": "reference_region",
                    "type": "select",
                    "label": "참조 영역",
                    "default": "cerebellum",
                    "options": [
                        {"value": "cerebellum", "label": "소뇌 (Cerebellum)"},
                        {"value": "pons", "label": "교뇌 (Pons)"},
                        {"value": "whole_brain", "label": "전체 뇌"},
                    ],
                },
                {
                    "key": "atlas",
                    "type": "select",
                    "label": "ROI 아틀라스",
                    "default": "AAL",
                    "options": [
                        {"value": "AAL", "label": "AAL"},
                        {"value": "AAL3", "label": "AAL3"},
                        {"value": "Brodmann", "label": "Brodmann"},
                    ],
                },
            ]
        },
        "pricing": {
            "base_price": 50000,
            "per_case_price": 40000,
            "currency": "KRW",
            "volume_discounts": [{"min_cases": 10, "discount_percent": 10}],
        },
        "output_schema": {
            "fields": [
                {"key": "roi_suvr_table", "type": "csv", "label": "ROI별 SUVR 테이블"},
                {"key": "z_score_map", "type": "image", "label": "Z-score 맵"},
                {"key": "report_pdf", "type": "pdf", "label": "분석 보고서"},
            ]
        },
    },
    # 4. Voxel-based SPM FDG-PET
    {
        "name": "spm_fdg_pet",
        "display_name": "복셀 기반 SPM FDG-PET 분석",
        "description": "SPM을 이용한 FDG-PET 영상의 복셀 수준 통계 분석.",
        "category": "PET",
        "department": "핵의학과",
        "input_schema": {
            "fields": [
                *COMMON_DEMOGRAPHICS,
                {
                    "key": "tracer",
                    "type": "select",
                    "label": "추적자",
                    "required": True,
                    "default": "FDG",
                    "options": [{"value": "FDG", "label": "18F-FDG"}],
                    "group": "검사 정보",
                },
            ]
        },
        "upload_slots": [
            {
                "key": "pet_fdg",
                "label": "FDG-PET 영상",
                "required": True,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
            },
            {
                "key": "mri_t1",
                "label": "MRI T1 영상 (선택)",
                "required": False,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
            },
        ],
        "options_schema": {
            "fields": [
                {
                    "key": "threshold_p",
                    "type": "number",
                    "label": "통계 임계값 (p-value)",
                    "default": 0.001,
                    "validation": {"min": 0.0001, "max": 0.05},
                },
                {
                    "key": "cluster_extent",
                    "type": "number",
                    "label": "클러스터 크기 임계값 (voxels)",
                    "default": 100,
                    "validation": {"min": 10, "max": 1000},
                },
                {
                    "key": "reference_region",
                    "type": "select",
                    "label": "참조 영역",
                    "default": "cerebellum",
                    "options": [
                        {"value": "cerebellum", "label": "소뇌"},
                        {"value": "pons", "label": "교뇌"},
                    ],
                },
            ]
        },
        "pricing": {
            "base_price": 50000,
            "per_case_price": 45000,
            "currency": "KRW",
            "volume_discounts": [{"min_cases": 10, "discount_percent": 10}],
        },
        "output_schema": {
            "fields": [
                {"key": "spm_map", "type": "image", "label": "SPM 결과 맵"},
                {"key": "cluster_table", "type": "csv", "label": "클러스터 테이블"},
                {"key": "report_pdf", "type": "pdf", "label": "분석 보고서"},
            ]
        },
    },
    # 5. Molecular Image Analysis (FDG/Amyloid PET)
    {
        "name": "molecular_pet",
        "display_name": "분자영상 분석 (FDG/Amyloid PET)",
        "description": "FDG-PET 및 아밀로이드 PET 영상의 정량 분석. 알츠하이머병 진단 보조.",
        "category": "PET",
        "department": "핵의학과",
        "input_schema": {
            "fields": [
                *COMMON_DEMOGRAPHICS,
                {
                    "key": "tracer",
                    "type": "select",
                    "label": "추적자",
                    "required": True,
                    "options": [
                        {"value": "FDG", "label": "18F-FDG"},
                        {"value": "Florbetaben", "label": "18F-Florbetaben"},
                        {"value": "Flutemetamol", "label": "18F-Flutemetamol"},
                        {"value": "Florbetapir", "label": "18F-Florbetapir"},
                        {"value": "PIB", "label": "11C-PIB"},
                    ],
                    "group": "검사 정보",
                },
                {
                    "key": "injection_dose_mbq",
                    "type": "number",
                    "label": "투여량 (MBq)",
                    "required": False,
                    "validation": {"min": 0, "max": 1000},
                    "group": "검사 정보",
                },
                {
                    "key": "uptake_time_min",
                    "type": "number",
                    "label": "섭취 시간 (분)",
                    "required": False,
                    "validation": {"min": 0, "max": 180},
                    "group": "검사 정보",
                },
            ]
        },
        "upload_slots": [
            {
                "key": "pet_image",
                "label": "PET 영상",
                "required": True,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
            },
            {
                "key": "mri_t1",
                "label": "MRI T1 영상 (선택)",
                "required": False,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
            },
        ],
        "options_schema": {
            "fields": [
                {
                    "key": "reference_region",
                    "type": "select",
                    "label": "참조 영역",
                    "default": "cerebellum",
                    "options": [
                        {"value": "cerebellum", "label": "소뇌"},
                        {"value": "pons", "label": "교뇌"},
                        {"value": "whole_cerebellum", "label": "전체 소뇌"},
                    ],
                },
                {
                    "key": "quantification_method",
                    "type": "select",
                    "label": "정량화 방법",
                    "default": "SUVR",
                    "options": [
                        {"value": "SUVR", "label": "SUVR"},
                        {"value": "Centiloid", "label": "Centiloid"},
                    ],
                },
            ]
        },
        "pricing": {
            "base_price": 50000,
            "per_case_price": 50000,
            "currency": "KRW",
            "volume_discounts": [{"min_cases": 10, "discount_percent": 10}],
        },
        "output_schema": {
            "fields": [
                {"key": "suvr_map", "type": "image", "label": "SUVR 맵"},
                {"key": "roi_table", "type": "csv", "label": "ROI별 SUVR 데이터"},
                {"key": "amyloid_status", "type": "json", "label": "아밀로이드 양성/음성 판정"},
                {"key": "report_pdf", "type": "pdf", "label": "분석 보고서"},
            ]
        },
    },
    # 6. rsfMRI Connectivity Analysis
    {
        "name": "rsfmri_connectivity",
        "display_name": "휴지기 fMRI 연결성 분석 (rsfMRI)",
        "description": "휴지기 fMRI 데이터의 기능적 연결성 분석. 뇌 네트워크 연구에 활용.",
        "category": "MRI",
        "department": "신경과",
        "input_schema": {
            "fields": [
                *COMMON_DEMOGRAPHICS,
                {
                    "key": "tr_ms",
                    "type": "number",
                    "label": "TR (ms)",
                    "label_en": "Repetition Time (ms)",
                    "required": False,
                    "validation": {"min": 100, "max": 10000},
                    "group": "검사 정보",
                    "help_text": "fMRI 스캔의 반복 시간 (TR). DICOM에서 자동 추출 가능.",
                },
            ]
        },
        "upload_slots": [
            {
                "key": "fmri_resting",
                "label": "휴지기 fMRI 영상",
                "required": True,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 500,
                "description": "4D 휴지기 fMRI 데이터",
            },
            {
                "key": "mri_t1",
                "label": "MRI T1 영상",
                "required": True,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
                "description": "공간 정규화를 위한 해부학적 T1 영상",
            },
        ],
        "options_schema": {
            "fields": [
                {
                    "key": "parcellation",
                    "type": "select",
                    "label": "뇌 구획화",
                    "default": "AAL",
                    "options": [
                        {"value": "AAL", "label": "AAL"},
                        {"value": "Power264", "label": "Power 264"},
                        {"value": "Schaefer400", "label": "Schaefer 400"},
                    ],
                },
                {
                    "key": "bandpass_low",
                    "type": "number",
                    "label": "대역통과 필터 하한 (Hz)",
                    "default": 0.01,
                    "validation": {"min": 0.001, "max": 0.1},
                },
                {
                    "key": "bandpass_high",
                    "type": "number",
                    "label": "대역통과 필터 상한 (Hz)",
                    "default": 0.08,
                    "validation": {"min": 0.05, "max": 0.5},
                },
            ]
        },
        "pricing": {
            "base_price": 50000,
            "per_case_price": 60000,
            "currency": "KRW",
            "volume_discounts": [{"min_cases": 10, "discount_percent": 10}],
        },
        "output_schema": {
            "fields": [
                {"key": "connectivity_matrix", "type": "csv", "label": "연결성 행렬"},
                {"key": "network_map", "type": "image", "label": "네트워크 맵"},
                {"key": "report_pdf", "type": "pdf", "label": "분석 보고서"},
            ]
        },
    },
    # 7. Tract-based DTI Analysis
    {
        "name": "dti_tractography",
        "display_name": "트랙트 기반 DTI 분석",
        "description": "확산텐서영상(DTI) 기반 백질 경로 분석. FA, MD 등 확산 지표 산출.",
        "category": "MRI",
        "department": "신경과",
        "input_schema": {
            "fields": [
                *COMMON_DEMOGRAPHICS,
            ]
        },
        "upload_slots": [
            {
                "key": "dti",
                "label": "DTI 영상",
                "required": True,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 500,
                "description": "확산텐서영상 (DICOM 시리즈 또는 NIfTI + bvec/bval)",
            },
            {
                "key": "bvec_bval",
                "label": "b-vector/b-value 파일 (NIfTI 사용 시)",
                "required": False,
                "accepted_types": ["CSV"],
                "accepted_extensions": [".bvec", ".bval", ".txt"],
                "min_files": 1,
                "max_files": 2,
                "help_text": "NIfTI 형식 업로드 시 bvec, bval 파일을 함께 업로드하세요.",
            },
            {
                "key": "mri_t1",
                "label": "MRI T1 영상 (선택)",
                "required": False,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
            },
        ],
        "options_schema": {
            "fields": [
                {
                    "key": "analysis_method",
                    "type": "select",
                    "label": "분석 방법",
                    "default": "TBSS",
                    "options": [
                        {"value": "TBSS", "label": "TBSS (Tract-Based Spatial Statistics)"},
                        {"value": "tractography", "label": "Tractography"},
                    ],
                },
                {
                    "key": "fa_threshold",
                    "type": "number",
                    "label": "FA 임계값",
                    "default": 0.2,
                    "validation": {"min": 0.05, "max": 0.5},
                },
            ]
        },
        "pricing": {
            "base_price": 50000,
            "per_case_price": 50000,
            "currency": "KRW",
            "volume_discounts": [{"min_cases": 10, "discount_percent": 10}],
        },
        "output_schema": {
            "fields": [
                {"key": "fa_map", "type": "image", "label": "FA 맵"},
                {"key": "md_map", "type": "image", "label": "MD 맵"},
                {"key": "tract_table", "type": "csv", "label": "트랙트별 확산 지표"},
                {"key": "report_pdf", "type": "pdf", "label": "분석 보고서"},
            ]
        },
    },
    # 8. EEG Source Analysis
    {
        "name": "eeg_source",
        "display_name": "EEG 소스 분석",
        "description": "EEG 데이터의 뇌 전기 활동 소스 위치 추정.",
        "category": "EEG",
        "department": "신경과",
        "input_schema": {
            "fields": [
                *COMMON_DEMOGRAPHICS,
                {
                    "key": "channel_count",
                    "type": "number",
                    "label": "채널 수",
                    "label_en": "Channel Count",
                    "required": False,
                    "validation": {"min": 8, "max": 256},
                    "group": "검사 정보",
                },
                {
                    "key": "sampling_rate",
                    "type": "number",
                    "label": "샘플링 레이트 (Hz)",
                    "required": False,
                    "validation": {"min": 100, "max": 10000},
                    "group": "검사 정보",
                },
                {
                    "key": "recording_condition",
                    "type": "select",
                    "label": "기록 조건",
                    "required": False,
                    "options": [
                        {"value": "eyes_closed", "label": "눈 감은 상태"},
                        {"value": "eyes_open", "label": "눈 뜬 상태"},
                        {"value": "task", "label": "과제 수행 중"},
                        {"value": "sleep", "label": "수면"},
                    ],
                    "group": "검사 정보",
                },
            ]
        },
        "upload_slots": [
            {
                "key": "eeg_data",
                "label": "EEG 데이터",
                "required": True,
                "accepted_types": ["EEG", "EDF"],
                "accepted_extensions": [".edf", ".set", ".fdt", ".bdf", ".eeg", ".vhdr", ".zip"],
                "min_files": 1,
                "max_files": 10,
                "description": "EEG 원시 데이터 (EDF, EEGLAB SET, BrainVision 등)",
            },
            {
                "key": "mri_t1",
                "label": "MRI T1 영상 (선택)",
                "required": False,
                "accepted_types": ["DICOM", "NIfTI"],
                "accepted_extensions": [".dcm", ".nii", ".nii.gz", ".zip"],
                "min_files": 1,
                "max_files": 300,
                "help_text": "소스 추정 정확도 향상을 위한 개인 MRI (없으면 표준 헤드 모델 사용)",
            },
        ],
        "options_schema": {
            "fields": [
                {
                    "key": "source_method",
                    "type": "select",
                    "label": "소스 추정 방법",
                    "default": "eLORETA",
                    "options": [
                        {"value": "eLORETA", "label": "eLORETA"},
                        {"value": "sLORETA", "label": "sLORETA"},
                        {"value": "LCMV", "label": "LCMV Beamformer"},
                    ],
                },
                {
                    "key": "frequency_bands",
                    "type": "select",
                    "label": "주파수 대역",
                    "default": "all",
                    "options": [
                        {"value": "all", "label": "전체 대역"},
                        {"value": "delta", "label": "Delta (1-4 Hz)"},
                        {"value": "theta", "label": "Theta (4-8 Hz)"},
                        {"value": "alpha", "label": "Alpha (8-13 Hz)"},
                        {"value": "beta", "label": "Beta (13-30 Hz)"},
                        {"value": "gamma", "label": "Gamma (30-100 Hz)"},
                    ],
                },
            ]
        },
        "pricing": {
            "base_price": 50000,
            "per_case_price": 40000,
            "currency": "KRW",
            "volume_discounts": [{"min_cases": 10, "discount_percent": 10}],
        },
        "output_schema": {
            "fields": [
                {"key": "source_map", "type": "image", "label": "소스 활동 맵"},
                {"key": "roi_power", "type": "csv", "label": "ROI별 파워 데이터"},
                {"key": "report_pdf", "type": "pdf", "label": "분석 보고서"},
            ]
        },
    },
    # 9. EEG Spectral Analysis
    {
        "name": "eeg_spectral",
        "display_name": "EEG 스펙트럼 분석",
        "description": "EEG 데이터의 주파수 영역 분석. 파워 스펙트럼, 코히런스, 위상 분석.",
        "category": "EEG",
        "department": "신경과",
        "input_schema": {
            "fields": [
                *COMMON_DEMOGRAPHICS,
                {
                    "key": "channel_count",
                    "type": "number",
                    "label": "채널 수",
                    "required": False,
                    "validation": {"min": 8, "max": 256},
                    "group": "검사 정보",
                },
                {
                    "key": "sampling_rate",
                    "type": "number",
                    "label": "샘플링 레이트 (Hz)",
                    "required": False,
                    "validation": {"min": 100, "max": 10000},
                    "group": "검사 정보",
                },
                {
                    "key": "recording_condition",
                    "type": "select",
                    "label": "기록 조건",
                    "required": False,
                    "options": [
                        {"value": "eyes_closed", "label": "눈 감은 상태"},
                        {"value": "eyes_open", "label": "눈 뜬 상태"},
                        {"value": "task", "label": "과제 수행 중"},
                    ],
                    "group": "검사 정보",
                },
            ]
        },
        "upload_slots": [
            {
                "key": "eeg_data",
                "label": "EEG 데이터",
                "required": True,
                "accepted_types": ["EEG", "EDF"],
                "accepted_extensions": [".edf", ".set", ".fdt", ".bdf", ".eeg", ".vhdr", ".zip"],
                "min_files": 1,
                "max_files": 10,
                "description": "EEG 원시 데이터",
            },
        ],
        "options_schema": {
            "fields": [
                {
                    "key": "analysis_type",
                    "type": "select",
                    "label": "분석 유형",
                    "default": "power_spectrum",
                    "options": [
                        {"value": "power_spectrum", "label": "파워 스펙트럼"},
                        {"value": "coherence", "label": "코히런스"},
                        {"value": "phase", "label": "위상 분석"},
                        {"value": "all", "label": "전체"},
                    ],
                },
                {
                    "key": "epoch_length_sec",
                    "type": "number",
                    "label": "에포크 길이 (초)",
                    "default": 2,
                    "validation": {"min": 0.5, "max": 30},
                },
                {
                    "key": "artifact_rejection",
                    "type": "checkbox",
                    "label": "자동 아티팩트 제거",
                    "default": True,
                },
            ]
        },
        "pricing": {
            "base_price": 50000,
            "per_case_price": 35000,
            "currency": "KRW",
            "volume_discounts": [{"min_cases": 10, "discount_percent": 10}],
        },
        "output_schema": {
            "fields": [
                {"key": "power_spectrum", "type": "chart", "label": "파워 스펙트럼"},
                {"key": "topographic_map", "type": "image", "label": "토포그래피 맵"},
                {"key": "band_power_table", "type": "csv", "label": "주파수 대역별 파워"},
                {"key": "report_pdf", "type": "pdf", "label": "분석 보고서"},
            ]
        },
    },
]


async def seed_services() -> None:
    async with async_session_factory() as session:
        for svc_data in SERVICES:
            svc = ServiceDefinition(
                institution_id=DEV_INSTITUTION_ID,
                name=svc_data["name"],
                display_name=svc_data["display_name"],
                description=svc_data.get("description"),
                version=1,
                version_label="1.0.0",
                status="PUBLISHED",
                department=svc_data.get("department"),
                category=svc_data.get("category"),
                input_schema=svc_data.get("input_schema"),
                upload_slots=svc_data.get("upload_slots"),
                options_schema=svc_data.get("options_schema"),
                pricing=svc_data.get("pricing"),
                output_schema=svc_data.get("output_schema"),
                is_immutable=True,
                created_by=DEV_USER_ID,
            )
            session.add(svc)

            # Add default pipeline for each service
            pipeline = PipelineDefinition(
                service_id=svc.id,
                name=f"{svc_data['name']}_default",
                version="1.0.0",
                is_default=True,
                steps=[{"name": "preprocess"}, {"name": "compute"}, {"name": "postprocess"}],
                qc_rules={"auto_pass_threshold": 0.8},
                resource_requirements={"gpu": False, "memory_gb": 8, "timeout_sec": 3600},
            )
            session.add(pipeline)

        await session.commit()
        print(f"✅ Seeded {len(SERVICES)} service definitions with pipelines")


if __name__ == "__main__":
    asyncio.run(seed_services())
