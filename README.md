# Fraud Detection Platform

A platform for detecting and preventing fraudulent transactions using machine learning and rule-based systems.

## Architecture

> _To be defined as the project evolves._

## Tech Stack

- **Language**: Python 3.11+
- **ML**: scikit-learn, XGBoost (planned)
- **API**: FastAPI (planned)
- **Database**: PostgreSQL (planned)
- **Queue**: Redis / Kafka (planned)

## Prerequisites

- Python 3.11+
- pip / Poetry

## Quick Start

```bash
# Clone the repo
git clone git@github.com:razaHamdani/fraud-detection-platform.git
cd fraud-detection-platform

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

> _Configuration details will be added as services are implemented._

## Testing

```bash
pytest
```

## Project Structure

```
fraud-detection-platform/
├── README.md
├── .gitignore
├── requirements.txt          # (to be created)
├── src/                      # Application source code
├── tests/                    # Test suite
├── data/                     # Data directory (gitignored)
├── models/                   # Trained models (gitignored)
└── docs/                     # Documentation
```
