from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("folk_agents.firebase")

# In-memory storage fallback for local development and unit tests
_IN_MEMORY_STORE: Dict[str, Dict[str, Any]] = {
    "curricula": {},
    "student_profiles": {
        "student_demo_101": {
            "student_id": "student_demo_101",
            "reading_level": "Grade 7 (approaching grade level)",
            "learning_style_affinities": ["Visual Diagrams", "Analogies", "Step-by-Step Chunking"],
            "mastery_map": {
                "photosynthesis_light_reaction": {
                    "concept_name": "Photosynthesis - Light Reaction",
                    "mastery_percentage": 45.0,
                    "attempts": 3,
                    "last_tested_date": "2026-08-20",
                    "status": "needs_remediation",
                },
                "cellular_respiration_basics": {
                    "concept_name": "Cellular Respiration Basics",
                    "mastery_percentage": 85.0,
                    "attempts": 2,
                    "last_tested_date": "2026-08-22",
                    "status": "mastered",
                },
            },
            "recurrent_misconceptions": [
                "Confuses ATP synthesis role with direct sunlight absorption",
                "Assumes plants do not perform cellular respiration at night",
            ],
            "cognitive_growth_trend": "Improving with visual scaffolding",
            "total_sessions_completed": 5,
            "scaffolding_recommendations": [
                "Provide dual-code visual diagrams before text explanations",
                "Include concrete kitchen/everyday energy analogies",
            ],
            "last_updated": "2026-08-22T14:30:00Z",
        }
    },
    "session_evaluations": {},
    "remediation_plans": {},
}


class FirestoreService:
    """Firebase Firestore abstraction with graceful local fallback."""

    def __init__(self):
        self.db = None
        self._is_mock = True
        self._init_client()

    def _init_client(self):
        try:
            from google.cloud import firestore
            from google.oauth2 import service_account

            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            database_name = os.getenv("FIRESTORE_DATABASE", "(default)")

            if cred_path and os.path.exists(cred_path):
                creds = service_account.Credentials.from_service_account_file(cred_path)
                self.db = firestore.Client(project=project_id, credentials=creds, database=database_name)
                self._is_mock = False
                logger.info(f"Connected to live Google Cloud Firestore (project: {self.db.project}, database: {database_name}).")
            elif project_id:
                if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ and not os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
                    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
                self.db = firestore.Client(project=project_id, database=database_name)
                self._is_mock = False
                logger.info(f"Connected to live Google Cloud Firestore (project: {self.db.project}, database: {database_name}).")
            else:
                logger.info("Using in-memory Firestore mock store.")
                self._is_mock = True
        except Exception as e:
            logger.warning(f"Firestore initialization fallback to in-memory: {e}")
            self._is_mock = True

    async def save_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        if not self._is_mock and self.db:
            try:
                self.db.collection(collection).document(doc_id).set(data, merge=True)
                return True
            except Exception as e:
                logger.error(f"Firestore save error: {e}")
        # Fallback
        if collection not in _IN_MEMORY_STORE:
            _IN_MEMORY_STORE[collection] = {}
        _IN_MEMORY_STORE[collection][doc_id] = data
        return True

    async def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        if not self._is_mock and self.db:
            try:
                doc = self.db.collection(collection).document(doc_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Firestore read error: {e}")
        # Fallback
        return _IN_MEMORY_STORE.get(collection, {}).get(doc_id)

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        if not self._is_mock and self.db:
            try:
                self.db.collection(collection).document(doc_id).delete()
                return True
            except Exception as e:
                logger.error(f"Firestore delete error: {e}")
        # Fallback
        if collection in _IN_MEMORY_STORE and doc_id in _IN_MEMORY_STORE[collection]:
            del _IN_MEMORY_STORE[collection][doc_id]
        return True

    async def list_documents(self, collection: str) -> list[Dict[str, Any]]:
        docs_map = await self.list_collection(collection)
        results = []
        for doc_id, data in docs_map.items():
            if isinstance(data, dict):
                if "id" not in data and "student_id" not in data and "package_id" not in data:
                    data["id"] = doc_id
                results.append(data)
        return results

    async def list_collection(self, collection: str) -> Dict[str, Any]:
        if not self._is_mock and self.db:
            try:
                docs = self.db.collection(collection).stream()
                return {d.id: d.to_dict() for d in docs}
            except Exception as e:
                logger.error(f"Firestore list error: {e}")
        return _IN_MEMORY_STORE.get(collection, {})


# Global singleton
firestore_service = FirestoreService()
