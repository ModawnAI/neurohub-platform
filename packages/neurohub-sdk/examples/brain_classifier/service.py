"""Example: Brain MRI Classifier Service for NeuroHub.

This demonstrates building a multi-modal AI service that:
- Accepts MRI scan files (NIfTI/DICOM)
- Takes structured patient demographics
- Returns classification results with confidence scores
- Outputs a heatmap visualization

Usage:
    python service.py  # Starts HTTP server on :8080
"""

from neurohub_sdk import BaseService, InputContext, OutputContext, ServiceConfig
from neurohub_sdk.schema import SchemaDefinition, InputField, OutputField, UploadSlot


class BrainClassifierService(BaseService):
    config = ServiceConfig(
        name="brain-classifier",
        version="1.0.0",
        display_name="뇌 MRI 분류기",
        description="T1/T2/FLAIR MRI 스캔을 분석하여 이상 유무를 분류합니다.",
        department="neurology",
        category="classification",
    )

    schema = SchemaDefinition(
        inputs=[
            InputField(
                key="patient_age",
                type="number",
                label="환자 나이",
                label_en="Patient Age",
                required=True,
                validation={"min": 0, "max": 150},
            ),
            InputField(
                key="scan_type",
                type="select",
                label="스캔 유형",
                label_en="Scan Type",
                required=True,
                options=[
                    {"value": "t1", "label": "T1"},
                    {"value": "t2", "label": "T2"},
                    {"value": "flair", "label": "FLAIR"},
                ],
            ),
            InputField(
                key="clinical_notes",
                type="textarea",
                label="임상 메모",
                label_en="Clinical Notes",
                required=False,
            ),
        ],
        uploads=[
            UploadSlot(
                key="mri_scan",
                label="MRI 스캔 파일",
                label_en="MRI Scan File",
                required=True,
                accepted_extensions=[".nii", ".nii.gz", ".dcm"],
                accepted_types=["NIfTI", "DICOM"],
                max_files=1,
            ),
        ],
        outputs=[
            OutputField(key="classification", type="text", label="분류 결과"),
            OutputField(key="confidence", type="number", label="신뢰도 (0-1)"),
            OutputField(key="findings", type="json", label="상세 소견"),
            OutputField(key="heatmap", type="file", label="관심 영역 히트맵"),
        ],
    )

    async def predict(self, ctx: InputContext) -> OutputContext:
        # 1. Read structured inputs
        age = ctx.get_input("patient_age")
        scan_type = ctx.get_input("scan_type")
        notes = ctx.get_input("clinical_notes", default="")

        # 2. Download and process files
        output = ctx.create_output()

        if ctx.has_file("mri_scan"):
            try:
                mri_bytes = await ctx.get_file("mri_scan")
                output.set_metric("input_size_bytes", len(mri_bytes))
            except Exception as e:
                output.set_metric("input_size_bytes", 0)

        # 3. Run inference (replace with your actual model)
        # In production, you'd load a PyTorch/TensorFlow model here
        classification = "normal"
        confidence = 0.92

        # Example: age-based risk adjustment
        if age > 70:
            confidence *= 0.95  # Slight uncertainty for elderly

        # 4. Set outputs
        output.set("classification", classification)
        output.set("confidence", round(confidence, 4))
        output.set("findings", {
            "primary": classification,
            "secondary_findings": [],
            "scan_quality": "good",
            "scan_type": scan_type,
            "patient_age": age,
        })

        # 5. Generate visualization (placeholder)
        heatmap = b"\x89PNG\r\n\x1a\n"  # Minimal PNG header
        output.set_file("heatmap", heatmap, "heatmap.png", "image/png")

        output.set_metric("model_version", "1.0.0")
        return output


if __name__ == "__main__":
    BrainClassifierService().serve()
