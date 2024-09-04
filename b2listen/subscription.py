import hashlib
import hmac
import json
import logging
from threading import Thread, Event

import requests

EVENT_NOTIFICATION_SIGNATURE_HEADER = 'x-bz-event-notification-signature'

logging.basicConfig()
logger = logging.getLogger('subscription')


class Subscription(Thread):
    """
    Manage a subscription to the event broker
    """

    def __init__(self, event_broker_url: str, tunnel_url: str, bucket_name: str, rule_name: str | None,
                 signing_secret: str, interval_seconds: float):
        super().__init__()
        self.event_broker_url = event_broker_url
        self.tunnel_url = tunnel_url
        self.bucket_name = bucket_name
        self.rule_name = rule_name
        self.signing_secret = signing_secret
        self.interval_seconds = interval_seconds
        self.stop_event = Event()
        self.id_ = None
        logger.info(f'Creating subscription object for {self.bucket_name}/{self.rule_name} with '
                    f'{self.interval_seconds} polling interval')
        self.subscribe()
        self.start()

    def create_message_signature(self, body: bytes):
        """
        Create the signature for the event notification message.
        """
        return 'v1=' + hmac.new(
            bytes(self.signing_secret, 'utf-8'),
            msg=body,
            digestmod=hashlib.sha256
        ).hexdigest().lower()

    def subscribe(self):
        """
        Create a new subscription
        """
        payload = {'url': self.tunnel_url}
        body = bytes(json.dumps(payload), 'utf-8')

        signature = self.create_message_signature(body)

        res = requests.post(
            f'{self.event_broker_url}/@subscriptions/{self.bucket_name}/{self.rule_name}',
            data=body,
            headers={EVENT_NOTIFICATION_SIGNATURE_HEADER: signature}
        )
        res.raise_for_status()
        res = res.json()
        self.id_ = res['id']
        logger.info(f'Subscribed to {self.bucket_name}/{self.rule_name}/{self.id_}')

    def subscription(self):
        """
        Check whether the current subscription is active. The broker removes a subscription after a configurable number
        (default 5) failed message delivery attempts.
        """
        signature = self.create_message_signature(bytes())

        res = requests.head(
            f'{self.event_broker_url}/@subscriptions/{self.bucket_name}/{self.rule_name}/{self.id_}',
            headers={EVENT_NOTIFICATION_SIGNATURE_HEADER: signature}
        )
        logger.debug(f'Received {res.status_code} for {self.bucket_name}/{self.rule_name}/{self.id_}')
        return res.ok

    def unsubscribe(self):
        """
        Remove the current subscription
        """
        signature = self.create_message_signature(bytes())

        res = requests.delete(
            f'{self.event_broker_url}/@subscriptions/{self.bucket_name}/{self.rule_name}/{self.id_}',
            headers={EVENT_NOTIFICATION_SIGNATURE_HEADER: signature}
        )
        res.raise_for_status()
        logger.info(f'Unsubscribed from {self.bucket_name}/{self.rule_name}/{self.id_}')
        self.id_ = None

    def probe_tunnel_url(self):
        """
        Send an empty event notifications list to the client to check that it is still up
        """
        payload = {"event": []}
        body = bytes(json.dumps(payload), 'utf-8')

        signature = self.create_message_signature(body)

        res = requests.post(
            f'{self.tunnel_url}',
            data=body,
            headers={EVENT_NOTIFICATION_SIGNATURE_HEADER: signature}
        )
        logger.debug(f'Received {res.status_code} for {self.tunnel_url}')
        return res.ok

    def run(self):
        """
        Periodically check that the subscription is still active. If the subscription is no longer active, but we can
        ping the client, resubscribe; otherwise, try again later.
        """
        while not self.stop_event.wait(self.interval_seconds):
            if not self.subscription():
                if self.probe_tunnel_url():
                    logger.info('Subscription is no longer active, but client is awake. Resubscribing.')
                    self.subscribe()
                else:
                    logger.warning('Subscription is no longer active, and client is not responding. '
                                   f'Will try again in {self.interval_seconds} seconds')

    def stop(self):
        self.stop_event.set()
        self.unsubscribe()
        logger.info(f'Stopped subscription for {self.bucket_name}/{self.rule_name}')
