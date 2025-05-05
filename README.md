# Library Management System

### This is a Library Solution that enables users to be able to:

* Get a list of books
* Get a specific book
* Order for a book
* AI service is employed to attain summary or other prompts peculiar to a specific book available in the library.

#### Tools:
* Docker for containerization
* RabbitMQ for communication between consumer and producer to asynchronously process order
* SocketIO to transfer communication and give status real-time

## Features
* Asynchronous order processing via RabbitMQ
* Real-time updates (planned/implemented) via SocketIO
    * Nested item using indentation

## Setup and Installation

### Prerequisites 

Install the following:

1.  Python 3.12.6 
2.  Pip (Python package installer)
3.  RabbitMQ Server, used Homebrew
4.  Docker & Docker Compose 

### Installation Steps

Provide step-by-step instructions.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Nobelwrite/ai-library.git
    cd NewLIB
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate # On macOS/Linux
    # .\ .venv\Scripts\activate # On Windows
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: You'll need to create a `requirements.txt` file)*

4.  **Configure Environment Variables:**
    Including: `RABBITMQ_URL`, `FLASK_SECRET_KEY`.  `.env` file (optional but recommended).
    ```plaintext
    # Example .env file content
    RABBITMQ_URL
    FLASK_SECRET_KEY=your_super_secret_key_here
    ```

5.  **Start RabbitMQ:**
    Used brew services command using `brew services start rabbitmq`

## Running the Application

Instructions on how to run the different parts.

1.  **Run the Consumer:**
    ```bash
    python consumer.py
    ```

2.  **Run the Flask/SocketIO Server:**
    ```bash
    python app.py
    ```

--- 

## API Endpoints

Describe the available API endpoints.

* **`POST /orders`**: Place a new order.
    * **Request Body:**
        ```json
        {
          "items": [
            { "book_id": 1, "quantity": 1 },
            { "book_id": 3, "quantity": 2 }
          ],
          "user_identifier": "optional_user_id"
        }
        ```
    * **Success Response (201 Created):** Order details.
    * **Error Responses (400, 500):** Error details.

* **`GET /books`**: Get list of available books.

## SocketIO Events

Describe real-time events clients can listen for.

* `connect`: Emitted when a client connects.
* `disconnect`: Emitted when a client disconnects.
* `order_received`: Emitted by server when an order is initially accepted.
    * Data: `{'order_id': '...', 'status': 'Pending'}`
* `order_error`: Emitted on queueing failure.
    * Data: `{'order_id': '...', 'error': 'Queueing Failed'}`
* `order_status_update` (Emitted by Consumer - *Implementation Note*): Ideally emitted when order status changes during processing.
    * Data: `{'order_id': '...', 'status': 'Processed' | 'Failed'}`

