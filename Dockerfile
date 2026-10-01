# Agentic Code Reviewer — production container
FROM python:3.12-slim

# git is required at runtime: ml_impact_predictor.py and feature_engineering.py
# shell out to `git clone` to fetch any repo the user analyzes.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloned target repos are ephemeral scratch space — do not bake them into the image.
RUN rm -rf repositories && mkdir -p repositories

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
    "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]