import yaml
from NorenRestApiPy import NorenApi
from pyotp import TOTP
import base64
import time
import threading


# -------------------------------------------------------
# LOGIN + API INITIALIZATION
# -------------------------------------------------------

def load_credentials():
    with open("config/credentials.yml", "r") as file:
        return yaml.safe_load(file)


def generate_totp(base32_secret: str) -> str:
    """Generate TOTP value for Shoonya 2FA login."""
    return TOTP(base32_secret).now()


def login_shoonya(mock_mode: bool = False):
    """
    Create a NorenApi session and perform Shoonya login.
    WebSocket callbacks are no longer configured here.
    """
    print("🌐 MOCK_MODE =", "🟡🟡 LOCAL 🟡🟡" if mock_mode else "🟢🟢 LIVE 🟢🟢")
    print(
        "🌐 Using WebSocket URL =",
        "ws://localhost:9000" if mock_mode else "wss://api.shoonya.com/NorenWSWeb/",
    )

    credentials = load_credentials()
    secret = credentials["totp_secret"]

    # Convert to Base32 if required
    base32_secret = (
        base64.b32encode(secret.encode()).decode()
        if not secret.isupper()
        else secret
    )

    factor2 = generate_totp(base32_secret)

    api = NorenApi.NorenApi(
        host="https://api.shoonya.com/NorenWClientTP/",
        websocket="ws://localhost:9000" if mock_mode else "wss://api.shoonya.com/NorenWSWeb/",
    )

    login_response = api.login(
        userid=credentials["user"],
        password=credentials["pwd"],
        twoFA=factor2,
        vendor_code=credentials["vc"],
        api_secret=credentials["apikey"],
        imei=credentials["imei"],
    )

    return api, login_response


def print_login_summary(login_response):
    keys_of_interest = [
        "stat",
        "request_time",
        "uname",
        "actid",
    ]
    summary = {k: login_response.get(k) for k in keys_of_interest}
    print("✅ Login Summary:", summary)


# -------------------------------------------------------
# TOKEN RESOLUTION
# -------------------------------------------------------

def get_token(api, exchange, tradingsymbols):
    """
    Convert tradingsymbol(s) to Shoonya token(s).
    Returns list of "EXCHANGE|TOKEN".
    """

    if isinstance(tradingsymbols, str):
        tradingsymbols = [tradingsymbols]

    result_tokens = []
    not_found = []

    for symbol in tradingsymbols:
        resp = api.searchscrip(exchange=exchange, searchtext=symbol)

        token_found = None
        if resp and "values" in resp:
            for item in resp["values"]:
                if item["tsym"] == symbol:
                    token_found = item["token"]
                    break

        if token_found:
            result_tokens.append(f"{exchange}|{token_found}")
        else:
            not_found.append(symbol)

    if not_found:
        print("⚠️ Token NOT found for:", not_found)

    return result_tokens


# -------------------------------------------------------
# KEEPALIVE
# -------------------------------------------------------

def start_keepalive(api, interval: int = 30):
    """Sends periodic harmless requests to keep the HTTP session alive."""

    def run():
        while True:
            try:
                api.get_limits()
                # print("🟢 KeepAlive sent")
            except Exception as e:
                print("⚠️ KeepAlive failed:", e)
            time.sleep(interval)

    t = threading.Thread(target=run, daemon=True)
    t.start()


# -------------------------------------------------------
# CLEAN LOGOUT
# -------------------------------------------------------

def logout_shoonya(api):
    try:
        print("✅ Logout Summary:")
        return api.logout()
    except Exception as e:
        print("⚠️ Logout failed (network/DNS issue). Ignoring...")
        print(e)
        return {"stat": "Not Logged Out"}
