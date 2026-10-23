# Store configuration — edit this file for your own store.
# The UPI payee below is the store owner's payee ID, shown to buyers at
# checkout so they can pay by UPI. It is intentionally public-facing at
# checkout (like a shop's UPI ID on a QR board). It is NOT a password or
# secret key, and it must never be used as a login credential.
STORE_NAME = "Product King"
UPI_ID = "7774086386@ybl"
UPI_PAYEE_NAME = "Shirish Digital Store"
SECRET_KEY = "change-me-before-production"
# YouPI webhook secret — set via environment variable YOUPI_WEBHOOK_SECRET
# in a real self-hosted deployment. It is NEVER invented here and is NOT
# stored in this file. If it is unset, the YouPI webhook will NOT auto-
# unlock orders; admin manual confirmation is required instead.
import os as _os
YOUPI_WEBHOOK_SECRET = _os.environ.get("YOUPI_WEBHOOK_SECRET", "")
GST_RATE_IN = 0.18
DOWNLOAD_MAX_DEFAULT = 5
DOWNLOAD_LINK_MINUTES = 15
