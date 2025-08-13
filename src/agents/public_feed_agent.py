import os
from sqlalchemy.orm import Session
from src.db.models import Media, User
from src.utils.logging import logger
from datetime import datetime, timedelta
import random
import uuid
from sqlalchemy import or_

class PublicFeedAgent:
    def __init__(self, db: Session):
        self.db = db
        self.mock_mode = os.getenv("LIFEMIRROR_MODE") == "mock"

    def get_feed(
        self,
        limit=20,
        offset=0,
        days=None,
        min_percentile=None,
        tags=None,
        search_query=None,
        sort_by="newest"
    ):
        if self.mock_mode:
            return self._mock_feed(
                limit=limit,
                search_query=search_query,
                min_percentile=min_percentile,
                tags=tags,
                sort_by=sort_by
            )
    
        q = (
            self.db.query(Media, User)
            .join(User, Media.user_id == User.id)
            .filter(User.opt_in_public_analysis == True)
        )
    
        if days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            q = q.filter(Media.created_at >= cutoff_date)
    
        if tags:
            for tag in tags:
                q = q.filter(Media.metadata['social']['tags'].astext.contains(tag))
    
        if search_query:
            like_query = f"%{search_query}%"
            q = q.filter(
                or_(
                    User.public_alias.ilike(like_query),
                    Media.metadata['social']['tags'].astext.ilike(like_query)
                )
            )
    
        # Sorting logic
        if sort_by == "newest":
            q = q.order_by(Media.created_at.desc())
        elif sort_by == "highest":
            q = q.order_by(Media.metadata['social']['percentile']['overall'].desc().nullslast())
        elif sort_by == "random":
            q = q.order_by(func.random())
        elif sort_by == "trending":
            # trending = percentile + recency score
            q = q.order_by(
                (Media.metadata['social']['percentile']['overall'].cast(Float) +
                 (100 - func.extract('epoch', now() - Media.created_at) / 3600) * 0.1)
                .desc().nullslast()
            )
        else:
            q = q.order_by(Media.created_at.desc())
    
        q = q.offset(offset).limit(limit)
        items = q.all()
    
        feed = []
        for media, user in items:
            social = media.metadata.get("social") if media.metadata else {}
            percentile = social.get("percentile", {}).get("overall")
    
            if min_percentile is not None and (percentile is None or percentile < min_percentile):
                continue
    
            feed.append({
                "user_id": str(user.id),
                "alias": user.public_alias or "Anonymous",
                "media_id": str(media.id),
                "thumbnail_url": media.thumbnail_url,
                "created_at": media.created_at,
                "perception": social,
            })
    
        return feed



    def get_leaderboard(
        self,
        limit=20,
        offset=0,
        days=None,
        search_query=None,
        sort_by="highest"
    ):
        if self.mock_mode:
            return self._mock_leaderboard(limit, search_query=search_query, sort_by=sort_by)
    
        q = (
            self.db.query(User, func.max(Media.created_at).label("last_upload"), Media.metadata)
            .join(Media, Media.user_id == User.id)
            .filter(User.opt_in_public_analysis == True)
            .group_by(User.id, Media.metadata)
        )
    
        if days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            q = q.filter(Media.created_at >= cutoff_date)
    
        if search_query:
            like_query = f"%{search_query}%"
            q = q.filter(
                or_(
                    User.public_alias.ilike(like_query),
                    Media.metadata['social']['tags'].astext.ilike(like_query)
                )
            )
    
        # Sorting
        if sort_by == "highest":
            q = q.order_by(Media.metadata['social']['percentile']['overall'].desc().nullslast())
        elif sort_by == "newest":
            q = q.order_by(func.max(Media.created_at).desc())
        elif sort_by == "random":
            q = q.order_by(func.random())
        elif sort_by == "trending":
            q = q.order_by(
                (Media.metadata['social']['percentile']['overall'].cast(Float) +
                 (100 - func.extract('epoch', now() - func.max(Media.created_at)) / 3600) * 0.1)
                .desc().nullslast()
            )
    
        q = q.offset(offset).limit(limit)
        items = q.all()
    
        leaderboard = []
        for user, last_upload, metadata in items:
            social = metadata.get("social") if metadata else {}
            leaderboard.append({
                "user_id": str(user.id),
                "alias": user.public_alias or "Anonymous",
                "percentile": social.get("percentile", {}).get("overall"),
                "tags": social.get("tags", []),
                "last_upload": last_upload
            })
    
        return leaderboard


    # -----------------------
    # Mock Data Generators
    # -----------------------
    def _mock_feed(self, limit, search_query=None, min_percentile=None, tags=None, sort_by="newest"):
        mock_aliases = ["Alex", "Sam", "Riya", "Jordan", "Maya", "Omar"]
        mock_tags = [["confident", "stylish"], ["approachable"], ["energetic", "funny"]]
        now = datetime.utcnow()
    
        feed = []
        for i in range(limit * 2):
            alias = random.choice(mock_aliases)
            perception_tags = random.choice(mock_tags)
            percentile = random.randint(50, 99)
    
            item = {
                "user_id": str(uuid.uuid4()),
                "alias": alias,
                "media_id": str(uuid.uuid4()),
                "thumbnail_url": f"https://placehold.co/200x200?text={i}",
                "created_at": now - timedelta(hours=i),
                "perception": {
                    "percentile": {"overall": percentile},
                    "tags": perception_tags
                }
            }
    
            if min_percentile and percentile < min_percentile:
                continue
            if tags and not any(tag in perception_tags for tag in tags):
                continue
            if search_query:
                sq = search_query.lower()
                if sq not in alias.lower() and not any(sq in t.lower() for t in perception_tags):
                    continue
    
            feed.append(item)
    
        if sort_by == "highest":
            feed.sort(key=lambda x: x["perception"]["percentile"]["overall"], reverse=True)
        elif sort_by == "random":
            random.shuffle(feed)
        elif sort_by == "trending":
            feed.sort(key=lambda x: x["perception"]["percentile"]["overall"] + (100 - (now - x["created_at"]).total_seconds() / 3600) * 0.1, reverse=True)
        else:  # newest
            feed.sort(key=lambda x: x["created_at"], reverse=True)
    
        return feed[:limit]


    def _mock_leaderboard(self, limit, search_query=None, sort_by="highest"):
        mock_aliases = ["Alex", "Sam", "Riya", "Jordan", "Maya", "Omar"]
        mock_tags = [["confident", "stylish"], ["approachable"], ["energetic", "funny"]]
        now = datetime.utcnow()
    
        leaderboard = []
        for i in range(limit * 2):
            alias = random.choice(mock_aliases)
            tags = random.choice(mock_tags)
            percentile = random.randint(50, 99)
    
            item = {
                "user_id": str(uuid.uuid4()),
                "alias": alias,
                "percentile": percentile,
                "tags": tags,
                "last_upload": now - timedelta(days=random.randint(0, 30))
            }
    
            if search_query:
                sq = search_query.lower()
                if sq not in alias.lower() and not any(sq in t.lower() for t in tags):
                    continue
    
            leaderboard.append(item)
    
        if sort_by == "highest":
            leaderboard.sort(key=lambda x: x["percentile"], reverse=True)
        elif sort_by == "newest":
            leaderboard.sort(key=lambda x: x["last_upload"], reverse=True)
        elif sort_by == "random":
            random.shuffle(leaderboard)
        elif sort_by == "trending":
            leaderboard.sort(key=lambda x: x["percentile"] + (100 - (now - x["last_upload"]).total_seconds() / 3600) * 0.1, reverse=True)
    
        return leaderboard[:limit]
    
