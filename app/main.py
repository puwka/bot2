import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import settings
from app.db import check_connection
from app.middlewares.role_middleware import RoleMiddleware
from app.middlewares.rate_limit_middleware import RateLimitMiddleware
from app.handlers import common, admin, uploader, distributor

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())

    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())

    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(uploader.router)
    dp.include_router(distributor.router)

    return dp


async def on_startup_webhook(bot: Bot) -> None:
    await bot.set_webhook(
        settings.webhook_url,
        drop_pending_updates=True,
    )
    logger.info("Webhook set: %s", settings.webhook_url)


async def on_shutdown_webhook(bot: Bot) -> None:
    await bot.delete_webhook()
    logger.info("Webhook removed")


def main() -> None:
    bot = create_bot()
    dp = create_dispatcher()

    if settings.USE_POLLING:
        import asyncio
        async def run_polling():
            logger.info("Checking database connection...")
            try:
                await check_connection()
                logger.info("Database OK")
            except asyncio.TimeoutError as e:
                logger.error(
                    "Supabase: таймаут подключения. Проверьте интернет, VPN/прокси и SUPABASE_URL в .env.",
                )
                raise SystemExit(1) from e
            except Exception as e:
                logger.error(
                    "Supabase connection failed: %s. Проверьте в .env: SUPABASE_URL (https://PROJECT.supabase.co без слэша в конце), SUPABASE_SERVICE_ROLE_KEY (из Settings → API). При прокси/VPN попробуйте другую сеть.",
                    e,
                )
                raise SystemExit(1) from e
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        asyncio.run(run_polling())
    else:
        if not settings.WEBHOOK_HOST:
            raise ValueError("Set WEBHOOK_HOST in .env or use USE_POLLING=true for local dev")
        dp.startup.register(on_startup_webhook)
        dp.shutdown.register(on_shutdown_webhook)
        app = web.Application()
        webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_handler.register(app, path=settings.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        port = int(os.environ.get("PORT", settings.WEBAPP_PORT))
        logger.info("Starting webhook server on %s:%s", settings.WEBAPP_HOST, port)
        web.run_app(app, host=settings.WEBAPP_HOST, port=port)


if __name__ == "__main__":
    main()
