"""Generate a Google Ads refresh token from your own OAuth client file."""
import argparse

from google_auth_oauthlib.flow import InstalledAppFlow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client_secrets", help="Path to your downloaded OAuth desktop client JSON")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    flow = InstalledAppFlow.from_client_secrets_file(
        args.client_secrets, scopes=["https://www.googleapis.com/auth/adwords"]
    )
    credentials = flow.run_local_server(port=args.port, access_type="offline", prompt="consent")
    print("Refresh token:", credentials.refresh_token)


if __name__ == "__main__":
    main()
