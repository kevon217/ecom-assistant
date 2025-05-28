"""
Session management for chat service.

This module provides persistence and operations for chat sessions,
abstracting storage backend and providing a clean API for session handling.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from libs.ecom_shared.logging import get_logger

logger = get_logger(__name__)


class SessionStore:
    """
    Storage backend for chat sessions.

    Abstracts the storage mechanism (memory, file, database) and provides
    persistence operations for sessions.
    """

    # Class-level storage (in-memory fallback)
    _sessions: Dict[str, Dict[str, Any]] = {}
    _dirty_sessions: Set[str] = set()
    _storage_path: Optional[Path] = None
    _initialized: bool = False

    @classmethod
    def initialize(cls, storage_path: Optional[str] = None) -> None:
        """
        Initialize the session store with optional persistent storage.

        Args:
            storage_path: Optional path to store session data on disk
        """
        if cls._initialized:
            return

        if storage_path:
            cls._storage_path = Path(storage_path)
            os.makedirs(cls._storage_path, exist_ok=True)
            logger.info(f"SessionStore initialized with path: {cls._storage_path}")
            # Load existing sessions
            cls._load_sessions()
        else:
            logger.info("SessionStore initialized with in-memory storage only")

        cls._initialized = True

    @classmethod
    def _load_sessions(cls) -> None:
        """Load sessions from persistent storage if available."""
        if not cls._storage_path:
            return

        try:
            for session_file in cls._storage_path.glob("*.json"):
                try:
                    with open(session_file, "r") as f:
                        session_data = json.load(f)
                        session_id = session_file.stem
                        cls._sessions[session_id] = session_data
                        logger.debug(f"Loaded session: {session_id}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load session {session_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")

    @classmethod
    async def flush(cls) -> None:
        """
        Persist dirty sessions to storage.
        Call this method periodically or on shutdown.
        """
        if not cls._storage_path or not cls._dirty_sessions:
            return

        for session_id in list(cls._dirty_sessions):
            try:
                session_data = cls._sessions.get(session_id)
                if session_data:
                    file_path = cls._storage_path / f"{session_id}.json"
                    with open(file_path, "w") as f:
                        json.dump(session_data, f, indent=2)
                    cls._dirty_sessions.remove(session_id)
                    logger.debug(f"Persisted session: {session_id}")
            except Exception as e:
                logger.error(f"Failed to persist session {session_id}: {e}")

    @classmethod
    def get(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data if found, None otherwise
        """
        return cls._sessions.get(session_id)

    @classmethod
    def save(cls, session_id: str, data: Dict[str, Any]) -> None:
        """
        Save session data.

        Args:
            session_id: Session identifier
            data: Session data to save
        """
        cls._sessions[session_id] = data
        cls._dirty_sessions.add(session_id)

    @classmethod
    def delete(cls, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        if session_id in cls._sessions:
            del cls._sessions[session_id]
            cls._dirty_sessions.discard(session_id)

            # Remove from persistent storage if exists
            if cls._storage_path:
                file_path = cls._storage_path / f"{session_id}.json"
                if file_path.exists():
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        logger.error(f"Failed to delete session file {session_id}: {e}")

            return True
        return False

    @classmethod
    def get_all_ids(cls) -> List[str]:
        """Get all session IDs."""
        return list(cls._sessions.keys())


class SessionManager:
    """
    Manager for chat sessions.

    Provides operations for working with sessions, including
    creation, retrieval, and message handling.
    """

    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize the session manager.

        Args:
            ttl_minutes: Session time-to-live in minutes
        """
        self.ttl_minutes = ttl_minutes

    def get_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get or create a session.

        Args:
            session_id: Optional session ID to retrieve

        Returns:
            Session data
        """
        # Ensure store is initialized
        if not SessionStore._initialized:
            SessionStore.initialize()

        # Use provided ID or generate a new one
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.debug(f"Created new session: {session_id}")

        # Get existing session or create new one
        session = SessionStore.get(session_id)
        if not session:
            session = {
                "id": session_id,
                "history": [],
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "metadata": {},
            }
            SessionStore.save(session_id, session)
            logger.debug(f"Initialized new session: {session_id}")
        else:
            # Check if session is expired
            last_active = datetime.fromisoformat(session["last_active"])
            if datetime.now() - last_active > timedelta(minutes=self.ttl_minutes):
                logger.debug(f"Session expired: {session_id}")
                # Reset the session but keep the ID
                session = {
                    "id": session_id,
                    "history": [],
                    "created_at": datetime.now().isoformat(),
                    "last_active": datetime.now().isoformat(),
                    "metadata": {},
                }
            else:
                # Update last active timestamp
                session["last_active"] = datetime.now().isoformat()
                SessionStore.save(session_id, session)

        return session

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        Add a message to a session's history.

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content

        Returns:
            True if successful, False otherwise
        """
        session = SessionStore.get(session_id)
        if not session:
            logger.warning(
                f"Attempted to add message to non-existent session: {session_id}"
            )
            return False

        # Add message to history
        session["history"].append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )

        # Update last active timestamp
        session["last_active"] = datetime.now().isoformat()

        # Save session
        SessionStore.save(session_id, session)
        return True

    def get_history(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get a session's message history.

        Args:
            session_id: Session identifier
            limit: Optional maximum number of messages to return (newest first)

        Returns:
            List of message objects
        """
        session = SessionStore.get(session_id)
        if not session:
            logger.warning(
                f"Attempted to get history for non-existent session: {session_id}"
            )
            return []

        history = session.get("history", [])
        if limit and limit > 0:
            return history[-limit:]
        return history

    def update_metadata(self, session_id: str, key: str, value: Any) -> bool:
        """
        Update session metadata.

        Args:
            session_id: Session identifier
            key: Metadata key
            value: Metadata value

        Returns:
            True if successful, False otherwise
        """
        session = SessionStore.get(session_id)
        if not session:
            logger.warning(
                f"Attempted to update metadata for non-existent session: {session_id}"
            )
            return False

        if "metadata" not in session:
            session["metadata"] = {}

        session["metadata"][key] = value
        SessionStore.save(session_id, session)
        return True

    def get_metadata(self, session_id: str, key: str) -> Optional[Any]:
        """
        Get session metadata value.

        Args:
            session_id: Session identifier
            key: Metadata key

        Returns:
            Metadata value if found, None otherwise
        """
        session = SessionStore.get(session_id)
        if not session or "metadata" not in session:
            return None

        return session["metadata"].get(key)

    def clear_history(self, session_id: str) -> bool:
        """
        Clear a session's message history.

        Args:
            session_id: Session identifier

        Returns:
            True if successful, False otherwise
        """
        session = SessionStore.get(session_id)
        if not session:
            return False

        session["history"] = []
        SessionStore.save(session_id, session)
        return True

    def count_active_sessions(self, hours: int = 24) -> int:
        """
        Count sessions active within the specified time window.

        Args:
            hours: Time window in hours

        Returns:
            Count of active sessions
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        count = 0

        for session_id in SessionStore.get_all_ids():
            session = SessionStore.get(session_id)
            if session and "last_active" in session:
                try:
                    last_active = datetime.fromisoformat(session["last_active"])
                    if last_active > cutoff:
                        count += 1
                except (ValueError, TypeError):
                    continue

        return count


# Dependency for FastAPI
def get_session(session_id: Optional[str] = None):
    """
    FastAPI dependency to get or create a session.

    Args:
        session_id: Optional session ID to retrieve

    Returns:
        Session data
    """
    manager = SessionManager()
    return manager.get_session(session_id)
