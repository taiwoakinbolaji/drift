#!/bin/bash
# Build Lambda deployment package with dependencies
# This script creates a zip file containing the Lambda function and all dependencies

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔨 Building Lambda deployment package...${NC}\n"

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="$PROJECT_ROOT/lambda"
BUILD_DIR="$PROJECT_ROOT/build/lambda"
OUTPUT_ZIP="$PROJECT_ROOT/terraform/modules/lambda/lambda_function.zip"

# Clean previous build
echo -e "${YELLOW}🧹 Cleaning previous build...${NC}"
rm -rf "$BUILD_DIR"
rm -f "$OUTPUT_ZIP"
mkdir -p "$BUILD_DIR"

# Check if requirements.txt exists
if [ ! -f "$LAMBDA_DIR/requirements.txt" ]; then
    echo -e "${RED}❌ Error: requirements.txt not found in $LAMBDA_DIR${NC}"
    exit 1
fi

# Check if drift_detector.py exists
if [ ! -f "$LAMBDA_DIR/drift_detector.py" ]; then
    echo -e "${RED}❌ Error: drift_detector.py not found in $LAMBDA_DIR${NC}"
    exit 1
fi

# Install dependencies to build directory
echo -e "${GREEN}📦 Installing Python dependencies...${NC}"
pip3 install -r "$LAMBDA_DIR/requirements.txt" -t "$BUILD_DIR" --quiet

# Check if installation was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error: Failed to install dependencies${NC}"
    exit 1
fi

# Copy Lambda function code
echo -e "${GREEN}📄 Copying Lambda function code...${NC}"
cp "$LAMBDA_DIR/drift_detector.py" "$BUILD_DIR/"

# Remove unnecessary files to reduce package size
echo -e "${YELLOW}🗑️  Removing unnecessary files...${NC}"
cd "$BUILD_DIR"
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Create zip file
echo -e "${GREEN}📦 Creating deployment package...${NC}"
zip -r "$OUTPUT_ZIP" . -q

# Get package size
PACKAGE_SIZE=$(du -h "$OUTPUT_ZIP" | cut -f1)

echo -e "\n${GREEN}✅ Lambda deployment package created successfully!${NC}"
echo -e "${GREEN}📍 Location: $OUTPUT_ZIP${NC}"
echo -e "${GREEN}📊 Size: $PACKAGE_SIZE${NC}"

# Check if package is too large (Lambda limit is 50MB zipped, 250MB unzipped)
PACKAGE_SIZE_BYTES=$(stat -f%z "$OUTPUT_ZIP" 2>/dev/null || stat -c%s "$OUTPUT_ZIP" 2>/dev/null)
if [ $PACKAGE_SIZE_BYTES -gt 52428800 ]; then
    echo -e "${RED}⚠️  Warning: Package size exceeds 50MB. Consider using Lambda Layers.${NC}"
fi

echo -e "\n${YELLOW}📝 Next steps:${NC}"
echo -e "   1. Run 'terraform init' (if not already done)"
echo -e "   2. Run 'terraform plan' to preview changes"
echo -e "   3. Run 'terraform apply' to deploy"

