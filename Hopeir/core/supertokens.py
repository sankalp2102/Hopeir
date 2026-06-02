# core/supertokens.py

import os
from supertokens_python import init, InputAppInfo, SupertokensConfig
from supertokens_python.recipe import session, emailpassword, dashboard
from supertokens_python.recipe.emailpassword import InputOverrideConfig
from supertokens_python.recipe.emailpassword.interfaces import (
    APIInterface, APIOptions, SignUpPostOkResult
)
from .models import CustomUser
from asgiref.sync import sync_to_async

def create_django_user(user_id: str, email: str):
    user = CustomUser(user_id=user_id, email=email, username=email)
    user.set_unusable_password()
    user.save()
    print(f"Successfully created Django user: {email}")
    return user

def override_emailpassword_apis(original_implementation: APIInterface):
    original_sign_up_post = original_implementation.sign_up_post

    async def custom_sign_up(
        form_fields, tenant_id, api_options: APIOptions,
        request, response, user_context
    ):
        resp = await original_sign_up_post(
            form_fields, tenant_id, api_options, request, response, user_context
        )
        if isinstance(resp, SignUpPostOkResult):
            user = resp.user
            await sync_to_async(create_django_user)(
                user_id=user.id,
                email=user.login_methods[0].email
            )
        return resp
 
    original_implementation.sign_up_post = custom_sign_up
    return original_implementation


def init_supertokens():
    init(
        app_info=InputAppInfo(
            app_name="Hopeir",
            # Read from env — on GCP this will be your external IP or domain
            api_domain=os.environ.get("API_DOMAIN", "http://localhost:8000"),
            website_domain=os.environ.get("WEBSITE_DOMAIN", "http://localhost:3000"),
            api_base_path="/auth",
            website_base_path="/auth"
        ),
        supertokens_config=SupertokensConfig(
            # On GCP: http://supertokens:3567 (docker service name)
            # On local: http://localhost:3567
            connection_uri=os.environ.get("SUPERTOKENS_URL", "http://localhost:3567"),
        ),
        framework='django',
        recipe_list=[
            session.init(),
            emailpassword.init(
                override=InputOverrideConfig(
                    apis=override_emailpassword_apis
                )
            ),
            dashboard.init(),
        ],
        mode='asgi'
    )