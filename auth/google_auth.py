from google_auth_oauthlib.flow import Flow

def get_auth_url(client_config, redirect_uri):
    flow = Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri=redirect_uri
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url, flow
