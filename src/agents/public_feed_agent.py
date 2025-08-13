import os
from sqlalchemy.orm import Session
from src.db.models import Media, User
from src.utils.logging import logger
from datetime import datetime, timedelta
import random
import uuid

class PublicFeedAgent:
    def __init__(self, db: Session):
        self.db = db
        self.mock_mode = os.getenv("LIFEMIRROR_MODE") == "mock"

    def get_feed(self, limit=20, days=30):
        if self.mock_mode:
            return self._mock_feed(limit)

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        items = (
            self.db.query(Media, User)
            .join(User, Media.user_id == User.id)
            .filter(User.opt_in_public_analysis == True)
            .filter(Media.created_at >= cutoff_date)
            .order_by(Media.created_at.desc())
            .limit(limit)
            .all()
        )

        feed = []
        for media, user in items:
            feed.append({
                "user_id": str(user.id),
                "alias": user.public_alias or "Anonymous",
                "media_id": str(media.id),
                "thumbnail_url": media.thumbnail_url,
                "created_at": media.created_at,
                "perception": media.metadata.get("social") if media.metadata else {},
            })

        return feed

    def get_leaderboard(self, limit=10):
        if self.mock_mode:
            return self._mock_leaderboard(limit)

        users = (
            self.db.query(User)
            .filter(User.opt_in_public_analysis == True)
            .all()
        )

        leaderboard = []
        for user in users:
            latest_media = (
                self.db.query(Media)
                .filter(Media.user_id == user.id)
                .order_by(Media.created_at.desc())
                .first()
            )
            if latest_media and latest_media.metadata:
                social_data = latest_media.metadata.get("social", {})
                percentile = social_data.get("percentile", {}).get("overall")
                if percentile is not None:
                    leaderboard.append({
                        "user_id": str(user.id),
                        "alias": user.public_alias or "Anonymous",
                        "percentile": percentile,
                        "media_id": str(latest_media.id),
                        "thumbnail_url": latest_media.thumbnail_url
                    })

        leaderboard.sort(key=lambda x: x["percentile"], reverse=True)
        return leaderboard[:limit]

    # -----------------------
    # Mock Data Generators
    # -----------------------
    def _mock_feed(self, limit):
        mock_aliases = ["Alex", "Sam", "Riya", "Jordan", "Maya", "Omar"]
        mock_tags = [["confident", "stylish"], ["approachable"], ["energetic", "funny"]]
        now = datetime.utcnow()

        return [
            {
                "user_id": str(uuid.uuid4()),
                "alias": random.choice(mock_aliases),
                "media_id": str(uuid.uuid4()),
                "thumbnail_url": f"https://placehold.co/200x200?text={i}",
                "created_at": now - timedelta(hours=i),
                "perception": {
                    "percentile": {"overall": random.randint(50, 99)},
                    "tags": random.choice(mock_tags)
                }
            }
            for i in range(limit)
        ]

    def _mock_leaderboard(self, limit):
        mock_aliases = ["Alex", "Sam", "Riya", "Jordan", "Maya", "Omar"]
        leaderboard = []
        for _ in range(limit):
            leaderboard.append({
                "user_id": str(uuid.uuid4()),
                "alias": random.choice(mock_aliases),
                "percentile": random.randint(60, 99),
                "media_id": str(uuid.uuid4()),
                "thumbnail_url": "https://placehold.co/200x200"
            })
        leaderboard.sort(key=lambda x: x["percentile"], reverse=True)
        return leaderboard
