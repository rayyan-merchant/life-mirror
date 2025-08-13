import os
import math
import random
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.db.session import get_db
from src.db.models import Media, User


class SocialGraphOutput(BaseModel):
    cold_start: bool = Field(..., description="True if using synthetic baseline due to low public data.")
    sample_size: int = Field(..., description="Number of real public users used (0 during cold start).")
    user_vibe_score: Optional[int] = Field(None, description="User's latest vibe_score (0-100) if available.")
    percentile: Dict[str, int] = Field(..., description="Overall percentile and optional facet percentiles.")
    similar_users: List[Dict[str, Any]] = Field(..., description="List of similar public users (id, alias, score, tags).")
    complementary_users: List[Dict[str, Any]] = Field(..., description="List of complementary users (id, alias, score, tags).")


class SocialGraphAgent(BaseAgent):
    """
    Compares a user's vibe to other users who opted-in (privacy-first).
    Cold start handled via synthetic distribution when few (or zero) public users exist.
    """
    name = "social_graph_agent"
    output_schema = SocialGraphOutput

    MIN_PUBLIC_USERS = int(os.getenv("SOCIAL_GRAPH_MIN_PUBLIC_USERS", "25"))
    RECENT_LIMIT_PER_USER = int(os.getenv("SOCIAL_GRAPH_RECENT_LIMIT_PER_USER", "1"))  # compare latest only

    def _latest_vibe_for_user(self, db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch latest media with vibe_analysis for a user."""
        m = (
            db.query(Media)
            .filter(Media.user_id == user_id)
            .filter(Media.metadata.has_key("vibe_analysis"))  # type: ignore[attr-defined]
            .order_by(Media.created_at.desc())
            .first()
        )
        if not m:
            return None
        va = (m.metadata or {}).get("vibe_analysis") or {}
        score = va.get("vibe_score")
        tags = va.get("vibe_tags") or []
        return {"media_id": m.id, "score": score, "tags": tags, "created_at": m.created_at.isoformat()}

    def _collect_public_baseline(self, db: Session, exclude_user_id: int) -> List[Dict[str, Any]]:
        """Collect latest vibe_analysis from all opt-in users except the current user."""
        # Find all public users
        pub_users = (
            db.query(User.id, User.public_alias)
            .filter(User.opt_in_public_analysis.is_(True))
            .all()
        )
        results = []
        for uid, alias in pub_users:
            if uid == exclude_user_id:
                continue
            latest = self._latest_vibe_for_user(db, uid)
            if latest and isinstance(latest.get("score"), (int, float)):
                results.append({
                    "user_id": uid,
                    "alias": alias or f"User {uid}",
                    "score": int(round(latest["score"])),
                    "tags": latest.get("tags", []),
                    "media_id": latest["media_id"]
                })
        return results

    @staticmethod
    def _percentile_from_distribution(value: int, population_scores: List[int]) -> int:
        if not population_scores:
            return 50
        below = sum(1 for s in population_scores if s <= value)
        pct = int(round(100 * below / len(population_scores)))
        return max(1, min(99, pct))

    @staticmethod
    def _synthetic_scores(n: int = 1000) -> List[int]:
        """Truncated normal ~ N(60, 15^2), clamped to 0..100."""
        out = []
        for _ in range(n):
            x = random.gauss(60, 15)
            out.append(int(max(0, min(100, round(x)))))
        return out

    @staticmethod
    def _jaccard(a: List[str], b: List[str]) -> float:
        sa, sb = set(a), set(b)
        if not sa and not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def _rank_users(self, me_score: int, me_tags: List[str], candidates: List[Dict[str, Any]]):
        """
        Similarity = high tag overlap + close score
        Complementary = low tag overlap + close score (within ~10)
        """
        def sim(u):
            tag_sim = self._jaccard(me_tags, u["tags"])
            score_gap = abs(me_score - u["score"])  # smaller is better
            # Weighted: 70% tags, 30% score closeness
            score_component = max(0.0, 1.0 - (score_gap / 100.0))
            return 0.7 * tag_sim + 0.3 * score_component

        def comp(u):
            tag_sim = self._jaccard(me_tags, u["tags"])
            score_gap = abs(me_score - u["score"])
            score_component = max(0.0, 1.0 - (score_gap / 20.0))  # tighter band
            # Prefer *low* tag similarity but similar scores
            return (1.0 - tag_sim) * 0.7 + score_component * 0.3

        similar = sorted(candidates, key=sim, reverse=True)[:5]
        complementary = sorted(candidates, key=comp, reverse=True)[:5]
        return similar, complementary

    def run(self, input: AgentInput) -> AgentOutput:
        """
        input.data expects: { "user_id": int }
        Respects privacy via users.opt_in_public_analysis.
        """
        mode = os.getenv("LIFEMIRROR_MODE", "mock")
        user_id = int(input.data["user_id"])

        if mode == "mock":
            # Simple, consistent mock for UI wiring
            mock = SocialGraphOutput(
                cold_start=True,
                sample_size=0,
                user_vibe_score=78,
                percentile={"overall": 85},
                similar_users=[
                    {"user_id": 101, "alias": "Alex", "score": 80, "tags": ["confident", "stylish"]},
                    {"user_id": 102, "alias": "Sam", "score": 76, "tags": ["approachable", "calm"]}
                ],
                complementary_users=[
                    {"user_id": 201, "alias": "Riya", "score": 79, "tags": ["playful", "expressive"]}
                ]
            )
            return AgentOutput(success=True, data=mock.dict())

        # --- PROD ---
        db = next(get_db())

        # Get user's latest vibe
        mine = self._latest_vibe_for_user(db, user_id)
        if not mine or mine.get("score") is None:
            return AgentOutput(success=False, data={}, error="No vibe_analysis found for this user.")

        my_score = int(round(mine["score"]))
        my_tags = mine.get("tags", [])

        # Fetch baseline of other public users
        baseline = self._collect_public_baseline(db, exclude_user_id=user_id)

        # Cold start if too few public users
        if len(baseline) < self.MIN_PUBLIC_USERS:
            synth = self._synthetic_scores(1000)
            pct = self._percentile_from_distribution(my_score, synth)
            result = SocialGraphOutput(
                cold_start=True,
                sample_size=len(baseline),
                user_vibe_score=my_score,
                percentile={"overall": pct},
                similar_users=[],
                complementary_users=[]
            )
            return AgentOutput(success=True, data=result.dict())

        # Compute percentiles and matches
        pop_scores = [b["score"] for b in baseline]
        overall_pct = self._percentile_from_distribution(my_score, pop_scores)
        similar, complementary = self._rank_users(my_score, my_tags, baseline)

        result = SocialGraphOutput(
            cold_start=False,
            sample_size=len(baseline),
            user_vibe_score=my_score,
            percentile={"overall": overall_pct},
            similar_users=similar,
            complementary_users=complementary
        )
        return AgentOutput(success=True, data=result.dict())
