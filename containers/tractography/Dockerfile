FROM ubuntu:22.04

LABEL maintainer="NeuroHub <admin@neurohub.com>"
LABEL description="Tractography technique — MRtrix3 CSD + tckgen wrapper"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    libtiff5 libpng16-16 libwebp7 libzstd1 liblzma5 libjbig0 libjpeg8 libdeflate0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir nibabel numpy

WORKDIR /app
COPY entrypoint.py ./

# Host-mounted tools
ENV FSLDIR=/opt/fsl
ENV MRTRIX_DIR=/opt/mrtrix3
ENV FREESURFER_HOME=/opt/freesurfer
ENV FSLOUTPUTTYPE=NIFTI_GZ
ENV STREAMLINE_COUNT=10000
ENV LD_LIBRARY_PATH="/opt/mrtrix3/lib:/opt/fsl/lib:${LD_LIBRARY_PATH}"
ENV PATH="/opt/mrtrix3/bin:/opt/fsl/bin:/opt/fsl/share/fsl/bin:/opt/freesurfer/bin:${PATH}"

VOLUME ["/input", "/output"]

ENTRYPOINT ["python3", "/app/entrypoint.py"]
