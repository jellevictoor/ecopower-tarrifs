FROM python:3.12-slim

WORKDIR /app

# Install uv for faster dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY ecopower_tarrifs/ ./ecopower_tarrifs/
COPY example_usage.py ./
COPY compare_tariffs.py ./

# Install dependencies
RUN uv sync --frozen

# Run the comparison by default
CMD ["uv", "run", "python", "compare_tariffs.py"]
