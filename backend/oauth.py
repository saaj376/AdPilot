
from google_auth_oauthlib.flow import InstalledAppFlow
from pexpect import EOF
flow = InstalledAppFlow.from_client_secrets_file(
    "/home/saajan/Downloads/Albus-Dumbledore/backend/client_secret_1003887054540-77uns74giam29iahdp6e42u9pi8jqs0p.apps.googleusercontent.com.json",
    scopes=["https://www.googleapis.com/auth/adwords"]
)
creds = flow.run_local_server(port=8080)
print("Refresh token:", creds.refresh_token)
