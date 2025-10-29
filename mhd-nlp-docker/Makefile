dev:        ## hybrid dev (artifacts → S3/MinIO)
\tdocker compose -f docker-compose.dev.yml up -d --build

dev-azure-mlflow: ## hybrid dev + artifacts on Azure Blob
\tdocker compose -f docker-compose.dev.yml -f docker-compose.azure-mlflow.yml up -d --build

aws:
\tdocker compose -f docker-compose.aws.yml up -d --build

azure:
\tdocker compose -f docker-compose.azure.yml up -d --build

down:
\tdocker compose -f docker-compose.dev.yml down -v || true
\tdocker compose -f docker-compose.aws.yml down -v || true
\tdocker compose -f docker-compose.azure.yml down -v || true