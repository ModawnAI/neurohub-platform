"""Example inference.py for experts to use as a template."""
from neurohub_sdk import NeuroHubContext


def run(ctx: NeuroHubContext):
    """
    This is the standard entry point for a NeuroHub analysis model.

    1. Get inputs via ctx.get_input(slot_name)
    2. Load model weights via ctx.load_model(filename)
    3. Run your analysis
    4. Save results via ctx.save_output(name, data)
    5. Save metrics via ctx.save_metric(name, value)
    """
    # Example: cortical thickness analysis
    mri_path = ctx.get_input("mri_t1")
    atlas = ctx.get_option("atlas", default="AAL3")

    # Load model (example)
    # model = torch.load(ctx.load_model("cortex_model.pt"))

    # Run analysis (placeholder)
    ctx.report_progress(50, "Processing MRI")

    # Save outputs
    # ctx.save_output("thickness_map", output_nifti_path)
    ctx.save_metric("confidence", 0.95)
    ctx.save_metric("quality_score", 0.88)

    ctx.report_progress(100, "Done")
