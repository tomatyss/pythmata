import json
import logging
import asyncio
from typing import Any, Callable, Dict, Optional

import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue

from pythmata.core.config import Settings

logger = logging.getLogger(__name__)

class EventBus:
    """Event bus for handling BPMN events using RabbitMQ."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.connection: Optional[Connection] = None
        self.channel: Optional[Channel] = None
        self.exchange: Optional[Exchange] = None
        self._event_handlers: Dict[str, list[Callable]] = {}

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            # Connect with retry logic
            for attempt in range(self.settings.rabbitmq.connection_attempts):
                try:
                    self.connection = await aio_pika.connect_robust(
                        str(self.settings.rabbitmq.url)
                    )
                    break
                except Exception as e:
                    if attempt == self.settings.rabbitmq.connection_attempts - 1:
                        raise
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(self.settings.rabbitmq.retry_delay)

            # Create channel and exchange
            self.channel = await self.connection.channel()
            self.exchange = await self.channel.declare_exchange(
                "pythmata.events",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            logger.info("Successfully connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None
            self.exchange = None

    async def publish(self, routing_key: str, data: Dict[str, Any]) -> None:
        """Publish an event to RabbitMQ.
        
        Args:
            routing_key: The routing key for the event (e.g., "process.started")
            data: The event data to publish
        """
        if not self.exchange:
            raise RuntimeError("Not connected to RabbitMQ")

        message = aio_pika.Message(
            body=json.dumps(data).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )

        await self.exchange.publish(message, routing_key=routing_key)
        logger.debug(f"Published event {routing_key}: {data}")

    async def subscribe(
        self,
        routing_key: str,
        callback: Callable[[Dict[str, Any]], None],
        queue_name: Optional[str] = None
    ) -> None:
        """Subscribe to events with the given routing key.
        
        Args:
            routing_key: The routing key to subscribe to (e.g., "process.#")
            callback: Function to call when an event is received
            queue_name: Optional queue name, will be auto-generated if not provided
        """
        if not self.channel or not self.exchange:
            raise RuntimeError("Not connected to RabbitMQ")

        # Create queue
        queue = await self.channel.declare_queue(
            queue_name or "",
            durable=True,
            auto_delete=queue_name is None
        )

        # Bind queue to exchange
        await queue.bind(self.exchange, routing_key)

        # Store handler
        if routing_key not in self._event_handlers:
            self._event_handlers[routing_key] = []
        self._event_handlers[routing_key].append(callback)

        # Start consuming
        async def process_message(message: aio_pika.IncomingMessage) -> None:
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Depending on the error, we might want to reject/requeue the message
                    message.reject(requeue=True)

        await queue.consume(process_message)
        logger.info(f"Subscribed to {routing_key} events")
