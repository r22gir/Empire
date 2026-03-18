"""
Social Service — Instagram & Facebook posting via Facebook Graph API v21.0.
Uses httpx for async HTTP calls.
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

GRAPH_API = "https://graph.facebook.com/v21.0"
INSTAGRAM_API_TOKEN = os.getenv("INSTAGRAM_API_TOKEN", "")
FACEBOOK_PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN", "")


async def _get_instagram_account_id() -> str | None:
    """Discover the Instagram Business Account ID linked to the Facebook page."""
    if not FACEBOOK_PAGE_TOKEN:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        # First get the page ID
        resp = await client.get(
            f"{GRAPH_API}/me",
            params={"fields": "id,instagram_business_account", "access_token": FACEBOOK_PAGE_TOKEN},
        )
        if resp.status_code != 200:
            logger.warning("Failed to get page info: %s", resp.text)
            return None
        data = resp.json()
        ig_account = data.get("instagram_business_account")
        if ig_account:
            return ig_account["id"]
        return None


async def post_to_instagram(caption: str, image_url: str = None) -> dict:
    """
    Post to Instagram via Facebook Graph API v21.0.
    Steps: 1) Create media container  2) Publish it.
    Requires an image_url (Instagram API requires media for feed posts).
    """
    token = INSTAGRAM_API_TOKEN or FACEBOOK_PAGE_TOKEN
    if not token:
        return {"posted": False, "post_id": "", "error": "No Instagram/Facebook token configured"}

    if not image_url:
        return {"posted": False, "post_id": "", "error": "image_url is required for Instagram posts"}

    try:
        ig_account_id = await _get_instagram_account_id()
        if not ig_account_id:
            return {"posted": False, "post_id": "", "error": "Could not find Instagram Business Account ID"}

        async with httpx.AsyncClient(timeout=30) as client:
            # Step 1: Create media container
            container_resp = await client.post(
                f"{GRAPH_API}/{ig_account_id}/media",
                params={
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": token,
                },
            )
            if container_resp.status_code != 200:
                return {"posted": False, "post_id": "", "error": f"Container creation failed: {container_resp.text}"}

            container_id = container_resp.json().get("id")
            if not container_id:
                return {"posted": False, "post_id": "", "error": "No container ID returned"}

            # Step 2: Publish the container
            publish_resp = await client.post(
                f"{GRAPH_API}/{ig_account_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": token,
                },
            )
            if publish_resp.status_code != 200:
                return {"posted": False, "post_id": "", "error": f"Publish failed: {publish_resp.text}"}

            post_id = publish_resp.json().get("id", "")
            logger.info("Instagram post published: %s", post_id)
            return {"posted": True, "post_id": post_id}

    except Exception as e:
        logger.error("Instagram post error: %s", e)
        return {"posted": False, "post_id": "", "error": str(e)}


async def post_to_facebook(message: str, link: str = None) -> dict:
    """Post to Facebook Page feed via Graph API v21.0."""
    if not FACEBOOK_PAGE_TOKEN:
        return {"posted": False, "post_id": "", "error": "No Facebook page token configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Get page ID from token
            me_resp = await client.get(
                f"{GRAPH_API}/me",
                params={"fields": "id", "access_token": FACEBOOK_PAGE_TOKEN},
            )
            if me_resp.status_code != 200:
                return {"posted": False, "post_id": "", "error": f"Failed to get page ID: {me_resp.text}"}

            page_id = me_resp.json().get("id")
            if not page_id:
                return {"posted": False, "post_id": "", "error": "No page ID returned"}

            # Post to feed
            params = {
                "message": message,
                "access_token": FACEBOOK_PAGE_TOKEN,
            }
            if link:
                params["link"] = link

            post_resp = await client.post(
                f"{GRAPH_API}/{page_id}/feed",
                params=params,
            )
            if post_resp.status_code != 200:
                return {"posted": False, "post_id": "", "error": f"Post failed: {post_resp.text}"}

            post_id = post_resp.json().get("id", "")
            logger.info("Facebook post published: %s", post_id)
            return {"posted": True, "post_id": post_id}

    except Exception as e:
        logger.error("Facebook post error: %s", e)
        return {"posted": False, "post_id": "", "error": str(e)}


async def get_social_accounts() -> dict:
    """Check which social tokens are configured and verify them with /me."""
    result = {
        "instagram": {"connected": False, "handle": ""},
        "facebook": {"connected": False, "page": ""},
    }

    async with httpx.AsyncClient(timeout=10) as client:
        # Check Facebook
        if FACEBOOK_PAGE_TOKEN:
            try:
                resp = await client.get(
                    f"{GRAPH_API}/me",
                    params={"fields": "id,name", "access_token": FACEBOOK_PAGE_TOKEN},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result["facebook"] = {
                        "connected": True,
                        "page": data.get("name", ""),
                        "page_id": data.get("id", ""),
                    }
            except Exception as e:
                logger.warning("Facebook token check failed: %s", e)

        # Check Instagram
        token = INSTAGRAM_API_TOKEN or FACEBOOK_PAGE_TOKEN
        if token:
            try:
                ig_id = await _get_instagram_account_id()
                if ig_id:
                    resp = await client.get(
                        f"{GRAPH_API}/{ig_id}",
                        params={"fields": "id,username,name", "access_token": token},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        result["instagram"] = {
                            "connected": True,
                            "handle": data.get("username", ""),
                            "name": data.get("name", ""),
                            "account_id": data.get("id", ""),
                        }
            except Exception as e:
                logger.warning("Instagram token check failed: %s", e)

    return result
