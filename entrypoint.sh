#!/bin/bash

DB_FILE="telegram_user.db"

if [ ! -f "$DB_FILE" ]; then
    touch "$DB_FILE"
fi

exec poetry run parser