# Playwright official image already ships Python + Chromium + all the
# system libraries Chromium needs (libxkbcommon, libnss3, fonts, …).
# Pinning the same version that requirements.txt installs keeps the
# Python `playwright` package and the bundled browser in lockstep.
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]
