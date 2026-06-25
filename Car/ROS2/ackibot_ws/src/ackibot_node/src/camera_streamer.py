import gi
import cv2
import numpy as np
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from line_detection import detect_lines_logic

Gst.init(None)

# 1. Kreiramo dva odvojena dela pipeline-a
capture_pipe = Gst.parse_launch("v4l2src device=/dev/video0 ! video/x-raw,width=640,height=360,format=NV12 ! appsink name=mysink emit-signals=True sync=False")
stream_pipe = Gst.parse_launch("appsrc name=mysrc caps=video/x-raw,format=I420,width=640,height=360,framerate=30/1 ! videoconvert ! openh264enc bitrate=2000000 ! h264parse ! rtph264pay ! udpsink host=10.1.151.8 port=5600")

sink = capture_pipe.get_by_name("mysink")
appsrc = stream_pipe.get_by_name("mysrc")

def on_new_sample(sink):
    sample = sink.emit("pull-sample")
    buf = sample.get_buffer()
    
    # Mapiranje i obrada
    result, mapinfo = buf.map(Gst.MapFlags.READ)
    arr = np.ndarray((360 + 360//2, 640), buffer=mapinfo.data, dtype=np.uint8)
    frame = cv2.cvtColor(arr, cv2.COLOR_YUV2BGR_NV12)
    buf.unmap(mapinfo)
    
    processed_frame, offset = detect_lines_logic(frame)
    
    # Konverzija nazad
    res_yuv = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2YUV_I420)
    new_buf = Gst.Buffer.new_allocate(None, res_yuv.nbytes, None)
    new_buf.fill(0, res_yuv.tobytes())
    
    # Guranje u drugi pipeline
    appsrc.emit("push-buffer", new_buf)
    
    return Gst.FlowReturn.OK

sink.connect("new-sample", on_new_sample)

# Pokreni oba
capture_pipe.set_state(Gst.State.PLAYING)
stream_pipe.set_state(Gst.State.PLAYING)

GLib.MainLoop().run()