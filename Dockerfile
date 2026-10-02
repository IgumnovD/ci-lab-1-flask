FROM python:3.12 AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .


FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=build /app .
EXPOSE 5000
CMD ["python", "-m", "flask", "--app", "run", "run", "--host=0.0.0.0"]