#!/bin/bash
set -e

echo "Generating ThirdPartyNotices.txt..."

# Generate requirements.txt from pyproject.toml
echo "1. Compiling requirements.txt..."
uv pip compile pyproject.toml -o requirements.txt

# Create temp directory with only requirements.txt
echo "2. Creating clean workspace..."
mkdir -p .ort-temp
cp requirements.txt .ort-temp/

# Run ORT analyzer
echo "3. Running ORT analyzer..."
docker run --rm -v $(pwd)/.ort-temp:/project ghcr.io/oss-review-toolkit/ort:latest analyze -i /project -o /project/ort-results

# Generate notice file
echo "4. Generating notice file..."
docker run --rm -v $(pwd)/.ort-temp:/project ghcr.io/oss-review-toolkit/ort:latest report -i /project/ort-results/analyzer-result.yml -o /project/ort-results -f PlainTextTemplate

# Copy result
echo "5. Copying to ThirdPartyNotices.txt..."
cp .ort-temp/ort-results/NOTICE_DEFAULT ThirdPartyNotices.txt

# Cleanup
echo "6. Cleaning up..."
rm -rf .ort-temp requirements.txt

echo "✓ ThirdPartyNotices.txt generated successfully!"
