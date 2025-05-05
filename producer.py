"""import pika
import os
import json # To encode messages as JSON strings

# Define queue name
ORDER_QUEUE_NAME = 'order_processing_queue'
RABBITMQ_URL = os.environ.get('RABBITMQ_URL')"""

"""def get_rabbitmq_connection():
    #Establishes a connection to RabbitMQ.
    # Decision: Encapsulate connection logic for reuse and error handling.
    #print(f"Attempting to connect to RabbitMQ at {RABBITMQ_URL}...")
    try:
    #handles errors, in case of any
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        print("RabbitMQ connection successful.")
        return connection
    except pika.exceptions.AMQPConnectionError as e:
        print(f"Error connecting to RabbitMQ: {e}")
        return None"""

"""def get_rabbitmq_connection():
    #Establishes a connection to RabbitMQ
    rabbitmq_url = os.environ.get('RABBITMQ_URL')
    print(f"Attempting to connect to RabbitMQ at {rabbitmq_url}...")
    try:
        # Parse the URL and create connection parameters
        params = pika.URLParameters(rabbitmq_url)
        # Establish the connection
        connection = pika.BlockingConnection(params)
        print("RabbitMQ connection successful.")
        return connection
    except pika.exceptions.AMQPConnectionError as e:
        print(f"Error connecting to RabbitMQ: {e}")
        return None"""

"""def get_rabbitmq_channel(connection):
    #Creates a channel and declares the queue.
    if not connection or connection.is_closed:
        print("RabbitMQ connection is not available.")
        return None
    try:
        # Create a communication channel
        channel = connection.channel()
        # Declare the queue. durable=True ensures the queue survives RabbitMQ restarts.
        # If the queue already exists, this command does nothing unless parameters differ.
        channel.queue_declare(queue=ORDER_QUEUE_NAME, durable=True)
        print(f"Queue '{ORDER_QUEUE_NAME}' declared successfully.")
        return channel
    except Exception as e:
        print(f"Error getting RabbitMQ channel or declaring queue: {e}")
        return None"""


"""def send_order_to_queue(order_data):
    #Sends order data as a message to the RabbitMQ queue.
    connection = None # Ensure connection is closed even if errors occur mid-way
    try:
        # Get a connection and channel
        connection = get_rabbitmq_connection()
        channel = get_rabbitmq_channel(connection)

        if not channel:
            print("Failed to get RabbitMQ channel. Cannot send order.")
            return False

        # Convert the order dictionary to a JSON string (RabbitMQ messages are byte streams)
        message_body = json.dumps(order_data)

        # Publish the message to the specified queue
        channel.basic_publish(
            exchange='', # Default exchange
            routing_key=ORDER_QUEUE_NAME, # The queue name
            body=message_body,
            # Make message persistent (survives broker restart if queue is durable)
            properties=pika.BasicProperties(
                delivery_mode=2, # make message persistent
            )
        )
        print(f" [x] Sent order {order_data.get('id', '')} to queue '{ORDER_QUEUE_NAME}'")
        return True

    except Exception as e:
        # Log any errors during the publishing process
        print(f"Error sending message to RabbitMQ: {e}")
        return False
    finally:
        # Ensure the connection is closed cleanly
        if connection and connection.is_open:
            connection.close()
            print("RabbitMQ connection closed.")"""