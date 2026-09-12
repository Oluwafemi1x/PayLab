FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir ".[postgres]"
EXPOSE 8787
CMD ["paylab", "start", "--host", "0.0.0.0", "--port", "8787"]
