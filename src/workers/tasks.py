from src.services.perception import PerceptionAggregator
from src.agents.social_agent import SocialAgent, AgentInput
from src.agents.vibe_compare_agent import VibeComparisonAgent, AgentInputfrom src.agents.perception_history_agent import PerceptionHistoryAgent, AgentInput


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

        # Trigger perception history update for the user
        media = db.query(Media).filter(Media.id == media_id).first()
        if media and media.user_id:
            update_perception_history_async.delay(media.user_id)


    except Exception as e:
        logger.exception(f"process_media_async failed: {e}")



@celery_app.task
def compare_media_vibes_async(media_id_1: int, media_id_2: int):
    logger.info(f"[compare_media_vibes_async] Start for media_id_1={media_id_1}, media_id_2={media_id_2}")
    db = next(get_db())

    try:
        agent = VibeComparisonAgent()
        result = agent.run(AgentInput(media_id=0, url=None, data={
            "media_id_1": media_id_1,
            "media_id_2": media_id_2
        }))

        if result.success:
            # Store comparison result in both media items' metadata
            for mid in (media_id_1, media_id_2):
                _update_media_metadata(db, mid, {
                    f"vibe_comparison_with_{media_id_2 if mid == media_id_1 else media_id_1}": result.data
                })
        else:
            logger.error(f"VibeComparisonAgent failed: {result.error}")

        logger.info(f"[compare_media_vibes_async] Completed for {media_id_1} vs {media_id_2}")

    except Exception as e:
        logger.exception(f"compare_media_vibes_async failed: {e}")



@celery_app.task
def update_perception_history_async(user_id: int):
    logger.info(f"[update_perception_history_async] Start for user_id={user_id}")
    db = next(get_db())

    try:
        agent = PerceptionHistoryAgent()
        result = agent.run(AgentInput(media_id=0, url=None, data={"user_id": user_id}))

        if result.success:
            # Store the latest history summary in a special metadata field for the latest media
            latest_media = (
                db.query(Media)
                .filter(Media.user_id == user_id)
                .order_by(Media.created_at.desc())
                .first()
            )
            if latest_media:
                _update_media_metadata(db, latest_media.id, {
                    "history_summary": result.data
                })
        else:
            logger.error(f"PerceptionHistoryAgent failed: {result.error}")

        logger.info(f"[update_perception_history_async] Completed for user_id={user_id}")

    except Exception as e:
        logger.exception(f"update_perception_history_async failed: {e}")
