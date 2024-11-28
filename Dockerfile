FROM python:3.12.6

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd -m superuser
USER superuser
WORKDIR /home/superuser
COPY . .
USER root
RUN chmod +x /home/superuser/telegram_user.db
RUN chmod -R 755 /home/superuser
RUN chown -R superuser:superuser /home/superuser
USER superuser
WORKDIR /home/superuser
RUN pip install --upgrade pip || true
ENV PATH="/home/superuser/.local/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 - && poetry --version \
&& poetry install
RUN pip install -r /home/superuser/requirements.txt
COPY entrypoint.sh /home/superuser/entrypoint.sh

ENTRYPOINT ["/home/superuser/entrypoint.sh"]