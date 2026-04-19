import sib_api_v3_sdk

from app.core.config import get_settings

settings = get_settings()

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key["api-key"] = settings.brevo_api_key or ""

api_client = sib_api_v3_sdk.ApiClient(configuration)

email_api = sib_api_v3_sdk.TransactionalEmailsApi(api_client)
