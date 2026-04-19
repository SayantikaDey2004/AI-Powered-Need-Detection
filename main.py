from fastapi import FastAPI, HTTPException
from app.db.db import client
from app.routers.authRouter import router as auth_router
from app.routers.dashboardRouter import router as dashboard_router
from app.api.v1.routes.email import router as email_router
from app.core.config import get_settings
from app.services.email.sendEmail import send_email

settings = get_settings()
app = FastAPI(title=settings.APP_NAME)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(email_router)


@app.on_event("startup")
async def startup_db_ping():
    await client.admin.command("ping")


@app.get("/")
def root():
    return {"message": "API is working!"}


@app.post("/send-test-email")
def send_test_email():
    try:
        send_email(
            to_email="student@example.com",
            to_name="Student",
            subject="Welcome",
            html_content="<h1>Hello from Brevo</h1>",
        )
        return {"ok": True}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))