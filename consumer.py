import pika
import json
import time
import os

# --- RabbitMQ Configuration ---
ORDER_QUEUE_NAME = 'order_processing_queue'
RABBITMQ_URL = os.environ.get('RABBITMQ_URL') # Use localhost if not in Docker/env var set

def process_order_inventory(order_data):
    """
    Simulates processing the order and inventory update.
    Returns True on success, False on failure.
    """
    print(f"\n [CONSUMER] Received order {order_data['order_id']}. Processing inventory updates...")
    order_id = order_data['order_id']
    items = order_data['items']
    time.sleep(2) # Simulate work

    print(f" [CONSUMER] Updating stock for order {order_id}:")
    success = True # Assume success
    for item in items:
        print(f"   - Simulating decrease stock for book {item['book_id']} by {item['quantity']}")
        # --- !!! REAL INVENTORY UPDATE LOGIC HERE (DB interaction) !!! ---

    if success:
        print(f" [CONSUMER] Inventory updated successfully for order {order_id}.")
        time.sleep(1) # Simulate more work (e.g., notifying shipping)
        print(f" [CONSUMER] Order {order_id} processing complete (simulation).")
        print(f" [CONSUMER] SIMULATING SocketIO emit: Order {order_id} status changed to Processed.")
        return True
    else:
         print(f" [CONSUMER] Inventory update FAILED for order {order_id}.")
         print(f" [CONSUMER] SIMULATING SocketIO emit: Order {order_id} status changed to Processing Failed.")
         return False

def main():
    #Sets up RabbitMQ connection, channel, consumer, and starts listening.
    connection = None
    print("Starting Consumer...")
    # Decision: Loop trying to connect to RabbitMQ in case it starts after the consumer.
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.queue_declare(queue=ORDER_QUEUE_NAME, durable=True)
            print(f' [*] Connected to RabbitMQ. Waiting for messages in queue: {ORDER_QUEUE_NAME}. To exit press CTRL+C')
            break # Exit loop once connected
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error during connection setup: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    channel.basic_qos(prefetch_count=1) # Process one message at a time

    def callback(ch, method, properties, body):
        """Function executed when a message is received."""
        print(f"\n [CONSUMER] Received raw message. Delivery Tag: {method.delivery_tag}")
        try:
            order_data = json.loads(body.decode('utf-8'))
            if process_order_inventory(order_data):
                # Acknowledge message only if processing was successful.
                print(f" [CONSUMER] Acknowledging message for order {order_data['order_id']}...")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Processing failed. Negatively acknowledge (discard). Consider DLQ in production.
                print(f" [CONSUMER] Processing FAILED for order {order_data['order_id']}. Negatively acknowledging (discarding).")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except json.JSONDecodeError:
            print(" [CONSUMER] Failed to decode JSON message body. Discarding message.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            print(f" [CONSUMER] Unexpected error processing message: {e}. Discarding message.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # Avoid requeue loops

    # Register callback and start consuming
    channel.basic_consume(queue=ORDER_QUEUE_NAME, on_message_callback=callback, auto_ack=False)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Consumer stopped.")
    except Exception as e:
        print(f"An error occurred during consumption: {e}")
    finally:
        if connection and connection.is_open:
            connection.close()
            print("RabbitMQ connection closed.")


if __name__ == '__main__':
    main()