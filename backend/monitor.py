import json
import time

from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class MonitorHandler(FileSystemEventHandler):

    def save_event(self, event_type, file_path):

        event_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "file_path": file_path
        }

        print(json.dumps(event_data, indent=4))

        with open("events.log", "a") as log:
            log.write(json.dumps(event_data) + "\n")

    def on_created(self, event):
        if not event.is_directory:
            self.save_event("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.save_event("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.save_event("deleted", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:

            event_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": "moved",
                "source_path": event.src_path,
                "destination_path": event.dest_path
            }

            print(json.dumps(event_data, indent=4))

            with open("events.log", "a") as log:
                log.write(json.dumps(event_data) + "\n")


if __name__ == "__main__":

    path = "."

    event_handler = MonitorHandler()

    observer = Observer()

    observer.schedule(
        event_handler,
        path,
        recursive=True
    )

    observer.start()

    print("Monitoring started...")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()

    observer.join()
