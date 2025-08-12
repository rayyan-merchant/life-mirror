from sqlalchemy.orm import Session
from src.db.models import Media

class PerceptionAggregator:
    def __init__(self, db: Session):
        self.db = db

    def build_profile(self, media_id: int) -> dict:
        media = self.db.query(Media).filter(Media.id == media_id).first()
        if not media or not media.metadata:
            return {"error": "Media not found or not processed yet"}

        md = media.metadata

        faces = md.get("faces", [])
        posture = md.get("posture_crops", [])
        fashion = md.get("fashion_crops", [])
        objects = md.get("objects", [])
        embedding = md.get("embedding", None)

        # Compute summaries
        style_summary = None
        if fashion:
            colors = [f.get("dominant_color") for f in fashion if f.get("dominant_color")]
            style_summary = {
                "main_colors": list(set(colors)),
                "items_detected": len(fashion)
            }

        posture_grade = None
        if posture:
            score = posture[0].get("alignment_score")
            if score is not None:
                if score >= 8: posture_grade = "Excellent"
                elif score >= 6: posture_grade = "Good"
                elif score >= 4: posture_grade = "Average"
                else: posture_grade = "Poor"

        # Basic overall score (toy formula)
        overall_score = 0
        if faces: overall_score += 3
        if posture_grade in ["Excellent", "Good"]: overall_score += 3
        if fashion: overall_score += 2
        if objects: overall_score += 1

        profile = {
            "media_id": media.id,
            "media_url": media.url,
            "faces": faces,
            "posture": posture,
            "fashion": fashion,
            "environment": {
                "objects": objects,
                "embedding": embedding
            },
            "summaries": {
                "style_summary": style_summary,
                "posture_grade": posture_grade,
                "overall_score": overall_score
            }
        }

        return profile
