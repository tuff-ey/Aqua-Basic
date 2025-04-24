# Aqua Basic

Aqua Basic is a FastAPI-based water level monitoring and management system. It uses sensor readings to track water levels, detect leaks, and manage filling and draining operations. The project is designed to provide real-time insights into water usage and tank status.

---

## Features

- **Real-Time Monitoring**: Tracks water levels, water percentage, and water volume in real-time.
- **Leak Detection**: Detects potential leaks based on time and water level changes.
- **Filling and Draining Validation**: Validates sensor readings to ensure accurate water level tracking.
- **CSV Data Management**: Stores sensor readings, past fillings, and other data in CSV files.
- **API Endpoints**: Provides RESTful API endpoints for accessing and managing data.
- **Secure Access**: Uses API key-based authentication for secure access to endpoints.

---

## Project Structure
Aqua Basic/ 
├── app/ 
│ ├── __init__.py 
│ ├── config.py # Configuration settings for the system 
│ ├── csv_handler.py # Handles reading and writing to CSV files 
│ ├── data_analysis.py # Performs data analysis (e.g., leak detection) 
│ ├── processor.py # Validates and processes sensor readings 
│ ├── schemas.py # Defines data models for API requests and responses 
│ ├── security.py # Implements API key-based authentication 
│ ├── utils.py # Utility functions (e.g., time formatting) 
├── data/ 
│ ├── data.csv # Stores real-time sensor readings 
│ ├── past_fillings.csv # Stores past filling session data 
├── main.py # Main application file with API endpoints 
├── requirements.txt # Python dependencies 
├── Dockerfile # Docker configuration for containerization 
├── .gitignore # Git ignore file

---

## API Endpoints

### 1. **Get Latest Reading**
- **Endpoint**: `/get_latest_reading`
- **Method**: `GET`
- **Description**: Retrieves the latest water level reading from the CSV file.
- **Authentication**: Requires API key.

### 2. **Post Latest Reading**
- **Endpoint**: `/post_latest_reading`
- **Method**: `POST`
- **Description**: Posts a new water level reading and updates the CSV file.
- **Authentication**: Requires API key.

### 3. **Get Past Fillings**
- **Endpoint**: `/past_fillings`
- **Method**: `GET`
- **Description**: Retrieves a summary of past filling sessions.
- **Authentication**: Requires API key.

### 4. **Download Data Files**
- **Endpoints**:
  - `/files/data`: Download `data.csv`.
  - `/files/past_fillings`: Download `past_fillings.csv`.
  - `/files/sensor_readings`: Download `sensor_readings.csv`.
- **Method**: `GET`
- **Description**: Provides access to CSV files for data analysis.
- **Authentication**: Requires API key.

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Docker (optional, for containerization)

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/aqua-basic.git
   cd aqua-basic

2. Install dependencies:
    pip install -r requirements.txt

3. Run the application:
    uvicorn main:app --reload

Access the API:

    Swagger UI: http://localhost:8000/docs
    ReDoc: http://localhost:8000/redoc

### Docker Usage
1. Build the Docker Image
docker build -t aqua-basic .

2.Run the Docker Container
docker run -p 8000:8000 aqua-basic

###Configuration
The project uses the app/config.py file for configuration.

###Security
The project uses API key-based authentication. Add your API keys in app/security.py under the VALID_API_KEYS dictionary.

###Data Files
    data.csv: Stores real-time water level readings.
    past_fillings.csv: Stores summaries of past filling sessions.

###Contact
For questions or support, please contact:

Email: tufaylfayaz@gmail.com