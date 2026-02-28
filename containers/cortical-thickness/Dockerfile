FROM python:3.12-slim

LABEL maintainer="NeuroHub <admin@neurohub.com>"
LABEL description="Cortical Thickness technique — FreeSurfer recon-all wrapper"

RUN pip install --no-cache-dir nibabel numpy

WORKDIR /app
COPY entrypoint.py parse_freesurfer.py ./

# FreeSurfer is host-mounted at /opt/freesurfer
ENV FREESURFER_HOME=/opt/freesurfer
ENV NTHREADS=4
ENV NEUROHUB_SKIP_RECON=0

VOLUME ["/input", "/output"]

ENTRYPOINT ["python3", "/app/entrypoint.py"]
