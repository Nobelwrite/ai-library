import json
import os
import re
import uuid
import pika
from dotenv import load_dotenv
from flask import Flask, jsonify, abort, request
from flask_socketio import SocketIO
import ai_service
from data_store import books_data, orders, inventory

load_dotenv()

FLASK_SECRET = os.environ.get("FLASK_SECRET_KEY")
app = Flask(__name__)

ORDER_QUEUE_NAME = 'order_processing_queue'
RABBITMQ_URL = os.environ.get('RABBITMQ_URL')
socketio = SocketIO(app, async_mode='eventlet')

print(f"DEBUG: Initial RABBITMQ_URL value = {repr(RABBITMQ_URL)}")


#inventory = [{book_id: data['stock'] for book_id, data in books_data.items()}]

@app.route('/')
def api_root():
    return "Welcome to our Lib"

@app.route('/books', methods=['GET'])
def get_books():
    if books_data:
    #Gets a list of books
        books_list = list(books_data.values())
        return jsonify(books_list), 200
    abort(404, message="books not found")

@app.route('/books/<int:book_id>', methods=['GET'])
def get_one_book(book_id):
    #Returns details for a specific book by its ID
    book = books_data.get(book_id)
    # 2. Checks if book is found
    if book:
        #Flask automatically sends a 200 OK status code here.
        return jsonify(book)
    else:
        #     will catch this and return a standard JSON error message.
        abort(404, description=f"book with ID {book_id} not found.")


def get_rabbitmq_connection():
    """Establishes a connection to RabbitMQ."""
    # This print uses the potentially problematic RABBITMQ_URL
    print(f"Attempting to connect to RabbitMQ at {RABBITMQ_URL}...") # <<< This showed None
    # Add a check here too, just before using it
    if not RABBITMQ_URL:
        print("ERROR: RABBITMQ_URL is None or empty inside get_rabbitmq_connection!")
        return None
    try:
        params = pika.URLParameters(RABBITMQ_URL) # <<< This fails if RABBITMQ_URL is None
        connection = pika.BlockingConnection(params)
        print("RabbitMQ connection successful.")
        return connection
    except pika.exceptions.AMQPConnectionError as e:
        print(f"Error connecting to RabbitMQ: {e}")
        return None
    except Exception as e: # Catch other potential errors like the TypeError
        print(f"Error during RabbitMQ connection parameter parsing: {e}")
        return None

def send_order_to_queue(order_message):
    #Sends order data as a JSON message to the RabbitMQ queue.
    connection = None
    try:
        connection = get_rabbitmq_connection()
        if not connection:
            print("Failed to get RabbitMQ connection.")
            return False

        channel = connection.channel()

        channel.queue_declare(queue=ORDER_QUEUE_NAME, durable=True)

        message_body = json.dumps(order_message) # Convert dict to JSON string

        channel.basic_publish(
            exchange='',
            routing_key=ORDER_QUEUE_NAME,
            body=message_body,
            properties=pika.BasicProperties(delivery_mode=2) # Make message persistent
        )
        print(f" [API/PRODUCER] Sent order {order_message.get('order_id', '')} to queue '{ORDER_QUEUE_NAME}'")
        return True
    except Exception as e:
        print(f"Error sending message to RabbitMQ: {e}")
        return False
    finally:
        if connection and connection.is_open:
            connection.close()
            print("RabbitMQ connection closed.")

