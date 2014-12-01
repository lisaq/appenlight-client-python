import threading
import datetime
import urlparse

class BaseTransport(object):

    def __init__(self, client_config):
        self.report_queue = []
        self.report_queue_lock = threading.RLock()
        self.log_queue = []
        self.log_queue_lock = threading.RLock()
        self.request_stats = {}
        self.request_stats_lock = threading.RLock()
        self.last_submit = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=50)
        self.last_request_stats_submit = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=50)
        self.client_config = client_config

    def check_if_deliver(self, force_send=False):
        delta = datetime.datetime.utcnow() - self.last_submit
        metrics = []
        reports = []
        logs = []
        # should we send
        if delta > self.client_config['buffer_flush_interval'] or force_send:
            # build data to feed the transport
            with self.report_queue_lock:
                reports = self.report_queue[:250]
                if self.client_config['buffer_clear_on_send']:
                    self.report_queue = []
                else:
                    self.report_queue = self.report_queue[250:]

            with self.log_queue_lock:
                logs = self.log_queue[:2000]
                if self.client_config['buffer_clear_on_send']:
                    self.log_queue = []
                else:
                    self.log_queue = self.log_queue[2000:]
            # mark times
            self.last_submit = datetime.datetime.utcnow()

        # metrics we should send every 60s
        delta = datetime.datetime.utcnow() - self.last_request_stats_submit
        if delta >= datetime.timedelta(seconds=60):
            with self.request_stats_lock:
                request_stats = self.request_stats
                self.request_stats = {}
            for k, v in request_stats.iteritems():
                metrics.append({
                    "server": self.client_config['server_name'],
                    "metrics": v.items(),
                    "timestamp": k.isoformat()
                })
            # mark times
            self.last_request_stats_submit = datetime.datetime.utcnow()

        if reports or logs or metrics:
            self.submit(reports=reports, logs=logs, metrics=metrics)
            return True
        return False