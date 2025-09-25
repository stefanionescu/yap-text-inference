"""Session management for WebSocket connections."""

import asyncio
import random
from typing import Dict, Any, Optional

from ..config import CHAT_MODEL, TOOL_MODEL
from ..utils.time_utils import format_session_timestamp


class SessionManager:
    """Manages session metadata and lifecycle."""
    
    def __init__(self):
        # Per-session metadata: fixed seed + timestamp string
        self.session_meta: Dict[str, Dict[str, Any]] = {}
        
        # Track active session tasks/requests
        self.session_tasks: Dict[str, asyncio.Task] = {}
        self.session_active_req: Dict[str, str] = {}
        
        # Track in-flight tool req ids (when tool router runs in parallel with chat)
        self.session_tool_req: Dict[str, str] = {}
    
    def initialize_session(self, session_id: str) -> Dict[str, Any]:
        """Initialize session metadata if it doesn't exist.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session metadata dict
        """
        if session_id not in self.session_meta:
            session_seed = random.randint(1, 1_000_000)
            now_str = format_session_timestamp()
            
            self.session_meta[session_id] = {
                "seed": session_seed,
                "now_str": now_str,
                # defaults that can be overridden on start
                "assistant_gender": None,
                "persona_style": "wholesome",
                "persona_text_override": None,
                # expose models (handy for client logs)
                "chat_model": CHAT_MODEL,
                "tool_model": TOOL_MODEL,
            }
        
        return self.session_meta[session_id]
    
    def update_session_config(
        self,
        session_id: str,
        assistant_gender: Optional[str] = None,
        persona_style: Optional[str] = None,
        persona_text_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update session configuration.
        
        Args:
            session_id: Session identifier
            assistant_gender: Normalized assistant gender
            persona_style: Persona style string
            persona_text_override: Raw persona text override
            
        Returns:
            Dict of changed fields
        """
        if session_id not in self.session_meta:
            self.initialize_session(session_id)
        
        changed = {}
        
        if assistant_gender is not None:
            self.session_meta[session_id]["assistant_gender"] = assistant_gender
            changed["assistant_gender"] = assistant_gender
            
        if persona_style is not None:
            self.session_meta[session_id]["persona_style"] = persona_style
            changed["persona_style"] = persona_style
            
        if persona_text_override is not None:
            # explicit None/empty clears the override
            override_val = persona_text_override or None
            self.session_meta[session_id]["persona_text_override"] = override_val
            changed["persona_text_override"] = bool(override_val)
        
        return changed
    
    def get_session_config(self, session_id: str) -> Dict[str, Any]:
        """Get current session configuration.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session configuration dict
        """
        if session_id not in self.session_meta:
            return {}
        return self.session_meta[session_id].copy()
    
    def set_active_request(self, session_id: str, request_id: str) -> None:
        """Set the active request ID for a session.
        
        Args:
            session_id: Session identifier
            request_id: Request identifier
        """
        self.session_active_req[session_id] = request_id
    
    def set_tool_request(self, session_id: str, request_id: str) -> None:
        """Set the tool request ID for a session.
        
        Args:
            session_id: Session identifier
            request_id: Tool request identifier
        """
        self.session_tool_req[session_id] = request_id
    
    def cancel_session_requests(self, session_id: str) -> None:
        """Cancel all requests for a session.
        
        Args:
            session_id: Session identifier
        """
        self.session_active_req[session_id] = "CANCELLED"
        
        # Cancel session task
        task = self.session_tasks.get(session_id)
        if task:
            task.cancel()
    
    def cleanup_session_requests(self, session_id: str) -> Dict[str, str]:
        """Clean up session request tracking and return request IDs.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with 'active' and 'tool' request IDs
        """
        active_req = self.session_active_req.get(session_id, "")
        tool_req = self.session_tool_req.pop(session_id, "")
        
        return {
            "active": active_req,
            "tool": tool_req
        }
    
    def get_session_seed(self, session_id: str) -> int:
        """Get the fixed seed for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session seed value
        """
        return self.session_meta.get(session_id, {}).get("seed", 0)


# Global session manager instance
session_manager = SessionManager()