# --- Custom Error Handler for 404 ---
@app.route('/orders', methods=['POST'])
def create_order():
    """
    Receives order data, validates it, performs a preliminary stock check,
    creates an order record with 'Pending' status, and sends the order
    details to RabbitMQ for asynchronous processing.
    Includes debug prints before the stock comparison.
    """
    # Decision: Get JSON data from the incoming request body.
    data = request.get_json()
    #Decision: Basic validation: ensure data exists, has 'items' key, and 'items' is a list.
    if not data or 'items' not in data or not isinstance(data['items'], list):
        return jsonify({"error": "Invalid order data. 'items' list is required."}), 400 # Return 400 for bad request format.

    #Decision: Generate a unique ID for this order using UUID.
    order_id = str(uuid.uuid4())
    order_items_details = []
    order_items_message = []
    total_price = 0
    validation_error = None

    for item in data['items']:
        book_id_str = item.get('book_id')  # Get book_id (might be str or int from JSON).
        quantity = item.get('quantity', 1) # Get quantity, default to 1 if not provided.

        # Decision: Validate book_id and quantity rigorously within a try-except block.
        try:
            book_id = int(book_id_str) # Attempt to convert book_id to integer.
            # Decision: Check if the converted book_id exists in our known books.
            if book_id not in books_data:
                validation_error = f"Invalid book_id: {book_id}"
                break # Stop processing items on first error.
            # Decision: Check if quantity is an integer and is positive.
            if not isinstance(quantity, int) or quantity <= 0:
                 validation_error = f"Invalid quantity ({quantity}) for book_id: {book_id}"
                 break # Stop processing items on first error.
        except (ValueError, TypeError):
            # Decision: Handle cases where book_id couldn't be converted to int.
            validation_error = f"Invalid book_id format: {book_id_str}"
            break # Stop processing items on first error.

        # --- If no 'break' occurred, validation passed for this item ---
        # Decision: Retrieve book details using the validated integer book_id. Assumes book_id exists due to check above.
        book = books_data[book_id]
        # Decision: Safely get current stock count from INVENTORY, defaulting to 0 if book_id not in inventory.
        current_stock = inventory.get(book_id, 0)
        available_titles = []

        # Decision: Print debug info just before the comparison to inspect values and types. Use repr() for clear type representation.
        print(f"Checking item with book_id={book_id}")
        print(f" current_stock = {repr(current_stock)} (Type: {type(current_stock)})")
        print(f" quantity = {repr(quantity)} (Type: {type(quantity)})")

        # Decision: Perform the preliminary stock check. Compare integers.
        if current_stock < quantity:
            # Decision: If stock is insufficient based on current view, set error and stop processing.
            validation_error = f"Not enough stock for '{book['title']}' (ID: {book_id}). Available: {current_stock}"
            break # Exit loop, order cannot proceed.

        # --- If stock check passes, prepare item details ---
        #Safely get the price, defaulting to 0. Calculate total price.
        price = book.get('price', 0)
        #Append detailed item info for the order record.
        order_items_details.append({
            "book_id": book_id,
            "title": book['title'],
            "quantity": quantity,
            "price_per_item": price
        })
        # Decision: Append minimal info needed by the consumer to the message payload list.
        order_items_message.append({"book_id": book_id, "quantity": quantity})
        total_price += price * quantity # Accumulate total price.

    # Decision: After checking all items, see if any validation error occurred during the loop.
    if validation_error:
        return jsonify({"error": validation_error}), 400 # Return 400 Bad Request with the specific error message.

    # --- If all items validated successfully ---
    #Create the final order dictionary to be stored. Set initial status.
    new_order = {
        "order_id": order_id,
        "items": order_items_details,
        "total_price": round(total_price, 2), # Round price to 2 decimal places.
        "status": "Pending", # Initial status before consumer processing.
        "user_identifier": data.get('user_identifier', f"anon_{uuid.uuid4().hex[:6]}") # Optional user ID.
    }
    #Store the newly created order in our in-memory storage.
    orders[order_id] = new_order

    #Prepare the payload containing only essential info for the RabbitMQ message.
    message_payload = {
        "order_id": order_id,
        "items": order_items_message
    }

    message_payload = {"order_id": order_id, "items": order_items_message}

    # Decision: Attempt to send the message to the queue. This is the core producer step.
    if send_order_to_queue(message_payload):
        print(f" [API/PRODUCER] Order {order_id} created and sent to queue successfully.")
        # Decision: Optionally emit a SocketIO event to notify client immediately that order was received.
        # Emitting globally for simplicity here:
        socketio.emit('order_received', {'order_id': order_id, 'status': 'Pending'})
        print(f" [API/SOCKETIO] Emitted 'order_received' for order {order_id}")
        return jsonify(new_order), 201  # Return 201 Created

    else:
        # Handle failure to send to queue
        print(f" [API/PRODUCER] Failed to send order {order_id} to queue.")
        orders[order_id]["status"] = "Queueing Failed"
        # Optionally emit failure event via SocketIO
        socketio.emit('order_error', {'order_id': order_id, 'error': 'Queueing Failed'})
        return jsonify({"error": "Failed to queue order for processing. Please try again later."}), 500

@socketio.on('connect')
def handle_connect():
    # Decision: Log when a client connects via SocketIO.
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    # Decision: Log when a client disconnects.
    print(f"Client disconnected: {request.sid}")

@app.route('/api/v1/ai/prompt', methods=['POST'])
def handle_ai_chat():
    #Handles AI prompts """
    data = request.get_json()
    if not data or not isinstance(data.get('query'), str) or not data['query']:
        return jsonify({"error": {"message": "Invalid request. 'query' field (string) is required."}, "status": "failed"}), 400

    user_query = data['query']
    print(f"INFO [API]: Received AI query: '{user_query[:100]}...'") # Log query snippet

    try:
        # --- Get available titles (already checked for list return in service) ---
        available_titles = ai_service.get_available_book_titles()
        # Optional: Add a redundant check here if you are paranoid
        if not isinstance(available_titles, list):
             print("CRITICAL ERROR [API]: get_available_titles did not return a list!")
             # Use the specific error message structure
             return jsonify({"error": {"message": "Internal configuration error fetching allowed titles."}, "status": "failed"}), 500

        # --- Call the main AI processing function ---
        result = ai_service.get_ai_response(user_query, available_titles)

        # --- Process the structured response from the AI service ---
        if not isinstance(result, dict):
            print(f"CRITICAL ERROR [API]: ai_service.get_ai_response did not return a dict! Got: {type(result)}")
            return jsonify({"error": {"message": "Internal server error processing AI request."}, "status": "failed"}), 500

        # Check if the service returned an error payload
        if 'error' in result:
            error_payload = result['error']
            status = result.get('status', 'failed') # Get status if present
            print(f"WARN [API]: AI service returned error: {error_payload.get('message')}")
            # Determine HTTP status code (e.g., 400 for refusal, 500 for internal AI failure)
            http_status_code = 400 if status == 'refused' else 500
            return jsonify({"error": error_payload}), http_status_code
        # Check if the service returned a data payload
        elif 'data' in result:
             print("INFO [API]: AI service returned success.")
             return jsonify(result['data']), 200 # Return just the inner data part for success
        else:
             # Should not happen if ai_service returns consistent format
             print("CRITICAL ERROR [API]: AI service returned unknown structure.")
             return jsonify({"error": {"message": "Internal server error: Unknown AI response format."}, "status": "failed"}), 500

    except Exception as e:
        # Catch unexpected errors in the API handler itself
        print(f"CRITICAL ERROR [API]: Unexpected error in handle_ai_chat: {e}")
        return jsonify({"error": {"message": "An unexpected server error occurred handling AI request."}, "status": "failed"}), 500



if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)




