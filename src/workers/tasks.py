from src.services.perception import PerceptionAggregator
from src.agents.social_agent import SocialAgent, AgentInput

@celery_app.task
def process_media_async(media_id: int, storage_url: str):
    logger.info(f"[process_media_async] Start for media_id={media_id}, url={storage_url}")
    db = next(get_db())

    try:
        # Run agents sequentially
        face_res = FaceAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"FaceAgent output: {face_res.dict()}")
        if face_res.success:
            face_crops = []
            for f in face_res.data.get("faces", []):
                if f.get("crop_url"):
                    face_crops.append({
                        "crop_url": f["crop_url"],
                        "gender": f.get("gender"),
                        "age": f.get("age"),
                        "expression": f.get("expression")
                    })
            _update_media_metadata(db, media_id, {"faces": face_crops})

        posture_res = PostureAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"PostureAgent output: {posture_res.dict()}")
        if posture_res.success:
            posture_crops = []
            crop_url = posture_res.data.get("crop_url")
            if crop_url:
                posture_crops.append({
                    "crop_url": crop_url,
                    "alignment_score": posture_res.data.get("alignment_score"),
                    "tips": posture_res.data.get("tips", [])
                })
            _update_media_metadata(db, media_id, {"posture_crops": posture_crops})

        fashion_res = FashionAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"FashionAgent output: {fashion_res.dict()}")
        if fashion_res.success:
            fashion_crops = []
            for itm in fashion_res.data.get("items", []):
                if itm.get("crop_url"):
                    fashion_crops.append({
                        "type": itm.get("type"),
                        "score": itm.get("score"),
                        "crop_url": itm.get("crop_url")
                    })
            _update_media_metadata(db, media_id, {"fashion_crops": fashion_crops})

        detect_res = DetectAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"DetectAgent output: {detect_res.dict()}")
        if detect_res.success:
            _update_media_metadata(db, media_id, {"objects": detect_res.data.get("detections", [])})

        embed_res = EmbedAgent().run({"media_id": media_id, "url": storage_url})
        logger.info(f"EmbedAgent output: {embed_res.dict()}")
        if embed_res.success:
            _update_media_metadata(db, media_id, {"embedding": embed_res.data.get("embedding")})

        # --- Step 11: Build perception profile ---
        agg = PerceptionAggregator(db)
        perception_profile = agg.build_profile(media_id)

        # --- Step 12: Social Intelligence Agent ---
        social_agent = SocialAgent()
        social_result = social_agent.run(
            AgentInput(
                media_id=media_id,
                url=None,
                data={"perception_data": perception_profile}
            )
        )

        if social_result.success:
            _update_media_metadata(db, media_id, {"social": social_result.data})
        else:
            _update_media_metadata(db, media_id, {"social": {"error": social_result.error}})

        logger.info(f"[process_media_async] Completed for media_id={media_id}")

    except Exception as e:
        logger.exception(f"process_media_async failed: {e}")
