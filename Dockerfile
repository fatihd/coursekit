FROM python:3.13-slim

COPY scripts/run /usr/local/bin/course-server
RUN chmod 755 /usr/local/bin/course-server

ENTRYPOINT ["python", "/usr/local/bin/course-server", "/course", "--host", "0.0.0.0", "--port", "8000", "--no-browser"]
