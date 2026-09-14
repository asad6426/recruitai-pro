"""Minimal SSLCommerz integration — just the two REST calls the job-posting
payment flow needs. No SDK dependency, plain `requests` calls against their
documented v4 API. See https://developer.sslcommerz.com/doc/v4/ for the
full API surface if this needs to grow (refunds, subscriptions, etc.)."""
import requests
from django.conf import settings

SESSION_API = "https://{host}/gwprocess/v4/api.php"
VALIDATION_API = "https://{host}/validator/api/validationserverAPI.php"


def _host():
    return "sandbox.sslcommerz.com" if settings.SSLCOMMERZ_IS_SANDBOX else "securepay.sslcommerz.com"


def init_session(*, tran_id, amount, success_url, fail_url, cancel_url, ipn_url, customer):
    """Starts a payment session. Returns (gateway_url, raw_response) on
    success, or (None, raw_response) if SSLCommerz rejected the request
    (bad amount, missing field, etc. — raw_response carries the reason)."""
    payload = {
        "store_id": settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
        "total_amount": str(amount),
        "currency": "BDT",
        "tran_id": tran_id,
        "success_url": success_url,
        "fail_url": fail_url,
        "cancel_url": cancel_url,
        "ipn_url": ipn_url,
        "shipping_method": "NO",
        "product_name": "Job posting",
        "product_category": "Service",
        "product_profile": "general",
        "num_of_item": 1,
        "cus_name": customer.get("name") or "RecruitAI Recruiter",
        "cus_email": customer.get("email") or "recruiter@example.com",
        "cus_add1": customer.get("address") or "N/A",
        "cus_city": customer.get("city") or "Dhaka",
        "cus_country": "Bangladesh",
        "cus_phone": customer.get("phone") or "01700000000",
    }
    resp = requests.post(SESSION_API.format(host=_host()), data=payload, timeout=15)
    data = resp.json()
    if data.get("status") == "SUCCESS":
        return data["GatewayPageURL"], data
    return None, data


def validate_transaction(val_id):
    """Confirms a val_id SSLCommerz sent back is genuine (not a forged POST
    hitting our success URL directly) by asking SSLCommerz to look it up
    server-to-server. Returns the validation payload; caller checks
    `status` in ("VALID", "VALIDATED")."""
    params = {
        "val_id": val_id,
        "store_id": settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
        "format": "json",
    }
    resp = requests.get(VALIDATION_API.format(host=_host()), params=params, timeout=15)
    return resp.json()
