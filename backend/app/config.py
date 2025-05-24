import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text as sqlalchemy_text
from sqlmodel import SQLModel # type: ignore

from .example.router import router as example_router
from .chat.router import router as chat_router

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) # Will be app.main if file is app/main.py

# --- Environment Variable Loading ---
# Load environment variables from a .env file if it exists.
if not load_dotenv():
    logger.info(
        "No .env file found. Using default configurations or environment variables."
    )
else:
    logger.info("Successfully loaded .env file.")


# --- Application Configuration ---
class AppConfig:
    """Application configuration settings."""

    SQLITE_DATABASE_URL: str = os.getenv(
        "SQLITE_DATABASE_URL", "sqlite+aiosqlite:///./hackathon_app.db"
    )
    # API_ROOT_PATH is used for FastAPI's root_path, handling API versioning/prefixing.
    API_ROOT_PATH: str = os.getenv("API_ROOT_PATH", "/api").rstrip("/")
    # For production, consider echo=False or making it configurable
    SQLALCHEMY_ECHO: bool = os.getenv("SQLALCHEMY_ECHO", "True").lower() == "true"


# --- Database Lifespan Management ---
@asynccontextmanager
async def db_lifespan(app: FastAPI):
    """
    Manages the database engine lifecycle.
    Creates an async engine, creates tables, and disposes of the engine on shutdown.
    """
    config = AppConfig()
    logger.info(f"Connecting to database: {config.SQLITE_DATABASE_URL}")

    engine: AsyncEngine = create_async_engine(
        config.SQLITE_DATABASE_URL,
        echo=config.SQLALCHEMY_ECHO,
    )
    # Store the engine in app.state to be accessible by dependencies (e.g., get_session)
    app.state.db_engine = engine

    async with engine.begin() as conn:
        try:
            # This creates tables for all imported SQLModel models.
            # Ensure all model modules are imported before this is called.
            await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Database tables checked/created successfully.")
        except Exception as e:
            logger.error(f"Error during database table creation: {e}")
            raise # Prevent app startup if DB schema fails

    # Optional: Test connection and set PRAGMAs for SQLite
    try:
        async with engine.connect() as connection:
            # Enable foreign key support for SQLite (recommended)
            await connection.execute(sqlalchemy_text("PRAGMA foreign_keys=ON;"))
            await connection.commit()
            result = await connection.execute(sqlalchemy_text("SELECT 1"))
            if result.scalar_one_or_none() == 1:
                logger.info("Database connection test (SELECT 1) successful.")
            else:
                logger.warning("Database connection test (SELECT 1) did not return 1.")
    except Exception as e:
        logger.error(
            f"Failed to execute initial PRAGMA or test query on database: {e}"
        )
        # Depending on severity, you might choose to raise here as well.

    yield  # Application runs here

    logger.info("Shutting down application. Disposing database engine.")
    await engine.dispose()
    logger.info("Database engine disposed.")


# --- FastAPI Application Factory ---
def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application instance.
    """
    config = AppConfig()

    # Initialize FastAPI app with the configured root_path and lifespan manager.
    # The root_path handles the global API prefix (e.g., /api).
    # OpenAPI docs will be available at `config.API_ROOT_PATH + /docs`.
    app = FastAPI(
        lifespan=db_lifespan,
        root_path=config.API_ROOT_PATH,
        title="Hackathon API", # Optional: Add a title
        version="0.1.0",      # Optional: Add a version
    )

    # --- Middleware ---
    # Configure CORS (Cross-Origin Resource Sharing)
    # For production, restrict allow_origins to your frontend's domain.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # WARNING: For development only.
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers ---
    # Include your application's routers.
    # Paths defined in these routers will be prefixed by `config.API_ROOT_PATH`.
    # e.g., if chat_router has "/chat", it becomes "/api/chat".
    app.include_router(example_router, tags=["Example Endpoints"])
    app.include_router(chat_router, tags=["Chat Endpoints"])

    logger.info(
        f"FastAPI application configured. Root path: '{config.API_ROOT_PATH}'. "
        f"Docs at: '{config.API_ROOT_PATH}/docs'."
    )
    return app

