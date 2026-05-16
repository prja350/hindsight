FROM python:3.11-slim

RUN useradd -m -u 1000 user
WORKDIR /app

COPY --chown=user:user requirements.txt .
USER user
ENV PATH="/home/user/.local/bin:$PATH"
RUN pip install --user --no-cache-dir -r requirements.txt

COPY --chown=user:user . .
RUN mkdir -p data/db

EXPOSE 8050
CMD ["python", "-m", "ui.app"]
