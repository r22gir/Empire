"""Transport policy: what delivery method is default per output type + channel."""

TRANSPORT_POLICY = {
    "drawing": {
        "web_cc": {"default": "inline_svg", "fallback": "download_link"},
        "web": {"default": "inline_svg", "fallback": "download_link"},
        "telegram": {"default": "file_attachment", "fallback": "description_only"},
    },
    "pdf": {
        "web_cc": {"default": "download_link", "fallback": "description_only"},
        "web": {"default": "download_link", "fallback": "description_only"},
        "telegram": {"default": "file_attachment", "fallback": "download_link"},
    },
    "quote": {
        "web_cc": {"default": "inline_display", "fallback": "download_link"},
        "web": {"default": "inline_display", "fallback": "download_link"},
        "telegram": {"default": "summary_text", "fallback": "summary_text"},
    },
}

def get_transport(output_type: str, channel: str) -> dict:
    return TRANSPORT_POLICY.get(output_type, {}).get(channel, {"default": "none", "fallback": "none"})

NO_PROOF_RESPONSE = "I generated it, but I have not sent it externally. You can view/download it from the interface."
