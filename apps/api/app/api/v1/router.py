from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.auth import router as auth_router
from app.api.v1.b2b import router as b2b_router
from app.api.v1.batch import router as batch_router
from app.api.v1.billing import router as billing_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.health import router as health_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.payments import router as payments_router
from app.api.v1.requests import router as requests_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.services import router as services_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.users import router as users_router
from app.api.v1.webhooks import router as webhooks_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(services_router)
api_v1_router.include_router(requests_router)
api_v1_router.include_router(uploads_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(api_keys_router)
api_v1_router.include_router(billing_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(reviews_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(b2b_router)
api_v1_router.include_router(webhooks_router)
api_v1_router.include_router(batch_router)
api_v1_router.include_router(evaluations_router)
api_v1_router.include_router(payments_router)
