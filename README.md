# Code Migration Tool

This is a Streamlit application designed to automate a code migration process.

## Setup

### Prerequisites

- Python 3.7+
- Pip

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/khanh13nguyen/migration_tool.git
    cd migration_tool
    ```

2.  **Create a virtual environment:**

    **On Windows:**

    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

    **On Linux and macOS:**

    ```bash
    python3 -m venv .venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the application:**

    Create a `.env` file in the root of the project and add the following variables:

    ```
    FULL_EVIDENCE_INPUT_PATH="/path/to/your/evidence.xlsx"
    ROOT_APP_PATH="/path/to/your/root/app"
    ```

## Usage

1.  **Run the Streamlit application:**

    ```bash
    python -m streamlit run main_app.py --server.address localhost
    ```
    
    ```bash
     .\.venv\Scripts\activate
    python -m streamlit run main_app.py --server.address localhost
    ```

2.  **Open the application in your browser at `http://localhost:8501`**
