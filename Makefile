# Makefile for the Migration Tool project

# Variables
PYTHON = python3
ACTIVATE = . .venv/bin/activate

# Phony targets
.PHONY: all install lint format test run clean

# Default target
all: run

# Install dependencies
install:
	@echo "Installing dependencies..."
	$(PYTHON) -m venv .venv
	$(ACTIVATE) && pip install -r requirements.txt

# Lint the code
lint:
	@echo "Linting code..."
	$(ACTIVATE) && flake8 .

# Format the code
format:
	@echo "Formatting code..."
	$(ACTIVATE) && black .

# Run tests
test:
	@echo "Running tests..."
	$(ACTIVATE) && pytest

# Run the application
run:
	@echo "Running the application..."
	$(ACTIVATE) && streamlit run main_app.py 

# Clean up the project directory
clean:
	@echo "Cleaning up..."
	rm -rf .venv
	rm -rf __pycache__
	rm -f *.pyc
	rm -f *.pyo
