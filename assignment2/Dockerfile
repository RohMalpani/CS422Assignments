FROM ubuntu:24.04

# Docker supplies user-space tools; TCP_INFO and congestion control come from
# the Linux kernel of the machine running this container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy only inputs and code, not local results, plots, or the report.
COPY servers.csv run_all.py ./
COPY part1/ ./part1/
COPY part2/ ./part2/
COPY part3/ ./part3/

ENV PATH="/opt/venv/bin:${PATH}" \
    MPLBACKEND=Agg \
    PYTHONUNBUFFERED=1

# Bind-mount /app/results and /app/plots to keep generated files on the host.
# run_all.py checks the kernel, records its settings, and runs all three parts.
# Host kernel configuration (including BBR availability) must be done on the host.
CMD ["python3", "run_all.py"]
