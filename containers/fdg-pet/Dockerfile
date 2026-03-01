FROM ubuntu:22.04

LABEL maintainer="NeuroHub <admin@neurohub.com>"
LABEL description="FDG-PET analysis — neuroan_pet MATLAB/SPM25 wrapper"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    libxmu6 libxext6 libxt6 libxrender1 libgl1-mesa-glx \
    libncurses5 libxcb1 libxkbcommon0 \
    libgdk-pixbuf-2.0-0 libgtk-3-0 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libnss3 libnspr4 libdbus-1-3 libdrm2 libgbm1 libasound2 \
    xvfb \
    ca-certificates locales coreutils \
    && rm -rf /var/lib/apt/lists/* \
    && locale-gen en_US.UTF-8

# MATLAB R2025b requires UTF-8 locale for preferences directory handling
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LANGUAGE=en_US:en

# Pre-create MATLAB preferences directory (prevents reportInvalidPrefdir crash)
RUN mkdir -p /root/.matlab/R2025b /root/.MathWorks /tmp/mathworks_tmp

# Disable MathWorks ServiceHost daemon (unnecessary in headless containers,
# and it prevents subprocess.run from returning due to pipe inheritance)
ENV MW_SERVICEHOST_DISABLE=1

RUN pip3 install --no-cache-dir nibabel numpy scipy

WORKDIR /app
COPY entrypoint.py ./

# Host-mounted paths
ENV MATLAB_HOME=/opt/matlab
ENV SPM_HOME=/opt/spm25
ENV NEUROAN_PET_HOME=/opt/neuroan_pet
ENV NEUROAN_DB_HOME=/opt/neuroan_db
ENV PATH="/opt/matlab/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/matlab/bin/glnxa64:/opt/matlab/sys/os/glnxa64:${LD_LIBRARY_PATH}"

VOLUME ["/input", "/output"]

ENTRYPOINT ["python3", "/app/entrypoint.py"]
