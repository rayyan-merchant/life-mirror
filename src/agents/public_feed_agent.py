from sqlalchemy.orm import Session
from src.db.models import Media, User
from src.utils.logging import logger
from datetime import datetime, timedelta

class PublicFeedAgent:
    def __init__(self, db: Session):
        self.db = db

    def get_feed(self, limit=20, days=30):
        """Get latest perception results from opted-in users within X days."""
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
        """Rank opted-in users by latest percentile score from social graph."""
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
