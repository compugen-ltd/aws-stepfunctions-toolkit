#!/bin/bash
set -e

echo "Generating ThirdPartyNotices.txt..."

# Generate requirements.txt from pyproject.toml
echo "1. Compiling requirements.txt..."
uv pip compile pyproject.toml -o requirements.txt

# Create temp directory with only requirements.txt
echo "2. Creating clean workspace..."
rm -rf .ort-temp
mkdir -p .ort-temp
cp requirements.txt .ort-temp/

# Run ORT analyzer
echo "3. Running ORT analyzer..."
docker run --rm -v $(pwd)/.ort-temp:/project ghcr.io/oss-review-toolkit/ort:latest \
    analyze \
    -i /project \
    -o /project/ort-results

# Run ORT scanner to get copyright information
echo "4. Running ORT scanner..."
docker run --rm \
	-v $(pwd)/.ort-temp:/project \
	-v $(pwd)/ossconfig.yaml:/home/ort/.ort/config/config.yml \
    -v $(pwd)/.scan-results:/tmp/ort/scan-results \
	ghcr.io/oss-review-toolkit/ort:latest \
    scan \
    -i /project/ort-results/analyzer-result.yml \
    -o /project/ort-results

# Generate notice file
echo "5. Generating notice file..."
docker run --rm -v $(pwd)/.ort-temp:/project ghcr.io/oss-review-toolkit/ort:latest \
    report \
    -i /project/ort-results/scan-result.yml \
    -o /project/ort-results \
    -f PlainTextTemplate \
    -O PlainTextTemplate=template.id=NOTICE_SUMMARY

# Copy result
echo "6. Copying to ThirdPartyNotices.txt..."
cp .ort-temp/ort-results/NOTICE_DEFAULT ThirdPartyNotices.txt

# Cleanup
echo "7. Cleaning up..."
rm -rf .ort-temp requirements.txt

echo "✓ ThirdPartyNotices.txt generated successfully!"
