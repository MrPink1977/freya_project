"""Vision module - facial recognition, camera streams."""

from freya.vision.facial_recognition import FacialRecognition
from freya.vision.onvif_client import OnvifClient
from freya.vision.rtsp_stream import RTSPStream

__all__ = [
    "FacialRecognition",
    "OnvifClient",
    "RTSPStream",
]
