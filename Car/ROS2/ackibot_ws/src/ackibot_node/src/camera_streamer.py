import gi
import cv2
import numpy as np
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from line_detection import detect_lines_logic

Gst.init(None)

appsrc = None

def on_new_sample(sink):
    global appsrc
    sample = sink.emit("pull-sample")
    buf = sample.get_buffer()
    
    # 1. Mapiranje bafera za čitanje
    result, mapinfo = buf.map(Gst.MapFlags.READ)
    arr = np.ndarray((360 + 360//2, 640), buffer=mapinfo.data, dtype=np.uint8)
    frame = cv2.cvtColor(arr, cv2.COLOR_YUV2BGR_NV12)
    buf.unmap(mapinfo)
    
    # 2. Tvoja obrada
    processed_frame, offset = detect_lines_logic(frame)
    
    # 3. Konverzija nazad u GstBuffer
    # Konvertujemo BGR nazad u format koji enkoder očekuje
    res_bgr = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2YUV_I420)
    
    new_buf = Gst.Buffer.new_allocate(None, res_bgr.nbytes, None)
    new_buf.fill(0, res_bgr.tobytes())
    
    # 4. Guranje u pipeline
    if appsrc:
        appsrc.emit("push-buffer", new_buf)
    
    return Gst.FlowReturn.OK

# Pipeline (važno: appsrc mora imati definisane CAPS)
pipeline_str = (
    "v4l2src device=/dev/video0 ! video/x-raw,width=640,height=360,format=NV12 ! "
    "appsink name=mysink emit-signals=True sync=False ! "
    "appsrc name=mysrc caps=video/x-raw,format=I420,width=640,height=360,framerate=30/1 ! "
    "videoconvert ! v4l2h264enc ! h264parse ! rtph264pay ! udpsink host=10.1.151.8 port=5600"
)

pipeline = Gst.parse_launch(pipeline_str)
sink = pipeline.get_by_name("mysink")
appsrc = pipeline.get_by_name("mysrc") # Dohvatamo referencu

sink.connect("new-sample", on_new_sample)

pipeline.set_state(Gst.State.PLAYING)
GLib.MainLoop().run()